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
        self.transport = transport or SocketMQTToTTransport(REALTIME_HOST)
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
        app_version = getattr(self.client, "app_version", "")
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
            self.emit("message", parsed)
        if topic == MQTToTTopics.REALTIME_SUB:
            self.emit("realtime_sub", parsed)
        return parsed

    def emit(self, event: str, payload: Any) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)
