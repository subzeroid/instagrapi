import json
import zlib
from unittest import mock

from instagrapi import Client
from instagrapi.realtime import RealtimeClient
from instagrapi.realtime.mqttot import (
    MQTToTConnection,
    MQTToTTopics,
    SocketMQTToTTransport,
    decode_packet,
    read_thrift_object,
    write_connect_packet,
    write_pingreq_packet,
    write_publish_packet,
)


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


def test_mqttot_connect_packet_uses_custom_protocol_and_zipped_thrift_payload():
    connection = MQTToTConnection(
        client_identifier="phone-id-123456789",
        client_info={
            "userId": 12345,
            "userAgent": "Instagram 428",
            "clientCapabilities": 183,
            "endpointCapabilities": 0,
            "publishFormat": 1,
            "deviceId": "phone-id-12345678901234567890",
            "isInitiallyForeground": True,
            "subscribeTopics": [88, 135, 149, 150, 133, 146],
            "clientType": "cookie_auth",
            "appId": 567067343352427,
            "clientStack": 3,
        },
        password="sessionid=12345:session",
        app_specific_info={
            "app_version": "428.0.0.47.67",
            "platform": "android",
            "ig_mqtt_route": "django",
        },
    )

    packet = write_connect_packet(connection, keep_alive=20)

    assert packet[0] == 0x10
    decoded = decode_packet(packet)
    assert decoded.packet_type == "connect"
    assert decoded.protocol_name == "MQTToT"
    assert decoded.protocol_level == 3
    assert decoded.connect_flags == 0xC2
    assert decoded.keep_alive == 20

    thrift_payload = zlib.decompress(decoded.payload)
    thrift = read_thrift_object(thrift_payload, MQTToTConnection.thrift_descriptors())
    assert thrift["clientIdentifier"] == "phone-id-123456789"
    assert thrift["password"] == "sessionid=12345:session"
    assert thrift["clientInfo"]["clientType"] == "cookie_auth"
    assert thrift["clientInfo"]["subscribeTopics"] == [88, 135, 149, 150, 133, 146]
    assert thrift["appSpecificInfo"]["ig_mqtt_route"] == "django"


def test_publish_packet_round_trips_topic_and_zipped_payload():
    payload = zlib.compress(json.dumps({"sub": ["1/graphqlsubscriptions/test/{}"]}).encode())

    packet = write_publish_packet(MQTToTTopics.REALTIME_SUB, payload, qos=1, packet_id=7)

    decoded = decode_packet(packet)
    assert decoded.packet_type == "publish"
    assert decoded.topic == MQTToTTopics.REALTIME_SUB
    assert decoded.qos == 1
    assert decoded.packet_id == 7
    assert json.loads(zlib.decompress(decoded.payload)) == {"sub": ["1/graphqlsubscriptions/test/{}"]}


def test_ping_response_packet_decodes_as_pingresp():
    decoded = decode_packet(b"\xd0\x00")

    assert decoded.packet_type == "pingresp"
    assert decoded.payload == b""


def test_realtime_client_builds_cookie_auth_connection_from_instagram_session():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client)

    connection = realtime.build_connection()

    assert connection.client_identifier == "phone-id-12345678901"
    assert connection.password == "sessionid=12345:session"
    assert connection.client_info["userId"] == 12345
    assert connection.client_info["clientType"] == "cookie_auth"
    assert connection.client_info["appId"] == 567067343352427
    assert connection.client_info["subscribeTopics"] == [88, 135, 149, 150, 133, 146]
    assert connection.app_specific_info["app_version"] == "428.0.0.47.67"
    assert connection.app_specific_info["platform"] == "android"


def test_realtime_client_default_transport_uses_client_proxy():
    client = _build_logged_in_client()
    client.proxy = "socks5://127.0.0.1:8888"

    realtime = RealtimeClient(client)

    assert isinstance(realtime.transport, SocketMQTToTTransport)
    assert realtime.transport.proxy == "socks5://127.0.0.1:8888"


def test_client_exposes_stateful_realtime_helpers():
    client = _build_logged_in_client()
    transport = mock.Mock()
    client.realtime_connect(transport=transport)

    assert isinstance(client.realtime, RealtimeClient)
    transport.connect.assert_called_once()

    client.realtime_disconnect()
    transport.disconnect.assert_called_once()


def test_realtime_client_ping_sends_keepalive_and_reads_pingresp():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.recv_packet.return_value = b"\xd0\x00"
    realtime = RealtimeClient(client, transport=transport)
    realtime.connected = True

    assert realtime.ping()

    transport.send.assert_called_once_with(write_pingreq_packet())
    transport.recv_packet.assert_called_once()


