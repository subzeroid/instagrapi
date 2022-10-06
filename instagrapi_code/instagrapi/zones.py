from datetime import timedelta, tzinfo


class CET(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=1)

    def dst(self, dt):
        return timedelta(hours=2)


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)
