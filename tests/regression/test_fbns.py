import json
import zlib
from unittest import mock

from instagrapi import Client
from instagrapi.realtime import FbnsClient, FbnsDeviceAuth
from instagrapi.realtime.fbns import FBNS_HOST, FBNS_SUBSCRIBE_TOPICS, FBNSTopics
from instagrapi.realtime.mqttot import MQTToTConnection, decode_packet, read_thrift_object, write_publish_packet


def _build_logged_in_client():
    client = Client()
    client.authorization_data = {"ds_user_id": "12345", "sessionid": "12345:session"}
    client.phone_id = "phone-id-12345678901234567890"
    client.uuid = "uuid-1"
    client.user_agent = "Instagram 428.0.0.47.67 Android"
    client.app_version = "428.0.0.47.67"
    client.capabilities = "3brTvw=="
    client.locale = "en_US"
    return client


def _packet(packet_type: int, body: bytes) -> bytes:
    remaining = bytearray()
    value = len(body)
    while True:
        byte = value % 128
        value //= 128
        if value:
            byte |= 0x80
        remaining.append(byte)
        if not value:
            break
    return bytes([packet_type << 4]) + bytes(remaining) + body


def _connack(payload: dict) -> bytes:
    return _packet(2, b"\x00\x00" + json.dumps(payload, separators=(",", ":")).encode())


def _publish(topic: str, payload: dict, packet_id: int = 7) -> bytes:
    return write_publish_packet(topic, json.dumps(payload, separators=(",", ":")).encode(), packet_id=packet_id)


def _suback(packet_id: int = 2) -> bytes:
    return _packet(9, packet_id.to_bytes(2, "big") + b"\x01")


def test_fbns_device_auth_reads_connack_payload_and_updates_settings():
    client = _build_logged_in_client()
    auth = FbnsDeviceAuth.from_client(client)

    auth.read(
        {
            "ck": 123456,
            "cs": "connection-secret",
            "di": "fbns-device-id",
            "ds": "fbns-device-secret",
            "sr": "odn",
            "rc": "ATN",
        }
    )
    auth.save(client)

    assert auth.user_id == 123456
    assert auth.password == "connection-secret"
    assert auth.device_id == "fbns-device-id"
    assert auth.device_secret == "fbns-device-secret"
    assert client.settings["fbns_auth"]["device_id"] == "fbns-device-id"
    assert client.settings["fbns_auth"]["user_id"] == 123456


def test_fbns_device_auth_reads_length_prefixed_connack_payload():
    auth = FbnsDeviceAuth()
    payload = json.dumps({"ck": 123456, "cs": "secret"}, separators=(",", ":")).encode()

    auth.read(len(payload).to_bytes(2, "big") + payload)

    assert auth.user_id == 123456
    assert auth.password == "secret"


def test_fbns_initial_device_auth_connection_uses_zero_fbns_user_id():
    client = _build_logged_in_client()
    fbns = FbnsClient(client)

    connection = fbns.build_connection()

    assert connection.client_info["userId"] == 0


def test_fbns_client_builds_device_auth_connection():
    client = _build_logged_in_client()
    auth = FbnsDeviceAuth(
        client_id="phone-id-12345678901",
        user_id=12345,
        password="connection-secret",
        device_id="fbns-device-id",
        device_secret="fbns-device-secret",
    )
    fbns = FbnsClient(client, auth=auth)

    connection = fbns.build_connection()

    assert connection.client_identifier == "phone-id-12345678901"
    assert connection.password == "connection-secret"
    assert connection.client_info["userId"] == 12345
    assert connection.client_info["clientType"] == "device_auth"
    assert connection.client_info["endpointCapabilities"] == 128
    assert connection.client_info["subscribeTopics"] == FBNS_SUBSCRIBE_TOPICS
    assert connection.client_info["deviceId"] == "fbns-device-id"
    assert connection.client_info["deviceSecret"] == "fbns-device-secret"
    assert connection.client_info["fbnsDeviceId"] == "fbns-device-id"

    decoded = decode_packet(fbns.connect_packet())
    assert decoded.keep_alive == 60
    thrift = read_thrift_object(zlib.decompress(decoded.payload), MQTToTConnection.thrift_descriptors())
    assert thrift["clientInfo"]["clientType"] == "device_auth"
    assert thrift["clientInfo"]["subscribeTopics"] == FBNS_SUBSCRIBE_TOPICS


def test_fbns_register_token_publishes_registration_request_and_reads_token():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.recv_packet.return_value = _publish(FBNSTopics.REG_RESPONSE, {"token": "fbns-token-1"})
    fbns = FbnsClient(client, transport=transport)

    token = fbns.register_token()

    sent = decode_packet(transport.send.call_args_list[0].args[0])
    assert token == "fbns-token-1"
    assert sent.topic == FBNSTopics.REG_REQUEST
    assert json.loads(zlib.decompress(sent.payload)) == {
        "pkg_name": "com.instagram.android",
        "appid": 567310203415052,
    }


