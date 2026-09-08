"""Real loopback TLS/H2 fixture; it never opens an upstream connection."""

import base64
import gzip
import socket
import socketserver
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import DataReceived, RequestReceived, StreamEnded

LAB_HOST = "localhost"
LAB_JSON = b'{"status":"lab-ok"}'


def peek_protocols(sock):
    """Read ALPN names from the actual ClientHello without consuming it."""
    header = sock.recv(5, socket.MSG_PEEK | socket.MSG_WAITALL)
    if len(header) != 5 or header[0] != 22:
        raise ValueError("Expected a TLS handshake")
    size = 5 + int.from_bytes(header[3:5], "big")
    record = sock.recv(size, socket.MSG_PEEK | socket.MSG_WAITALL)
    if len(record) != size or record[5] != 1:
        raise ValueError("Expected one complete ClientHello")
    hello = record[9:]
    offset = 34
    offset += 1 + hello[offset]
    offset += 2 + int.from_bytes(hello[offset : offset + 2], "big")
    offset += 1 + hello[offset]
    end = offset + 2 + int.from_bytes(hello[offset : offset + 2], "big")
    offset += 2
    protocols = []
    while offset < end:
        kind = int.from_bytes(hello[offset : offset + 2], "big")
        length = int.from_bytes(hello[offset + 2 : offset + 4], "big")
        value = hello[offset + 4 : offset + 4 + length]
        offset += 4 + length
        if kind == 16:
            index = 2
            while index < len(value):
                length = value[index]
                protocols.append(value[index + 1 : index + 1 + length].decode("ascii"))
                index += 1 + length
    if offset != end or end != len(hello):
        raise ValueError("Malformed ClientHello")
    return protocols


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        raw = self.request
        raw.settimeout(5)
        try:
            offers = peek_protocols(raw)
            conn = self.server.tls.wrap_socket(raw, server_side=True)
        except (OSError, ValueError, ssl.SSLError):
            return
        with conn:
            with self.server.lock:
                self.server.connection_count += 1
                connection_id = self.server.connection_count
            h2 = H2Connection(config=H2Configuration(client_side=False, header_encoding="utf-8"))
            h2.initiate_connection()
            pending = {}
            try:
                conn.sendall(h2.data_to_send())
                while data := conn.recv(65535):
                    for event in h2.receive_data(data):
                        if isinstance(event, RequestReceived):
                            pending[event.stream_id] = {
                                "headers": event.headers,
                                "body": bytearray(),
                            }
                        elif isinstance(event, DataReceived):
                            pending[event.stream_id]["body"].extend(event.data)
                            h2.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                        elif isinstance(event, StreamEnded):
                            request = pending.pop(event.stream_id)
                            record = {
                                "connection_id": connection_id,
                                "stream_id": event.stream_id,
                                "alpn_offers": offers,
                                "negotiated": conn.selected_alpn_protocol(),
                                "headers": request["headers"],
                                "body_base64": base64.b64encode(request["body"]).decode(),
                            }
                            with self.server.lock:
                                self.server.records.append(record)
                            path = dict(request["headers"])[":path"]
                            if path == "/lab/drop":
                                return
                            status, response_headers, body = self.response(path)
                            declared_length = len(body) + (10 if path.endswith("/lab/partial") else 0)
                            headers = [
                                (":status", str(status)),
                                ("content-length", str(declared_length)),
                                *response_headers,
                            ]
                            if dict(request["headers"])[":method"] == "HEAD":
                                body = b""
                            h2.send_headers(event.stream_id, headers, end_stream=not body)
                            if body:
                                h2.send_data(event.stream_id, body, end_stream=True)
                    outgoing = h2.data_to_send()
                    if outgoing:
                        conn.sendall(outgoing)
            except (OSError, ssl.SSLError):
                return

    @staticmethod
    def response(path):
        if path.endswith("/lab/rate-limit"):
            return 429, [("content-type", "text/plain"), ("retry-after", "7")], b""
        if path == "/lab/slow":
            time.sleep(0.25)
        body = gzip.compress(LAB_JSON, mtime=0)
        return (
            200,
            [
                ("content-type", "application/json"),
                ("content-encoding", "gzip"),
                ("set-cookie", "first_cookie=one; Path=/; Secure"),
                ("set-cookie", "second_cookie=two; Path=/; Secure"),
            ],
            body,
        )


class TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True


def _write_certificates(artifacts):
    root_key = ec.generate_private_key(ec.SECP256R1())
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "curl adapter lab CA")])
    now = datetime.now(timezone.utc)
    root = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, LAB_HOST)])
    leaf = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(LAB_HOST)]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=True,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    ca_path = artifacts / "lab-ca.pem"
    cert_path = artifacts / "lab-leaf.pem"
    key_path = artifacts / "lab-leaf-key.pem"
    ca_path.write_bytes(root.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    ca_path.chmod(0o600)
    cert_path.chmod(0o600)
    key_path.chmod(0o600)
    return ca_path, cert_path, key_path


class LoopbackServer:
    def __init__(self, artifacts):
        ca_path, cert_path, key_path = _write_certificates(artifacts)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.set_alpn_protocols(["h2"])
        context.load_cert_chain(cert_path, key_path)
        self.server = TCPServer(("127.0.0.1", 0), Handler)
        self.server.tls = context
        self.server.lock = threading.Lock()
        self.server.connection_count = 0
        self.server.records = []
        self.port = self.server.server_address[1]
        self.records = self.server.records
        self.ca_path = ca_path
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
