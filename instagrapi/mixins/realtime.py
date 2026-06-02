from instagrapi.realtime import FbnsClient, FbnsDeviceAuth, RealtimeClient


class RealtimeMixin:
    realtime = None
    fbns = None

    def realtime_client(self, transport=None) -> RealtimeClient:
        return RealtimeClient(self, transport=transport)

    def realtime_connect(self, transport=None) -> RealtimeClient:
        if not self.realtime:
            self.realtime = self.realtime_client(transport=transport)
        elif transport is not None:
            self.realtime.transport = transport
        self.realtime.connect()
        return self.realtime

    def realtime_disconnect(self) -> None:
        if self.realtime:
            self.realtime.disconnect()
            self.realtime = None

    def realtime_on(self, event: str, handler) -> None:
        if not self.realtime:
            self.realtime = self.realtime_client()
        self.realtime.on(event, handler)

    def realtime_read_once(self):
        if not self.realtime:
            raise RuntimeError("Realtime client is not connected")
        return self.realtime.read_once()

    def realtime_ping(self) -> bool:
        if not self.realtime:
            raise RuntimeError("Realtime client is not connected")
        return self.realtime.ping()

    def fbns_client(self, transport=None, auth: FbnsDeviceAuth = None) -> FbnsClient:
        return FbnsClient(self, transport=transport, auth=auth)

    def fbns_connect(self, transport=None, auth: FbnsDeviceAuth = None, register: bool = True) -> FbnsClient:
        if not self.fbns:
            self.fbns = self.fbns_client(transport=transport, auth=auth)
        else:
            if transport is not None:
                self.fbns.transport = transport
            if auth is not None:
                self.fbns.auth = auth
        self.fbns.connect(register=register)
        return self.fbns

    def fbns_disconnect(self) -> None:
        if self.fbns:
            self.fbns.disconnect()
            self.fbns = None

    def fbns_on(self, event: str, handler) -> None:
        if not self.fbns:
            self.fbns = self.fbns_client()
        self.fbns.on(event, handler)

    def fbns_read_once(self):
        if not self.fbns:
            raise RuntimeError("FBNS client is not connected")
        return self.fbns.read_once()

    def fbns_ping(self) -> bool:
        if not self.fbns:
            raise RuntimeError("FBNS client is not connected")
        return self.fbns.ping()
