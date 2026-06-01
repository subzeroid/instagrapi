import json
import socket
import ssl
import struct
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import unquote, urlsplit

import socks


class MQTToTTopics:
    PUBSUB = "88"
    FOREGROUND_STATE = "102"
    SEND_MESSAGE = "132"
    SEND_MESSAGE_RESPONSE = "133"
    IRIS_SUB = "134"
    IRIS_SUB_RESPONSE = "135"
    MESSAGE_SYNC = "146"
    REALTIME_SUB = "149"
    REGION_HINT = "150"


class ThriftTypes:
    STOP = 0x00
    TRUE = 0x01
    FALSE = 0x02
    BYTE = 0x03
    INT_16 = 0x04
    INT_32 = 0x05
    INT_64 = 0x06
    BINARY = 0x08
    LIST = 0x09
    MAP = 0x0B
    STRUCT = 0x0C
    BOOLEAN = 0xA1
    LIST_INT_32 = (INT_32 << 8) | LIST
    LIST_BINARY = (BINARY << 8) | LIST
    MAP_BINARY_BINARY = (0x88 << 8) | MAP


@dataclass(frozen=True)
class ThriftDescriptor:
    name: str
    field: int
    type: int
    children: tuple["ThriftDescriptor", ...] = ()


@dataclass
class DecodedMQTToTPacket:
    packet_type: str
    payload: bytes
    protocol_name: Optional[str] = None
    protocol_level: Optional[int] = None
    connect_flags: Optional[int] = None
    keep_alive: Optional[int] = None
    topic: Optional[str] = None
    qos: int = 0
    packet_id: Optional[int] = None
    return_code: Optional[int] = None


@dataclass
class MQTToTConnection:
    client_identifier: str
    client_info: Dict[str, Any]
    password: str
    app_specific_info: Optional[Dict[str, str]] = None

    @staticmethod
    def thrift_descriptors() -> List[ThriftDescriptor]:
        return [
            ThriftDescriptor("clientIdentifier", 1, ThriftTypes.BINARY),
            ThriftDescriptor("willTopic", 2, ThriftTypes.BINARY),
            ThriftDescriptor("willMessage", 3, ThriftTypes.BINARY),
            ThriftDescriptor(
                "clientInfo",
                4,
                ThriftTypes.STRUCT,
                (
                    ThriftDescriptor("userId", 1, ThriftTypes.INT_64),
                    ThriftDescriptor("userAgent", 2, ThriftTypes.BINARY),
                    ThriftDescriptor("clientCapabilities", 3, ThriftTypes.INT_64),
                    ThriftDescriptor("endpointCapabilities", 4, ThriftTypes.INT_64),
                    ThriftDescriptor("publishFormat", 5, ThriftTypes.INT_32),
                    ThriftDescriptor("noAutomaticForeground", 6, ThriftTypes.BOOLEAN),
                    ThriftDescriptor("makeUserAvailableInForeground", 7, ThriftTypes.BOOLEAN),
                    ThriftDescriptor("deviceId", 8, ThriftTypes.BINARY),
                    ThriftDescriptor("isInitiallyForeground", 9, ThriftTypes.BOOLEAN),
                    ThriftDescriptor("networkType", 10, ThriftTypes.INT_32),
                    ThriftDescriptor("networkSubtype", 11, ThriftTypes.INT_32),
                    ThriftDescriptor("clientMqttSessionId", 12, ThriftTypes.INT_64),
                    ThriftDescriptor("clientIpAddress", 13, ThriftTypes.BINARY),
                    ThriftDescriptor("subscribeTopics", 14, ThriftTypes.LIST_INT_32),
                    ThriftDescriptor("clientType", 15, ThriftTypes.BINARY),
                    ThriftDescriptor("appId", 16, ThriftTypes.INT_64),
                    ThriftDescriptor("overrideNectarLogging", 17, ThriftTypes.BOOLEAN),
                    ThriftDescriptor("connectTokenHash", 18, ThriftTypes.BINARY),
                    ThriftDescriptor("regionPreference", 19, ThriftTypes.BINARY),
                    ThriftDescriptor("deviceSecret", 20, ThriftTypes.BINARY),
                    ThriftDescriptor("clientStack", 21, ThriftTypes.BYTE),
                    ThriftDescriptor("fbnsConnectionKey", 22, ThriftTypes.INT_64),
                    ThriftDescriptor("fbnsConnectionSecret", 23, ThriftTypes.BINARY),
                    ThriftDescriptor("fbnsDeviceId", 24, ThriftTypes.BINARY),
                    ThriftDescriptor("fbnsDeviceSecret", 25, ThriftTypes.BINARY),
                    ThriftDescriptor("anotherUnknown", 26, ThriftTypes.INT_64),
                ),
            ),
            ThriftDescriptor("password", 5, ThriftTypes.BINARY),
            ThriftDescriptor("getDiffsRequests", 6, ThriftTypes.LIST_BINARY),
            ThriftDescriptor("zeroRatingTokenHash", 9, ThriftTypes.BINARY),
            ThriftDescriptor("appSpecificInfo", 10, ThriftTypes.MAP_BINARY_BINARY),
        ]

    def to_thrift(self) -> bytes:
        payload: Dict[str, Any] = {
            "clientIdentifier": self.client_identifier,
            "clientInfo": self.client_info,
            "password": self.password,
        }
        if self.app_specific_info:
            payload["appSpecificInfo"] = self.app_specific_info
        return write_thrift_object(payload, self.thrift_descriptors())