def test_client_exposes_stateful_realtime_ping_helper():
    client = _build_logged_in_client()
    transport = mock.Mock()
    transport.recv_packet.return_value = b"\xd0\x00"
    client.realtime_connect(transport=transport)

    assert client.realtime_ping()


def test_realtime_client_iris_subscribe_publishes_inbox_sync_state():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client, transport=mock.Mock())

    with mock.patch.object(realtime, "publish_json") as publish_json:
        realtime.iris_subscribe(seq_id=123, snapshot_at_ms=456)

    publish_json.assert_called_once_with(
        MQTToTTopics.IRIS_SUB,
        {
            "seq_id": 123,
            "snapshot_at_ms": 456,
            "snapshot_app_version": "428.0.0.47.67",
        },
    )


def test_realtime_client_iris_subscribe_uses_device_settings_app_version():
    client = _build_logged_in_client()
    del client.app_version
    client.device_settings = {"app_version": "428.0.0.47.67"}
    realtime = RealtimeClient(client, transport=mock.Mock())

    with mock.patch.object(realtime, "publish_json") as publish_json:
        realtime.iris_subscribe(seq_id=123, snapshot_at_ms=456)

    assert publish_json.call_args.args[1]["snapshot_app_version"] == "428.0.0.47.67"


def test_realtime_client_direct_subscribe_fetches_inbox_and_subscribes_to_iris():
    client = _build_logged_in_client()
    client.last_json = {"seq_id": 123, "snapshot_at_ms": 456}
    client.direct_threads = mock.Mock(return_value=[])
    realtime = RealtimeClient(client, transport=mock.Mock())

    with mock.patch.object(realtime, "iris_subscribe") as iris_subscribe:
        state = realtime.direct_subscribe()

    client.direct_threads.assert_called_once_with(amount=1)
    iris_subscribe.assert_called_once_with(seq_id=123, snapshot_at_ms=456)
    assert state == {"seq_id": 123, "snapshot_at_ms": 456}


def test_realtime_client_direct_send_text_publishes_mqtt_direct_command():
    client = _build_logged_in_client()
    transport = mock.Mock()
    realtime = RealtimeClient(client, transport=transport)

    state = realtime.direct_send_text("thread-1", "hello", client_context="ctx-1")

    packet = decode_packet(transport.send.call_args.args[0])
    payload = json.loads(zlib.decompress(packet.payload))
    assert packet.topic == MQTToTTopics.SEND_MESSAGE
    assert payload == {
        "action": "send_item",
        "thread_id": "thread-1",
        "client_context": "ctx-1",
        "item_type": "text",
        "text": "hello",
    }
    assert state == {"thread_id": "thread-1", "client_context": "ctx-1", "action": "send_item"}


def test_realtime_client_direct_send_reaction_publishes_mqtt_direct_command():
    client = _build_logged_in_client()
    transport = mock.Mock()
    realtime = RealtimeClient(client, transport=transport)

    realtime.direct_send_reaction("thread-1", "item-1", emoji="🔥", client_context="ctx-1")

    packet = decode_packet(transport.send.call_args.args[0])
    payload = json.loads(zlib.decompress(packet.payload))
    assert packet.topic == MQTToTTopics.SEND_MESSAGE
    assert payload == {
        "action": "send_item",
        "thread_id": "thread-1",
        "client_context": "ctx-1",
        "item_type": "reaction",
        "item_id": "item-1",
        "node_type": "item",
        "reaction_type": "like",
        "reaction_status": "created",
        "target_item_type": "text",
        "emoji": "🔥",
    }


def test_realtime_client_direct_indicate_activity_publishes_typing_command():
    client = _build_logged_in_client()
    transport = mock.Mock()
    realtime = RealtimeClient(client, transport=transport)

    realtime.direct_indicate_activity("thread-1", is_active=False, client_context="ctx-1")

    packet = decode_packet(transport.send.call_args.args[0])
    payload = json.loads(zlib.decompress(packet.payload))
    assert packet.topic == MQTToTTopics.SEND_MESSAGE
    assert payload == {
        "action": "indicate_activity",
        "thread_id": "thread-1",
        "client_context": "ctx-1",
        "activity_status": "0",
    }


def test_realtime_client_direct_mark_seen_publishes_seen_command():
    client = _build_logged_in_client()
    transport = mock.Mock()
    realtime = RealtimeClient(client, transport=transport)

    realtime.direct_mark_seen("thread-1", "item-1")

    packet = decode_packet(transport.send.call_args.args[0])
    payload = json.loads(zlib.decompress(packet.payload))
    assert packet.topic == MQTToTTopics.SEND_MESSAGE
    assert payload == {
        "action": "mark_seen",
        "thread_id": "thread-1",
        "item_id": "item-1",
    }


