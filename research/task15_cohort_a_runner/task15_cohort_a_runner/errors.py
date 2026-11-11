class RunnerError(Exception):
    def __init__(self, code, detail=''):
        self.code = code
        self.detail = str(detail)
        super().__init__(f'{code}: {detail}')


def require(condition, code, detail=''):
    if not condition:
        raise RunnerError(code, detail)


class Interrupted(RunnerError):
    def __init__(self, detail='synthetic session interrupted'):
        super().__init__('SESSION_INTERRUPTED', detail)
