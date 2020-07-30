def check_login(func):
    def inner(self, *args, **kwargs):
        assert self.user_id, "Check login failed"
        return func(self, *args, **kwargs)

    return inner
