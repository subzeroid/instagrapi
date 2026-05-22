from instagrapi.realtime import RealtimeClient


class RealtimeMixin:
    realtime = None

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
