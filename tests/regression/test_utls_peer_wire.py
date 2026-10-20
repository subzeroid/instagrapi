# protects: Actual native HTTP/2 rejects poisoned frame sizes and push promises after ENABLE_PUSH=0.
# fails_when: A peer can elicit empty continuation loops, invalid settings ACKs, or accepted prohibited push.
# why_new: Normal native responses never exercise hostile peer settings and server push.
# seam: none
"""Bound hostile native peers by socket deadlines, frame caps and a child process."""

import json
import socketserver
import subprocess
import sys
import threading

import pytest

pytest.importorskip("h2")
pytest.importorskip("cryptography")

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import DataReceived, RemoteSettingsChanged, SettingsAcknowledged, StreamEnded
from hpack import Encoder
from hyperframe.frame import Frame, PushPromiseFrame, SettingsFrame

from tests.regression.test_utls_transport_wire import lab as lab
from tests.regression.test_utls_transport_wire import library_path as library_path
from tests.regression.test_utls_transport_wire import url

_REQUESTS = """
import json
import sys
from instagrapi import Client

client = Client(private_transport="utls", utls_library_path=sys.argv[1], tls_verify=False, request_timeout=0)
client.private.trust_env = False
result = {"statuses": [], "error": None}
try:
    for _ in range(int(sys.argv[3])):
        response = client.private.post(sys.argv[2], data=b"synthetic-peer-body", timeout=2)
        result["statuses"].append(response.status_code)
except Exception as error:
    result["error"] = type(error).__name__
finally:
    for session in (client.private, client.public, client.graphql):
        session.close()
print(json.dumps(result))
"""


def native_requests(library_path, lab, count):
    # subprocess.run kills and waits for a timed-out child, including native
    # threads. The peer separately stops after at most 64 received frames.
    process = subprocess.run(
        [sys.executable, "-c", _REQUESTS, library_path, url(lab), str(count)],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    )
    return json.loads(process.stdout)


def read_exact(conn, size):
    result = bytearray()
    while len(result) < size:
        chunk = conn.recv(size - len(result))
        if not chunk:
            raise EOFError
        result.extend(chunk)
    return bytes(result)


@pytest.mark.parametrize("frame_size", [0, 16383, 1 << 24, 16384, (1 << 24) - 1])
def test_native_peer_frame_size_validation_prevents_empty_continuation_loop(library_path, lab, monkeypatch, frame_size):
    observed = {"sent_setting": False, "acknowledged": False, "empty_frames": 0, "bodies": []}
    finished = threading.Event()

    class Peer(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            try:
                with self.server.tls.wrap_socket(self.request, server_side=True) as conn:
                    h2 = H2Connection(config=H2Configuration(client_side=False))
                    h2.initiate_connection()
                    conn.sendall(h2.data_to_send())
                    initial_ack, first_stream = False, None
                    body = bytearray()
                    for _ in range(64):
                        data = conn.recv(65535)
                        if not data:
                            return
                        for event in h2.receive_data(data):
                            if isinstance(event, SettingsAcknowledged):
                                initial_ack = True
                            elif isinstance(event, DataReceived):
                                body.extend(event.data)
                            elif isinstance(event, StreamEnded):
                                first_stream = event.stream_id
                        pending = h2.data_to_send()
                        if pending:
                            conn.sendall(pending)
                        if initial_ack and first_stream:
                            break
                    else:
                        return
                    observed["bodies"].append(bytes(body))
                    setting = SettingsFrame()
                    setting.settings[5] = frame_size
                    conn.sendall(setting.serialize())
                    observed["sent_setting"] = True
                    for _ in range(64):
                        header = read_exact(conn, 9)
                        frame, size = Frame.parse_frame_header(memoryview(header))
                        payload = read_exact(conn, size)
                        frame.parse_body(memoryview(payload))
                        if frame.type == 4 and "ACK" in frame.flags:
                            observed["acknowledged"] = True
                            h2.send_headers(first_stream, [(":status", "200")], end_stream=True)
                            conn.sendall(h2.data_to_send())
                        elif frame.type == 9 and not payload:
                            observed["empty_frames"] += 1
                            if observed["empty_frames"] == 32:
                                return
                        elif observed["acknowledged"] and frame.type in (0, 1, 9):
                            for event in h2.receive_data(header + payload):
                                if isinstance(event, DataReceived):
                                    observed["bodies"].append(event.data)
                                elif isinstance(event, StreamEnded):
                                    h2.send_headers(event.stream_id, [(":status", "200")], end_stream=True)
                            pending = h2.data_to_send()
                            if pending:
                                conn.sendall(pending)
            except (OSError, EOFError):
                return
            finally:
                finished.set()

    monkeypatch.setattr(lab.server, "RequestHandlerClass", Peer)
    result = native_requests(library_path, lab, 2)
    assert finished.wait(3), "bounded native peer did not stop"
    assert observed["sent_setting"], "native request never reached the hostile peer"
    if 16384 <= frame_size <= (1 << 24) - 1:
        assert result == {"statuses": [200, 200], "error": None}
        assert observed["acknowledged"] and observed["empty_frames"] == 0
        assert observed["bodies"] == [b"synthetic-peer-body"] * 2
    else:
        assert not observed["acknowledged"], observed
        assert observed["empty_frames"] == 0
        assert result == {"statuses": [], "error": "ConnectionError"}
        assert observed["bodies"] == [b"synthetic-peer-body"]


def test_native_rejects_push_after_actual_advertised_enable_push_zero(library_path, lab, monkeypatch):
    observed = {"enable_push": None, "sent_push": False, "bodies": []}
    finished = threading.Event()

    class Peer(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            try:
                with self.server.tls.wrap_socket(self.request, server_side=True) as conn:
                    h2 = H2Connection(config=H2Configuration(client_side=False))
                    h2.initiate_connection()
                    conn.sendall(h2.data_to_send())
                    body = bytearray()
                    for _ in range(64):
                        data = conn.recv(65535)
                        if not data:
                            return
                        for event in h2.receive_data(data):
                            if isinstance(event, RemoteSettingsChanged) and 2 in event.changed_settings:
                                observed["enable_push"] = event.changed_settings[2].new_value
                            elif isinstance(event, DataReceived):
                                body.extend(event.data)
                            elif isinstance(event, StreamEnded):
                                observed["bodies"].append(bytes(body))
                                promise = PushPromiseFrame(event.stream_id)
                                promise.promised_stream_id = 2
                                promise.flags.add("END_HEADERS")
                                promise.data = Encoder().encode(
                                    [
                                        (":method", "GET"),
                                        (":scheme", "https"),
                                        (":authority", f"localhost:{lab.port}"),
                                        (":path", "/pushed"),
                                    ]
                                )
                                # Deliberately bypass hyper-h2's compliant refusal
                                # to push after the client disabled server push.
                                conn.sendall(promise.serialize())
                                observed["sent_push"] = True
                                h2.send_headers(event.stream_id, [(":status", "200")], end_stream=True)
                        pending = h2.data_to_send()
                        if pending:
                            conn.sendall(pending)
            except OSError:
                return
            finally:
                finished.set()

    monkeypatch.setattr(lab.server, "RequestHandlerClass", Peer)
    result = native_requests(library_path, lab, 1)
    assert finished.wait(3), "bounded native push peer did not stop"
    assert observed == {"enable_push": 0, "sent_push": True, "bodies": [b"synthetic-peer-body"]}
    assert result == {"statuses": [], "error": "ConnectionError"}, result
