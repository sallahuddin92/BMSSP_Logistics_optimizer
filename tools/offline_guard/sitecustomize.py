import socket

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex


def _guarded_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Offline validation: outbound sockets disabled")
    return _original_connect(self, address)


def _guarded_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Offline validation: outbound sockets disabled")
    return _original_connect_ex(self, address)


socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex
