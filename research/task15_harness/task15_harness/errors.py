class ControlError(Exception):
    """Stable error classification for CLI, tests and audit logs."""
    def __init__(self, code: str, detail: str) -> None:
        self.code, self.detail = code, detail
        super().__init__(f'{code}: {detail}')


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise ControlError(code, detail)
