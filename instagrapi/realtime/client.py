import json
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List

from instagrapi.realtime.mqttot import (
    MQTToTConnection,
    MQTToTTopics,
    SocketMQTToTTransport,
    ThriftDescriptor,
    ThriftTypes,
    compress_payload,
    decode_packet,
    parse_json_payload,
    try_decompress_payload,
    write_connect_packet,
    write_disconnect_packet,
    write_pingreq_packet,
    write_publish_packet,
    write_thrift_object,
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

    def direct_send_text(self, thread_id: int | str, text: str, client_context: str | None = None) -> Dict[str, Any]:
        return self._publish_direct_command(
            "send_item",
            thread_id,
            {"item_type": "text", "text": text},
            client_context=client_context or self.new_client_context(),
        )

    def direct_send_reaction(
        self,
        thread_id: int | str,
        item_id: str,
        emoji: str = "",
        reaction_type: str = "like",
        reaction_status: str = "created",
        target_item_type: str = "text",
        client_context: str | None = None,
    ) -> Dict[str, Any]:
        return self._publish_direct_command(
            "send_item",
            thread_id,
            {
                "item_type": "reaction",
                "item_id": item_id,
                "node_type": "item",
                "reaction_type": reaction_type,
                "reaction_status": reaction_status,
                "target_item_type": target_item_type,
                "emoji": emoji,
            },
            client_context=client_context or self.new_client_context(),
        )

    def direct_mark_seen(self, thread_id: int | str, item_id: str) -> Dict[str, Any]:
        return self._publish_direct_command("mark_seen", thread_id, {"item_id": item_id})

    def direct_indicate_activity(
        self,
        thread_id: int | str,
        is_active: bool = True,
        client_context: str | None = None,
    ) -> Dict[str, Any]:
        return self._publish_direct_command(
            "indicate_activity",
            thread_id,
            {"activity_status": "1" if is_active else "0"},
            client_context=client_context or self.new_client_context(),
        )

    def send_foreground_state(
        self,
        in_foreground_app: bool | None = None,
        in_foreground_device: bool | None = None,
        keep_alive_timeout: int | None = None,
        subscribe_topics: List[str] | None = None,
        subscribe_generic_topics: List[str] | None = None,
        unsubscribe_topics: List[str] | None = None,
        unsubscribe_generic_topics: List[str] | None = None,
        request_id: int | None = None,
    ) -> Dict[str, Any]:
        state = {
            "inForegroundApp": in_foreground_app,
            "inForegroundDevice": in_foreground_device,
            "keepAliveTimeout": keep_alive_timeout,
            "subscribeTopics": subscribe_topics,
            "subscribeGenericTopics": subscribe_generic_topics,
            "unsubscribeTopics": unsubscribe_topics,
            "unsubscribeGenericTopics": unsubscribe_generic_topics,
            "requestId": request_id,
        }
        state = {key: value for key, value in state.items() if value is not None}
        self._publish_bytes(
            MQTToTTopics.FOREGROUND_STATE,
            compress_payload(b"\x00" + write_thrift_object(state, self.foreground_state_descriptors())),
        )
        return state

    def _publish_direct_command(
        self,
        action: str,
        thread_id: int | str,
        data: Dict[str, Any],
        client_context: str | None = None,
    ) -> Dict[str, Any]:
        payload = {"action": action, "thread_id": str(thread_id), **data}
        if client_context:
            payload["client_context"] = client_context
        self._publish_bytes(
            MQTToTTopics.SEND_MESSAGE,
            compress_payload(json.dumps(payload, separators=(",", ":")).encode()),
        )
        state = {"thread_id": str(thread_id), "action": action}
        if client_context:
            state["client_context"] = client_context
        return state

    def publish_json(self, topic: str, data: Dict[str, Any]) -> None:
        self._publish_bytes(topic, compress_payload(json.dumps(data, separators=(",", ":")).encode()))

    def _publish_bytes(self, topic: str, payload: bytes) -> None:
        self._packet_id += 1
        packet = write_publish_packet(
            topic,
            payload,
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
        if topic == MQTToTTopics.SEND_MESSAGE_RESPONSE:
            self.emit("send_response", parsed)
        if topic == MQTToTTopics.IRIS_SUB_RESPONSE:
            self.emit("iris_sub_response", parsed)
        if topic == MQTToTTopics.MESSAGE_SYNC:
            self.dispatch_message_sync(parsed)
        if topic == MQTToTTopics.REALTIME_SUB:
            self.dispatch_realtime_sub(parsed)
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
                self.dispatch_direct_realtime_event({"path": path, "op": patch.get("op"), "value": value})

    def dispatch_realtime_sub(self, payload: Any) -> None:
        self.emit("realtime_sub", payload)
        if not isinstance(payload, dict):
            return
        message = payload.get("message")
        if isinstance(message, str):
            try:
                self.dispatch_direct_realtime_payload(json.loads(message))
            except json.JSONDecodeError:
                return
            return
        if not isinstance(message, dict):
            return
        if message.get("topic") != "direct":
            return
        direct_payload = message.get("json") or message.get("payload")
        if isinstance(direct_payload, str):
            try:
                direct_payload = json.loads(direct_payload)
            except json.JSONDecodeError:
                direct_payload = {"value": direct_payload}
        self.dispatch_direct_realtime_payload(direct_payload)

    def dispatch_direct_realtime_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self.dispatch_direct_realtime_event({"value": payload})
            return
        data = payload.get("data")
        if not isinstance(data, list):
            self.dispatch_direct_realtime_event(payload)
            return
        meta = {key: value for key, value in payload.items() if key != "data"}
        for item in data:
            if isinstance(item, dict):
                self.dispatch_direct_realtime_event({**meta, **item})
            else:
                self.dispatch_direct_realtime_event({**meta, "value": item})

    def dispatch_direct_realtime_event(self, event: Dict[str, Any]) -> None:
        event = dict(event)
        value = event.get("value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        event["value"] = value
        path = event.get("path")
        if path and "thread_id" not in event:
            event["thread_id"] = self.thread_id_from_message_sync_path(path)
        self.emit("direct", event)
        kind = self.direct_realtime_event_kind(event)
        if kind:
            self.emit(kind, event)

    @staticmethod
    def direct_realtime_event_kind(event: Dict[str, Any]) -> str | None:
        path = str(event.get("path") or "").lower()
        action = str(event.get("action") or "").lower()
        value = event.get("value")
        value_text = json.dumps(value, sort_keys=True).lower() if isinstance(value, dict) else str(value).lower()
        if "activity_status" in value_text or "activity_indicator" in path or "typing" in path:
            return "typing"
        if "presence" in path or "is_active" in value_text or "last_active" in value_text:
            return "presence"
        if action == "mark_seen" or "/seen" in path or "seen_" in path or "read" in path or "seen" in value_text:
            return "seen"
        return None

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

    @staticmethod
    def foreground_state_descriptors() -> List[ThriftDescriptor]:
        return [
            ThriftDescriptor("inForegroundApp", 1, ThriftTypes.BOOLEAN),
            ThriftDescriptor("inForegroundDevice", 2, ThriftTypes.BOOLEAN),
            ThriftDescriptor("keepAliveTimeout", 3, ThriftTypes.INT_32),
            ThriftDescriptor("subscribeTopics", 4, ThriftTypes.LIST_BINARY),
            ThriftDescriptor("subscribeGenericTopics", 5, ThriftTypes.LIST_BINARY),
            ThriftDescriptor("unsubscribeTopics", 6, ThriftTypes.LIST_BINARY),
            ThriftDescriptor("unsubscribeGenericTopics", 7, ThriftTypes.LIST_BINARY),
            ThriftDescriptor("requestId", 8, ThriftTypes.INT_64),
        ]

    @staticmethod
    def new_client_context() -> str:
        return str(uuid.uuid4())

    def emit(self, event: str, payload: Any) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)
