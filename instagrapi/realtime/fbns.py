import contextlib
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from instagrapi.realtime.mqttot import (
    MQTToTConnection,
    SocketMQTToTTransport,
    compress_payload,
    decode_packet,
    try_decompress_payload,
    write_connect_packet,
    write_disconnect_packet,
    write_pingreq_packet,
    write_publish_packet,
    write_subscribe_packet,
)

FBNS_HOST = "mqtt-mini.facebook.com"
IG_FBNS_APP_ID = 567310203415052
FBNS_PACKAGE_NAME = "com.instagram.android"
FBNS_SUBSCRIBE_TOPICS = [76, 80, 231]


class FBNSTopics:
    MESSAGE = "76"
    REG_REQUEST = "79"
    REG_RESPONSE = "80"
    EXP_LOGGING = "231"
    PP = "34"


@dataclass
class FbnsDeviceAuth:
    client_id: str = ""
    user_id: int = 0
    password: str = ""
    device_id: str = ""
    device_secret: str = ""
    server_region: str = ""
    region_hint: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_client(cls, client) -> "FbnsDeviceAuth":
        settings = getattr(client, "settings", None) or {}
        stored = settings.get("fbns_auth") or {}
        phone_id = getattr(client, "phone_id", "") or ""
        return cls(
            client_id=stored.get("client_id") or phone_id[:20],
            user_id=int(stored.get("user_id") or 0),
            password=stored.get("password") or "",
            device_id=stored.get("device_id") or "",
            device_secret=stored.get("device_secret") or "",
            server_region=stored.get("server_region") or "",
            region_hint=stored.get("region_hint") or "",
            raw=stored.get("raw") or {},
        )

    def read(self, payload: bytes | str | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(payload, bytes):
            if not payload:
                data = {}
            else:
                data = json.loads(_strip_length_prefixed_json(payload).decode())
        elif isinstance(payload, str):
            data = json.loads(payload) if payload else {}
        else:
            data = dict(payload)
        self.raw.update(data)
        if "ck" in data:
            self.user_id = _optional_int(data.get("ck")) or self.user_id
        if "cs" in data:
            self.password = str(data.get("cs") or "")
        if "di" in data:
            self.device_id = str(data.get("di") or "")
            self.client_id = self.device_id[:20]
        if "ds" in data:
            self.device_secret = str(data.get("ds") or "")
        if "sr" in data:
            self.server_region = str(data.get("sr") or "")
        if "rc" in data:
            self.region_hint = str(data.get("rc") or "")
        return data

    def save(self, client) -> None:
        settings = getattr(client, "settings", None)
        if settings is not None:
            settings["fbns_auth"] = self.to_settings()

    def to_settings(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "password": self.password,
            "device_id": self.device_id,
            "device_secret": self.device_secret,
            "server_region": self.server_region,
            "region_hint": self.region_hint,
            "raw": self.raw,
        }


class FbnsClient:
    def __init__(self, client, transport=None, auth: FbnsDeviceAuth | None = None):
        self.client = client
        self.transport = transport or SocketMQTToTTransport(FBNS_HOST, proxy=getattr(client, "proxy", None))
        self.auth = auth or FbnsDeviceAuth.from_client(client)
        self.connected = False
        self._handlers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        self._packet_id = 0

    def on(self, event: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event].append(handler)

    def connect(self, register: bool = True) -> None:
        self.transport.connect()
        self._send(self.connect_packet())
        packet = decode_packet(self._recv_packet())
        if packet.packet_type != "connack" or packet.return_code != 0:
            raise ConnectionError(f"FBNS MQTT connect failed: {packet.return_code}")
        self.auth.read(packet.payload)
        self.auth.save(self.client)
        self.emit("auth", self.auth.to_settings())
        self.connected = True
        if register:
            self.subscribe(FBNSTopics.MESSAGE)
            token = self.register_token()
            response = self.register_push_token(token)
            self.emit("registered", {"token": token, "response": response})

    def disconnect(self) -> None:
        try:
            if self.connected:
                with contextlib.suppress(Exception):
                    self._send(write_disconnect_packet())
            self.transport.disconnect()
        finally:
            self.connected = False

    def build_connection(self) -> MQTToTConnection:
        phone_id = getattr(self.client, "phone_id", "") or ""
        client_id = self.auth.client_id or phone_id[:20]
        assert client_id, "Client phone_id is required"
        user_agent = getattr(self.client, "user_agent", "")
        client_info = {
            "userId": int(self.auth.user_id),
            "userAgent": user_agent,
            "clientCapabilities": 183,
            "endpointCapabilities": 128,
            "publishFormat": 1,
            "noAutomaticForeground": True,
            "makeUserAvailableInForeground": False,
            "deviceId": self.auth.device_id,
            "isInitiallyForeground": False,
            "networkType": 1,
            "networkSubtype": 0,
            "clientMqttSessionId": int(time.time() * 1000) & 0xFFFFFFFF,
            "subscribeTopics": FBNS_SUBSCRIBE_TOPICS,
            "clientType": "device_auth",
            "appId": IG_FBNS_APP_ID,
            "deviceSecret": self.auth.device_secret,
            "clientStack": 3,
            "anotherUnknown": -1,
        }
        if self.auth.password:
            client_info["fbnsConnectionSecret"] = self.auth.password
        if self.auth.device_id:
            client_info["fbnsDeviceId"] = self.auth.device_id
        if self.auth.device_secret:
            client_info["fbnsDeviceSecret"] = self.auth.device_secret
        return MQTToTConnection(
            client_identifier=client_id,
            client_info=client_info,
            password=self.auth.password,
        )

    def connect_packet(self) -> bytes:
        return write_connect_packet(self.build_connection(), keep_alive=60)

    def subscribe(self, topic: str) -> None:
        self._packet_id += 1
        self._send(write_subscribe_packet(topic, packet_id=self._packet_id))

    def register_token(self, max_packets: int = 10) -> str:
        self._publish_bytes(
            FBNSTopics.REG_REQUEST,
            json.dumps(
                {
                    "pkg_name": FBNS_PACKAGE_NAME,
                    "appid": IG_FBNS_APP_ID,
                },
                separators=(",", ":"),
            ).encode(),
        )
        for _ in range(max_packets):
            packet = decode_packet(self._recv_packet())
            if packet.packet_type != "publish":
                continue
            if packet.topic == FBNSTopics.REG_RESPONSE:
                response = self.parse_packet_payload(packet.payload)
                self._ack(packet)
                self.emit("reg_response", response)
                error = response.get("error") if isinstance(response, dict) else None
                if error:
                    raise RuntimeError(f"FBNS registration failed: {error}")
                token = response.get("token") if isinstance(response, dict) else None
                if not token:
                    raise RuntimeError("FBNS registration response did not include token")
                return str(token)
            self.dispatch_packet(packet.topic, packet.payload)
            self._ack(packet)
        raise TimeoutError("FBNS registration response was not received")

    def register_push_token(self, token: str) -> Dict[str, Any]:
        data = {
            "device_type": "android_mqtt",
            "is_main_push_channel": True,
            "device_sub_type": 2,
            "device_token": token,
            "_csrftoken": self.client.token,
            "guid": self.client.uuid,
            "uuid": self.client.uuid,
            "users": str(self.client.user_id),
            "family_device_id": str(uuid.uuid4()),
        }
        return self.client.private_request("push/register/", data, with_signature=False)

    def read_once(self) -> Any:
        packet = decode_packet(self._recv_packet())
        if packet.packet_type != "publish" or packet.topic is None:
            return packet
        payload = self.dispatch_packet(packet.topic, packet.payload)
        self._ack(packet)
        return payload

    def ping(self, max_packets: int = 5) -> bool:
        if not self.connected:
            raise RuntimeError("FBNS client is not connected")
        self._send(write_pingreq_packet())
        for _ in range(max_packets):
            packet = decode_packet(self._recv_packet())
            if packet.packet_type == "pingresp":
                return True
            if packet.packet_type != "publish" or packet.topic is None:
                return False
            self.dispatch_packet(packet.topic, packet.payload)
            self._ack(packet)
        return False

    def dispatch_packet(self, topic: str, payload: bytes) -> Any:
        parsed = self.parse_packet_payload(payload)
        if topic == FBNSTopics.MESSAGE:
            parsed = self.dispatch_fbns_message(parsed)
        elif topic == FBNSTopics.REG_RESPONSE:
            self.emit("reg_response", parsed)
        elif topic == FBNSTopics.EXP_LOGGING:
            self.emit("logging", parsed)
        elif topic == FBNSTopics.PP:
            self.emit("pp", parsed)
        else:
            self.emit("message", parsed)
        self.emit("receive", {"topic": topic, "payload": parsed})
        return parsed

    def dispatch_fbns_message(self, payload: Any) -> Any:
        if not isinstance(payload, dict):
            self.emit("message", payload)
            return payload
        push = payload.get("fbpushnotif")
        if push is None:
            self.emit("message", payload)
            return payload
        if isinstance(push, str):
            try:
                push = json.loads(push)
            except json.JSONDecodeError:
                push = {"value": push}
        self.emit("push", push)
        if isinstance(push, dict):
            collapse_key = push.get("collapse_key")
            if collapse_key:
                self.emit(str(collapse_key), push)
        return push

    @staticmethod
    def parse_packet_payload(payload: bytes) -> Any:
        body = _strip_length_prefixed_json(payload)
        try:
            return json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return body

    def _publish_bytes(self, topic: str, payload: bytes) -> None:
        self._packet_id += 1
        self._send(write_publish_packet(topic, compress_payload(payload), qos=1, packet_id=self._packet_id))

    def _ack(self, packet) -> None:
        if packet.qos == 1 and packet.packet_id is not None:
            self._send(b"\x40\x02" + packet.packet_id.to_bytes(2, "big"))

    def _send(self, packet: bytes) -> None:
        try:
            self.transport.send(packet)
        except Exception:
            self.connected = False
            raise

    def _recv_packet(self) -> bytes:
        try:
            return self.transport.recv_packet()
        except Exception:
            self.connected = False
            raise

    def emit(self, event: str, payload: Any) -> None:
        for handler in self._handlers.get(event, []):
            handler(payload)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _strip_length_prefixed_json(payload: bytes) -> bytes:
    body = try_decompress_payload(payload)
    if len(body) < 3:
        return body
    size = int.from_bytes(body[:2], "big")
    if size == len(body) - 2 and body[2:3] in {b"{", b"["}:
        return body[2:]
    return body
