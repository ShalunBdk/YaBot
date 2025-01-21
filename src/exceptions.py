class AccessException(Exception):
    detail = "Access error"

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)

class Has2FAException(Exception):
    detail = "2FA error"

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)