def test_realtime_client_send_foreground_state_publishes_thrift_state():
    client = _build_logged_in_client()
    transport = mock.Mock()
    realtime = RealtimeClient(client, transport=transport)

    realtime.send_foreground_state(keep_alive_timeout=60, subscribe_topics=["146"], request_id=99)

    packet = decode_packet(transport.send.call_args.args[0])
    payload = zlib.decompress(packet.payload)
    assert packet.topic == MQTToTTopics.FOREGROUND_STATE
    assert payload[0] == 0
    state = read_thrift_object(payload[1:], realtime.foreground_state_descriptors())
    assert state["keepAliveTimeout"] == 60
    assert state["subscribeTopics"] == ["146"]
    assert state["requestId"] == 99


def test_realtime_client_dispatches_send_message_response_event():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client, transport=mock.Mock())
    handler = mock.Mock()
    realtime.on("send_response", handler)
    payload = {"status": "ok", "client_context": "ctx-1"}

    realtime.dispatch_packet(MQTToTTopics.SEND_MESSAGE_RESPONSE, zlib.compress(json.dumps(payload).encode()))

    handler.assert_called_once_with(payload)


def test_message_sync_dispatch_emits_direct_message_wrapper():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client, transport=mock.Mock())
    handler = mock.Mock()
    realtime.on("message", handler)
    payload = [
        {
            "event": "patch",
            "seq_id": 123,
            "data": [
                {
                    "op": "add",
                    "path": "/direct_v2/threads/987/items/item-1",
                    "value": json.dumps({"item_id": "item-1", "text": "hello", "user_id": "55"}),
                }
            ],
        }
    ]

    realtime.dispatch_packet(MQTToTTopics.MESSAGE_SYNC, zlib.compress(json.dumps(payload).encode()))

    handler.assert_called_once()
    message = handler.call_args.args[0]["message"]
    assert message["thread_id"] == "987"
    assert message["path"] == "/direct_v2/threads/987/items/item-1"
    assert message["op"] == "add"
    assert message["text"] == "hello"
    assert message["user_id"] == "55"


def test_realtime_sub_dispatch_emits_direct_and_typing_events():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client, transport=mock.Mock())
    direct_handler = mock.Mock()
    typing_handler = mock.Mock()
    realtime.on("direct", direct_handler)
    realtime.on("typing", typing_handler)
    direct_payload = {
        "message": {
            "topic": "direct",
            "json": {
                "data": [
                    {
                        "path": "/direct_v2/threads/987/activity_indicator_id",
                        "value": json.dumps({"activity_status": "1", "sender_id": "55"}),
                    }
                ]
            },
        }
    }

    realtime.dispatch_packet(MQTToTTopics.REALTIME_SUB, zlib.compress(json.dumps(direct_payload).encode()))

    direct_handler.assert_called_once()
    typing_handler.assert_called_once()
    event = typing_handler.call_args.args[0]
    assert event["thread_id"] == "987"
    assert event["value"]["activity_status"] == "1"
    assert event["value"]["sender_id"] == "55"


def test_realtime_sub_dispatch_emits_seen_and_presence_events():
    client = _build_logged_in_client()
    realtime = RealtimeClient(client, transport=mock.Mock())
    seen_handler = mock.Mock()
    presence_handler = mock.Mock()
    realtime.on("seen", seen_handler)
    realtime.on("presence", presence_handler)
    direct_payload = {
        "message": json.dumps(
            {
                "data": [
                    {
                        "path": "/direct_v2/threads/987/seen_state",
                        "value": json.dumps({"item_id": "item-1", "user_id": "55"}),
                    },
                    {
                        "path": "/direct_v2/threads/987/presence",
                        "value": json.dumps({"is_active": True, "user_id": "55"}),
                    },
                ]
            }
        )
    }

    realtime.dispatch_packet(MQTToTTopics.REALTIME_SUB, zlib.compress(json.dumps(direct_payload).encode()))

    seen_handler.assert_called_once()
    presence_handler.assert_called_once()
    assert seen_handler.call_args.args[0]["thread_id"] == "987"
    assert presence_handler.call_args.args[0]["value"]["is_active"] is True


def test_realtime_connect_preserves_handlers_registered_before_connect():
    client = _build_logged_in_client()
    transport = mock.Mock()
    handler = mock.Mock()

    client.realtime_on("receive", handler)
    client.realtime_connect(transport=transport)
    client.realtime.emit("receive", {"topic": "146", "payload": {"ok": True}})

    handler.assert_called_once_with({"topic": "146", "payload": {"ok": True}})