def test_fbns_connect_reads_device_auth_and_registers_push_token():
    client = _build_logged_in_client()
    client.private_request = mock.Mock(return_value={"status": "ok"})
    transport = mock.Mock()
    transport.recv_packet.side_effect = [
        _connack(
            {
                "ck": 123456,
                "cs": "connection-secret",
                "di": "fbns-device-id",
                "ds": "fbns-device-secret",
            }
        ),
        _suback(),
        _publish(FBNSTopics.REG_RESPONSE, {"token": "fbns-token-1"}),
    ]
    registered = []
    fbns = FbnsClient(client, transport=transport)
    fbns.on("registered", registered.append)

    fbns.connect()

    assert fbns.connected
    assert fbns.auth.password == "connection-secret"
    assert client.settings["fbns_auth"]["device_secret"] == "fbns-device-secret"
    client.private_request.assert_called_once()
    endpoint, data = client.private_request.call_args.args[:2]
    assert endpoint == "push/register/"
    assert data["device_type"] == "android_mqtt"
    assert data["is_main_push_channel"] is True
    assert data["device_sub_type"] == 2
    assert data["device_token"] == "fbns-token-1"
    assert data["users"] == "12345"
    assert client.private_request.call_args.kwargs == {"with_signature": False}
    assert registered == [{"token": "fbns-token-1", "response": {"status": "ok"}}]


def test_fbns_connect_subscribes_to_message_topic_before_waiting_for_registration_response():
    client = _build_logged_in_client()
    client.private_request = mock.Mock(return_value={"status": "ok"})
    transport = mock.Mock()
    transport.recv_packet.side_effect = [_connack({}), _suback(), _publish(FBNSTopics.REG_RESPONSE, {"token": "x"})]
    fbns = FbnsClient(client, transport=transport)

    fbns.connect()

    subscribe_packet = transport.send.call_args_list[1].args[0]
    assert subscribe_packet[0] == 0x82
    assert b"\x00\x0276" in subscribe_packet


def test_fbns_dispatches_push_notification_payloads():
    client = _build_logged_in_client()
    fbns = FbnsClient(client, transport=mock.Mock())
    push_events = []
    direct_push_events = []
    received_events = []
    fbns.on("push", push_events.append)
    fbns.on("direct_v2_message", direct_push_events.append)
    fbns.on("receive", received_events.append)

    payload = fbns.dispatch_packet(
        FBNSTopics.MESSAGE,
        json.dumps(
            {
                "fbpushnotif": json.dumps(
                    {
                        "collapse_key": "direct_v2_message",
                        "message": "hello",
                        "ig": "payload",
                    },
                    separators=(",", ":"),
                )
            },
            separators=(",", ":"),
        ).encode(),
    )

    assert payload["collapse_key"] == "direct_v2_message"
    assert push_events == [payload]
    assert direct_push_events == [payload]
    assert received_events == [{"topic": FBNSTopics.MESSAGE, "payload": payload}]


def test_client_exposes_stateful_fbns_helpers():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.recv_packet.side_effect = [
        _connack({}),
        _suback(),
        _publish(FBNSTopics.REG_RESPONSE, {"token": "fbns-token-1"}),
    ]
    client.private_request = mock.Mock(return_value={"status": "ok"})

    fbns = client.fbns_connect(transport=transport)

    assert isinstance(fbns, FbnsClient)
    assert fbns.transport is transport
    assert fbns.transport.connect.called

    client.fbns_disconnect()
    transport.disconnect.assert_called_once()


def test_fbns_read_once_marks_client_disconnected_when_socket_closes():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.recv_packet.side_effect = ConnectionError("Socket closed while reading MQTT packet")
    fbns = FbnsClient(client, transport=transport)
    fbns.connected = True

    try:
        fbns.read_once()
    except ConnectionError:
        pass
    else:
        raise AssertionError("read_once should raise when the transport closes")

    assert not fbns.connected


def test_fbns_disconnect_clears_client_state_after_broken_socket():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.send.side_effect = ConnectionError("Socket is already closed")
    fbns = FbnsClient(client, transport=transport)
    fbns.connected = True
    client.fbns = fbns

    client.fbns_disconnect()

    transport.disconnect.assert_called_once()
    assert not fbns.connected
    assert client.fbns is None


def test_fbns_default_transport_uses_mqtt_mini_and_client_proxy():
    client = _build_logged_in_client()
    client.proxy = "socks5://127.0.0.1:8888"

    fbns = FbnsClient(client)

    assert fbns.transport.host == FBNS_HOST
    assert fbns.transport.proxy == "socks5://127.0.0.1:8888"