def compress_payload(data: bytes) -> bytes:
    return zlib.compress(data, level=9)


def try_decompress_payload(data: bytes) -> bytes:
    if not data or data[0] != 0x78:
        return data
    try:
        return zlib.decompress(data)
    except zlib.error:
        return data


def write_connect_packet(connection: MQTToTConnection, keep_alive: int = 20) -> bytes:
    payload = compress_payload(connection.to_thrift())
    variable_header = _write_utf8("MQTToT") + bytes([3, 0xC2]) + struct.pack("!H", keep_alive)
    remaining = variable_header + payload
    return bytes([0x10]) + _encode_remaining_length(len(remaining)) + remaining


def write_publish_packet(topic: str, payload: bytes, qos: int = 1, packet_id: int = 1) -> bytes:
    if qos not in (0, 1):
        raise ValueError("Only QoS 0 and QoS 1 are supported")
    variable_header = _write_utf8(str(topic))
    if qos:
        variable_header += struct.pack("!H", packet_id)
    body = variable_header + payload
    fixed_header = bytes([0x30 | (qos << 1)]) + _encode_remaining_length(len(body))
    return fixed_header + body


def write_subscribe_packet(topic: str, packet_id: int = 1, qos: int = 1) -> bytes:
    body = struct.pack("!H", packet_id) + _write_utf8(str(topic)) + bytes([qos])
    return bytes([0x82]) + _encode_remaining_length(len(body)) + body


def write_pingreq_packet() -> bytes:
    return b"\xc0\x00"


def write_disconnect_packet() -> bytes:
    return b"\xe0\x00"


def decode_packet(packet: bytes) -> DecodedMQTToTPacket:
    packet_type_id = packet[0] >> 4
    flags = packet[0] & 0x0F
    remaining_length, offset = _decode_remaining_length(packet, 1)
    body = packet[offset : offset + remaining_length]
    if packet_type_id == 1:
        protocol_name, pos = _read_utf8(body, 0)
        protocol_level = body[pos]
        connect_flags = body[pos + 1]
        keep_alive = struct.unpack("!H", body[pos + 2 : pos + 4])[0]
        payload = body[pos + 4 :]
        return DecodedMQTToTPacket(
            packet_type="connect",
            protocol_name=protocol_name,
            protocol_level=protocol_level,
            connect_flags=connect_flags,
            keep_alive=keep_alive,
            payload=payload,
        )
    if packet_type_id == 2:
        return DecodedMQTToTPacket(
            packet_type="connack",
            return_code=body[1],
            payload=body[2:],
        )
    if packet_type_id == 3:
        topic, pos = _read_utf8(body, 0)
        qos = (flags >> 1) & 0x03
        packet_id = None
        if qos:
            packet_id = struct.unpack("!H", body[pos : pos + 2])[0]
            pos += 2
        return DecodedMQTToTPacket(
            packet_type="publish",
            topic=topic,
            qos=qos,
            packet_id=packet_id,
            payload=body[pos:],
        )
    if packet_type_id == 12:
        return DecodedMQTToTPacket(packet_type="pingreq", payload=body)
    if packet_type_id == 13:
        return DecodedMQTToTPacket(packet_type="pingresp", payload=body)
    if packet_type_id == 14:
        return DecodedMQTToTPacket(packet_type="disconnect", payload=body)
    return DecodedMQTToTPacket(packet_type=str(packet_type_id), payload=body)


