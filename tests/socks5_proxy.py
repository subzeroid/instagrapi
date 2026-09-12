"""Authenticated SOCKS5 fixture restricted to one loopback TLS server."""

import select
import socket
import socketserver
import threading


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise OSError("Incomplete SOCKS5 message")
        data.extend(chunk)
    return bytes(data)


class LoopbackSocksProxy:
    def __init__(self, lab):
        self.records = []
        records = self.records

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                conn = self.request
                conn.settimeout(3)
                try:
                    version, count = read_exact(conn, 2)
                    if version != 5 or 2 not in read_exact(conn, count):
                        return
                    conn.sendall(b"\x05\x02")
                    version, length = read_exact(conn, 2)
                    username = read_exact(conn, length)
                    password = read_exact(conn, read_exact(conn, 1)[0])
                    if version != 1 or username != b"synthetic" or password != b"password":
                        conn.sendall(b"\x01\x01")
                        return
                    conn.sendall(b"\x01\x00")
                    # Domain-name addressing proves that socks5h defers DNS.
                    if read_exact(conn, 4) != b"\x05\x01\x00\x03":
                        return
                    hostname = read_exact(conn, read_exact(conn, 1)[0]).decode("ascii")
                    port = int.from_bytes(read_exact(conn, 2), "big")
                    if hostname != "localhost" or port != lab.port:
                        return
                    records.append({"hostname": hostname, "port": port, "authenticated": True})
                    with socket.create_connection(("127.0.0.1", lab.port), timeout=3) as upstream:
                        conn.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")
                        while True:
                            ready, _, _ = select.select([conn, upstream], [], [], 3)
                            if not ready:
                                return
                            for source in ready:
                                data = source.recv(65536)
                                if not data:
                                    return
                                (upstream if source is conn else conn).sendall(data)
                except (OSError, UnicodeError):
                    return

        class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
            daemon_threads = True
            block_on_close = False

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
