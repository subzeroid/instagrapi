import json
import time
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List

from instagrapi.realtime.mqttot import (
    MQTToTConnection,
    MQTToTTopics,
    SocketMQTToTTransport,
    compress_payload,
    decode_packet,
    parse_json_payload,
    try_decompress_payload,
    write_connect_packet,
    write_disconnect_packet,
    write_pingreq_packet,
    write_publish_packet,
)

REALTIME_HOST = "edge-mqtt.facebook.com"
IG_REALTIME_APP_ID = 567067343352427
REALTIME_SUBSCRIBE_TOPICS = [88, 135, 149, 150, 133, 146]


class RealtimeClient:
    def __init__(self, client, transport=None):
        self.client = client
        self.transport = transport or SocketMQTToTTransport(REALTIME_HOST, proxy=getattr(client, "proxy", None))
        self.connected = False
        self._handlers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        self._packet_id = 0

    def on(self, event: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event].append(handler)

    def connect(self) -> None:
        self.transport.connect()
        if isinstance(self.transport, SocketMQTToTTransport):
            self.transport.send(write_connect_packet(self.build_connection()))
            packet = decode_packet(self.transport.recv_packet())
            if packet.packet_type != "connack" or packet.return_code != 0:
                raise ConnectionError(f"Realtime MQTT connect failed: {packet.return_code}")
        self.connected = True

    def disconnect(self) -> None:
        if isinstance(self.transport, SocketMQTToTTransport) and self.connected:
            self.transport.send(write_disconnect_packet())
        self.transport.disconnect()
        self.connected = False

    def build_connection(self) -> MQTToTConnection:
        sessionid = self.client.sessionid
        assert sessionid, "Login required"
        device_id = self.client.phone_id
        assert device_id, "Client phone_id is required"
        user_agent = self.client.user_agent
        app_version = self.client_app_version()
        capabilities = getattr(self.client, "capabilities", "3brTv10=")
        locale = getattr(self.client, "locale", "en_US")
        return MQTToTConnection(
            client_identifier=device_id[:20],
            client_info={
                "userId": int(self.client.user_id),
                "userAgent": user_agent,
                "clientCapabilities": 183,
                "endpointCapabilities": 0,
                "publishFormat": 1,
                "noAutomaticForeground": False,
                "makeUserAvailableInForeground": True,
                "deviceId": device_id,
                "isInitiallyForeground": True,
                "networkType": 1,
                "networkSubtype": 0,
                "clientMqttSessionId": int(time.time() * 1000) & 0xFFFFFFFF,
                "subscribeTopics": REALTIME_SUBSCRIBE_TOPICS,
                "clientType": "cookie_auth",
                "appId": IG_REALTIME_APP_ID,
                "deviceSecret": "",
                "clientStack": 3,
            },
            password=f"sessionid={sessionid}",
            app_specific_info={
                "app_version": app_version,
                "X-IG-Capabilities": capabilities,
                "everclear_subscriptions": json.dumps(
                    {
                        "inapp_notification_subscribe_comment": "17899377895239777",
                        "inapp_notification_subscribe_comment_mention_and_reply": "17899377895239777",
                        "video_call_participant_state_delivery": "17977239895057311",
                        "presence_subscribe": "17846944882223835",
                    },
                    separators=(",", ":"),
                ),
                "User-Agent": user_agent,
                "Accept-Language": locale.replace("_", "-"),
                "platform": "android",
                "ig_mqtt_route": "django",
                "pubsub_msg_type_blacklist": "direct, typing_type",
                "auth_cache_enabled": "0",
            },
        )

    def graph_ql_subscribe(self, subscriptions: str | Iterable[str]) -> None:
        if isinstance(subscriptions, str):
            subscriptions = [subscriptions]
        self.publish_json(MQTToTTopics.REALTIME_SUB, {"sub": list(subscriptions)})

    def skywalker_subscribe(self, subscriptions: str | Iterable[str]) -> None:
        if isinstance(subscriptions, str):
            subscriptions = [subscriptions]
        self.publish_json(MQTToTTopics.PUBSUB, {"sub": list(subscriptions)})

    def iris_subscribe(self, seq_id: int, snapshot_at_ms: int, snapshot_app_version: str | None = None) -> None:
        self.publish_json(
            MQTToTTopics.IRIS_SUB,
            {
                "seq_id": seq_id,
                "snapshot_at_ms": snapshot_at_ms,
                "snapshot_app_version": snapshot_app_version or self.client_app_version(),
            },
        )

    def direct_subscribe(self, amount: int = 1) -> Dict[str, Any]:
        self.client.direct_threads(amount=amount)
        seq_id = self.client.last_json.get("seq_id")
        snapshot_at_ms = self.client.last_json.get("snapshot_at_ms")
        if seq_id is None or snapshot_at_ms is None:
            raise RuntimeError("Direct inbox did not return realtime sync state")
        state = {"seq_id": seq_id, "snapshot_at_ms": snapshot_at_ms}
        self.iris_subscribe(**state)
        return state

    def publish_json(self, topic: str, data: Dict[str, Any]) -> None:
        self._packet_id += 1
        packet = write_publish_packet(
            topic,
            compress_payload(json.dumps(data, separators=(",", ":")).encode()),
            qos=1,
            packet_id=self._packet_id,
        )
        self.transport.send(packet)

    def read_once(self) -> Any:
        packet = decode_packet(self.transport.recv_packet())
        if packet.packet_type != "publish":
            return packet
        if packet.topic is None:
            return packet
        payload = self.dispatch_packet(packet.topic, packet.payload)
        if packet.qos == 1 and packet.packet_id is not None:
            self.transport.send(b"\x40\x02" + packet.packet_id.to_bytes(2, "big"))
        return payload

    def ping(self, max_packets: int = 5) -> bool:
        if not self.connected:
            raise RuntimeError("Realtime client is not connected")
        self.transport.send(write_pingreq_packet())
        for _ in range(max_packets):
            packet = decode_packet(self.transport.recv_packet())
            if packet.packet_type == "pingresp":
                return True
            if packet.packet_type != "publish" or packet.topic is None:
                return False
            self.dispatch_packet(packet.topic, packet.payload)
            if packet.qos == 1 and packet.packet_id is not None:
                self.transport.send(b"\x40\x02" + packet.packet_id.to_bytes(2, "big"))
        return False

    def dispatch_packet(self, topic: str, payload: bytes) -> Any:
        body = try_decompress_payload(payload)
        parsed = None
        if topic in {
            MQTToTTopics.SEND_MESSAGE_RESPONSE,
            MQTToTTopics.IRIS_SUB_RESPONSE,
            MQTToTTopics.REALTIME_SUB,
            MQTToTTopics.MESSAGE_SYNC,
        }:
            try:
                parsed = json.loads(body.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed = body
        else:
            try:
                parsed = parse_json_payload(payload)
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed = body
        self.emit("receive", {"topic": topic, "payload": parsed})
        if topic == MQTToTTopics.MESSAGE_SYNC:
            self.dispatch_message_sync(parsed)
        if topic == MQTToTTopics.REALTIME_SUB:
            self.emit("realtime_sub", parsed)
        return parsed

    def dispatch_message_sync(self, payload: Any) -> None:
        if not isinstance(payload, list):
            self.emit("message", payload)
            return
        for item in payload:
            if not isinstance(item, dict):
                self.emit("iris", item)
                continue
            patches = item.get("data")
            if not isinstance(patches, list):
                self.emit("iris", item)
                continue
            meta = {key: value for key, value in item.items() if key != "data"}
            for patch in patches:
                if not isinstance(patch, dict):
                    self.emit("iris", {**meta, "data": patch})
                    continue
                path = patch.get("path")
                raw_value = patch.get("value")
                if not path or raw_value is None:
                    self.emit("iris", {**meta, **patch})
                    continue
                try:
                    value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                except json.JSONDecodeError:
                    value = {"value": raw_value}
                wrapper = {
                    **meta,
                    "message": {
                        "path": path,
                        "op": patch.get("op"),
                        "thread_id": self.thread_id_from_message_sync_path(path),
                        **(value if isinstance(value, dict) else {"value": value}),
                    },
                }
                if path.startswith("/direct_v2/threads/"):
                    self.emit("message", wrapper)
                else:
                    self.emit("thread_update", wrapper)

    @staticmethod
    def thread_id_from_message_sync_path(path: str) -> str | None:
        prefix = "/direct_v2/threads/"
        if path.startswith(prefix):
            return path[len(prefix) :].split("/", 1)[0]
        prefix = "/direct_v2/inbox/threads/"
        if path.startswith(prefix):
            return path[len(prefix) :].split("/", 1)[0]
        return None

    def client_app_version(self) -> str:
        device_settings = getattr(self.client, "device_settings", None) or {}
        return getattr(self.client, "app_version", None) or device_settings.get("app_version", "")

    def emit(self, event: str, payload: Any) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)