def write_thrift_object(data: Dict[str, Any], descriptors: List[ThriftDescriptor]) -> bytes:
    writer = _ThriftWriter()
    _write_thrift_struct(writer, data, descriptors)
    writer.write_stop()
    return bytes(writer.buffer)


def read_thrift_object(data: bytes, descriptors: List[ThriftDescriptor]) -> Dict[str, Any]:
    return _ThriftReader(data).read_struct(descriptors)


class SocketMQTToTTransport:
    def __init__(
        self,
        host: str,
        port: int = 443,
        timeout: float = 30.0,
        tls_context: Optional[ssl.SSLContext] = None,
        proxy: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_context = tls_context or ssl.create_default_context()
        self.proxy = proxy
        self.sock = None

    def connect(self) -> None:
        raw = (
            self._create_proxy_connection()
            if self.proxy
            else socket.create_connection((self.host, self.port), timeout=self.timeout)
        )
        self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        self.sock.settimeout(self.timeout)

    def _create_proxy_connection(self):
        proxy = self.proxy or ""
        if "://" not in proxy:
            proxy = f"http://{proxy}"
        parsed = urlsplit(proxy)
        proxy_types = {
            "http": socks.HTTP,
            "https": socks.HTTP,
            "socks4": socks.SOCKS4,
            "socks4a": socks.SOCKS4,
            "socks5": socks.SOCKS5,
            "socks5h": socks.SOCKS5,
        }
        proxy_type = proxy_types.get(parsed.scheme)
        if proxy_type is None or not parsed.hostname or parsed.port is None:
            raise ValueError(f"Unsupported realtime proxy URL: {self.proxy}")
        raw = socks.socksocket()
        raw.settimeout(self.timeout)
        raw.set_proxy(
            proxy_type,
            parsed.hostname,
            parsed.port,
            rdns=parsed.scheme in {"socks4a", "socks5h"},
            username=unquote(parsed.username) if parsed.username else None,
            password=unquote(parsed.password) if parsed.password else None,
        )
        raw.connect((self.host, self.port))
        return raw

    def send(self, packet: bytes) -> None:
        if self.sock is None:
            raise RuntimeError("Transport is not connected")
        self.sock.sendall(packet)

    def recv_packet(self) -> bytes:
        if self.sock is None:
            raise RuntimeError("Transport is not connected")
        first = _recv_exact(self.sock, 1)
        remaining = bytearray()
        while True:
            byte = _recv_exact(self.sock, 1)
            remaining.extend(byte)
            if byte[0] & 0x80 == 0:
                break
        size, _ = _decode_remaining_length(bytes(remaining), 0)
        return first + bytes(remaining) + _recv_exact(self.sock, size)

    def disconnect(self) -> None:
        if self.sock is None:
            return
        try:
            self.sock.close()
        finally:
            self.sock = None


class _ThriftWriter:
    def __init__(self):
        self.buffer = bytearray()
        self._field_stack: List[int] = []
        self._field = 0

    def write_stop(self) -> None:
        self.buffer.append(ThriftTypes.STOP)
        if self._field_stack:
            self._field = self._field_stack.pop()

    def write_field(self, field: int, field_type: int) -> None:
        delta = field - self._field
        thrift_type = field_type & 0x0F
        if 0 < delta <= 15:
            self.buffer.append((delta << 4) | thrift_type)
        else:
            self.buffer.append(thrift_type)
            self.write_varint(_zigzag(field, 16))
        self._field = field

    def write_varint(self, value: int) -> None:
        while True:
            if value & ~0x7F == 0:
                self.buffer.append(value)
                return
            self.buffer.append((value & 0x7F) | 0x80)
            value >>= 7

    def write_varbigint(self, value: int) -> None:
        self.write_varint(value)

    def write_string_direct(self, value: str) -> None:
        raw = value.encode()
        self.write_varint(len(raw))
        self.buffer.extend(raw)

    def write_string(self, field: int, value: str) -> None:
        self.write_field(field, ThriftTypes.BINARY)
        self.write_string_direct(value)

    def write_bool(self, field: int, value: bool) -> None:
        self.write_field(field, ThriftTypes.TRUE if value else ThriftTypes.FALSE)

    def write_int(self, field: int, value: int, bits: int) -> None:
        field_type = {8: ThriftTypes.BYTE, 16: ThriftTypes.INT_16, 32: ThriftTypes.INT_32, 64: ThriftTypes.INT_64}[bits]
        self.write_field(field, field_type)
        if bits == 8:
            self.buffer.extend(struct.pack("b", value))
        elif bits == 64:
            self.write_varbigint(_zigzag(value, 64))
        else:
            self.write_varint(_zigzag(value, bits))

    def push_struct(self, field: int) -> None:
        self.write_field(field, ThriftTypes.STRUCT)
        self._field_stack.append(self._field)
        self._field = 0


class _ThriftReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self._field_stack: List[int] = []
        self._field = 0

    def read_struct(self, descriptors: List[ThriftDescriptor]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while self.pos < len(self.data):
            field_type = self.read_field()
            if field_type == ThriftTypes.STOP:
                if self._field_stack:
                    self._field = self._field_stack.pop()
                break
            descriptor = _find_descriptor(descriptors, self._field, field_type)
            value = self.read_value(field_type, descriptor)
            if descriptor:
                result[descriptor.name] = value
        return result

    def read_field(self) -> int:
        byte = self.read_byte()
        if byte == ThriftTypes.STOP:
            return ThriftTypes.STOP
        delta = (byte & 0xF0) >> 4
        if delta:
            self._field += delta
        else:
            self._field = _unzigzag(self.read_varint())
        return byte & 0x0F

    def read_value(self, field_type: int, descriptor: Optional[ThriftDescriptor]) -> Any:
        if field_type == ThriftTypes.TRUE:
            return True
        if field_type == ThriftTypes.FALSE:
            return False
        if field_type == ThriftTypes.BYTE:
            return struct.unpack("b", self.read_bytes(1))[0]
        if field_type in (ThriftTypes.INT_16, ThriftTypes.INT_32):
            return _unzigzag(self.read_varint())
        if field_type == ThriftTypes.INT_64:
            return _unzigzag(self.read_varint())
        if field_type == ThriftTypes.BINARY:
            return self.read_bytes(self.read_varint()).decode()
        if field_type == ThriftTypes.LIST:
            return self.read_list()
        if field_type == ThriftTypes.MAP:
            return self.read_map()
        if field_type == ThriftTypes.STRUCT:
            self._field_stack.append(self._field)
            self._field = 0
            return self.read_struct(list(descriptor.children) if descriptor else [])
        raise ValueError(f"Unsupported thrift type: {field_type}")

    def read_list(self) -> List[Any]:
        header = self.read_byte()
        size = header >> 4
        item_type = header & 0x0F
        if size == 0x0F:
            size = self.read_varint()
        items = []
        for _ in range(size):
            items.append(self.read_value(item_type, None))
        return items

    def read_map(self) -> Dict[str, str]:
        size = self.read_varint()
        if not size:
            return {}
        item_types = self.read_byte()
        key_type = (item_types & 0xF0) >> 4
        value_type = item_types & 0x0F
        result = {}
        for _ in range(size):
            key = self.read_value(key_type, None)
            value = self.read_value(value_type, None)
            result[key] = value
        return result

    def read_byte(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def read_bytes(self, size: int) -> bytes:
        value = self.data[self.pos : self.pos + size]
        self.pos += size
        return value

    def read_varint(self) -> int:
        shift = 0
        result = 0
        while self.pos < len(self.data):
            byte = self.read_byte()
            result |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                break
            shift += 7
        return result


def _write_thrift_struct(writer: _ThriftWriter, data: Dict[str, Any], descriptors: List[ThriftDescriptor]) -> None:
    by_name = {descriptor.name: descriptor for descriptor in descriptors}
    for name, value in data.items():
        if value is None:
            continue
        descriptor = by_name[name]
        thrift_type = descriptor.type & 0xFF
        if thrift_type == ThriftTypes.BOOLEAN:
            writer.write_bool(descriptor.field, bool(value))
        elif thrift_type == ThriftTypes.BYTE:
            writer.write_int(descriptor.field, int(value), 8)
        elif thrift_type == ThriftTypes.INT_16:
            writer.write_int(descriptor.field, int(value), 16)
        elif thrift_type == ThriftTypes.INT_32:
            writer.write_int(descriptor.field, int(value), 32)
        elif thrift_type == ThriftTypes.INT_64:
            writer.write_int(descriptor.field, int(value), 64)
        elif thrift_type == ThriftTypes.BINARY:
            writer.write_string(descriptor.field, str(value))
        elif thrift_type == ThriftTypes.STRUCT:
            writer.push_struct(descriptor.field)
            _write_thrift_struct(writer, value, list(descriptor.children))
            writer.write_stop()
        elif thrift_type == ThriftTypes.LIST:
            writer.write_field(descriptor.field, ThriftTypes.LIST)
            item_type = descriptor.type >> 8
            _write_thrift_list(writer, item_type, value)
        elif thrift_type == ThriftTypes.MAP:
            _write_thrift_map(writer, descriptor.field, value)
        else:
            raise ValueError(f"Unsupported thrift type: {descriptor.type}")


def _write_thrift_list(writer: _ThriftWriter, item_type: int, values: List[Any]) -> None:
    size = len(values)
    if size < 0x0F:
        writer.buffer.append((size << 4) | item_type)
    else:
        writer.buffer.append(0xF0 | item_type)
        writer.write_varint(size)
    for value in values:
        if item_type == ThriftTypes.INT_32:
            writer.write_varint(_zigzag(int(value), 32))
        elif item_type == ThriftTypes.BINARY:
            writer.write_string_direct(str(value))
        else:
            raise ValueError(f"Unsupported thrift list type: {item_type}")


def _write_thrift_map(writer: _ThriftWriter, field: int, values: Dict[str, str]) -> None:
    writer.write_field(field, ThriftTypes.MAP)
    writer.write_varint(len(values))
    if not values:
        return
    writer.buffer.append((ThriftTypes.BINARY << 4) | ThriftTypes.BINARY)
    for key, value in values.items():
        writer.write_string_direct(str(key))
        writer.write_string_direct(str(value))


def _find_descriptor(
    descriptors: List[ThriftDescriptor],
    field: int,
    field_type: int,
) -> Optional[ThriftDescriptor]:
    for descriptor in descriptors:
        descriptor_type = descriptor.type & 0x0F
        if descriptor.field != field:
            continue
        if descriptor_type == field_type or (
            descriptor.type == ThriftTypes.BOOLEAN and field_type in (ThriftTypes.TRUE, ThriftTypes.FALSE)
        ):
            return descriptor
    return None


def _write_utf8(value: str) -> bytes:
    raw = value.encode()
    return struct.pack("!H", len(raw)) + raw


def _read_utf8(data: bytes, offset: int) -> tuple[str, int]:
    size = struct.unpack("!H", data[offset : offset + 2])[0]
    offset += 2
    return data[offset : offset + size].decode(), offset + size


def _encode_remaining_length(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value % 128
        value //= 128
        if value:
            byte |= 0x80
        encoded.append(byte)
        if not value:
            return bytes(encoded)


def _decode_remaining_length(data: bytes, offset: int) -> tuple[int, int]:
    multiplier = 1
    value = 0
    while True:
        encoded_byte = data[offset]
        offset += 1
        value += (encoded_byte & 127) * multiplier
        if encoded_byte & 128 == 0:
            return value, offset
        multiplier *= 128


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("Socket closed while reading MQTT packet")
        chunks.extend(chunk)
    return bytes(chunks)


def _zigzag(value: int, bits: int) -> int:
    return (value << 1) ^ (value >> (bits - 1))


def _unzigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def parse_json_payload(payload: bytes) -> Any:
    return json.loads(try_decompress_payload(payload).decode())


RealtimeHandler = Callable[[Any], None]
