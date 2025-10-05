import serial

port = "/dev/ttyUSB0"
baud = 9600
timeout = 0.5

_conn = None

def send(cmd):
    global _conn
    if not _conn:
        _conn = serial.serial_for_url(port, baudrate=baud, bytesize=8, parity='N', stopbits=1, timeout=timeout)
    while _conn.in_waiting:
        _conn.read(1)
    if isinstance(cmd, str):
        cmd = cmd.encode()
    _conn.write(cmd)
    res = b''
    while True:
        c = _conn.read(1)
        if not c: return res
        res += c
