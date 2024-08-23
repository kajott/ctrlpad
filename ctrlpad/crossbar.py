# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import logging
import re
import socket
import threading
import time

from .controls import bind, ControlEnvironment, Control, GridLayout, TabSheet, Button, Label

__all__ = [
    'Crossbar',
    'LightwareCrossbar',
    'ExtronCrossbar',
]

###############################################################################

class Crossbar:
    "base class for controlling video matrices ('crossbars')"

    def __init__(self, num_inputs: int = 0, num_outputs: int = 0, name: str = None):
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self.log = logging.getLogger(name or self.__class__.__name__)
        self.result = None

    def tie(self, *ties):
        """
        Send switch ('tie') commands to the crossbars.
        'ties' are tuples or lists, each of which contains at least two
        elements: the input number, followed by one or more output numbers.
        Note that input and output numbers are zero-based.
        """
        ties = [tie for tie in map(tuple, ties) if (len(tie) > 1) and (0 <= tie[0] < self.num_inputs) and all(0 <= out < self.num_outputs for out in tie[1:])]
        if not ties: return
        self.log.info("TIE: %r", ties)
        self.on_tie(ties)

    def on_tie(self, ties):
        """actual tie implementation; overridden by derived classes.
        'ties' is guaranteed to be non-empty, and each entry is guaranteed to
        be valid (at least one output, no invalid input/output numbers)
        """
        time.sleep(0.02)  # act as if tying takes some time

    @staticmethod
    def flatten_ties(ties):
        "converts a list of variable-length ties into ties of length 2"
        for tie in ties:
            for out in tie[1:]:
                yield (tie[0], out)

    def clear_status(self):
        "clear the last command's status"
        self.result = None
    def notify_success(self):
        "set the last command's status to 'success'"
        self.result = True
    def notify_error(self):
        "set the last command's status to 'error'"
        self.result = False

    def wait(self, timeout=None):
        "wait until an asynchronous command completed and return its status"
        t1 = None
        while self.result is None:
            if timeout:
                if not t1: t1 = time.time() + timeout
                elif time.time() > t1: break
            time.sleep(0.05)
        return self.result

    def geometry_known(self) -> bool:
        "query if the number of inputs and outputs is already known"
        return bool(self.num_inputs and self.num_outputs)

    def set_geometry(self, num_inputs: int = 0, num_outputs: int = 0):
        "set the number of inputs and outputs, if not already set"
        if num_inputs  and not(self.num_inputs):  self.num_inputs  = num_inputs
        if num_outputs and not(self.num_outputs): self.num_outputs = num_outputs

    def set_geometry_str(self, s: str):
        """set the number of inputs and outputs, if not already set,
        from a string containing a substring like '8x16'"""
        if isinstance(s, bytes): s = s.decode('ascii', 'replace')
        if m := re.search(r'(\d+)[xX](\d+)', s):
            self.set_geometry(*map(int, m.groups()))

###############################################################################

    @staticmethod
    def schemed_name(scheme: str, num: int, names=None, format=None) -> str:
        if   scheme == '1': s_num = str(num + 1)
        elif scheme == 'A': s_num = chr(num + 65)
        elif scheme == 'a': s_num = chr(num + 97)
        else: s_num = str(num)
        if names and isinstance(names, dict):
            name = names.get(s_num)
        elif names and (0 <= num < len(names)):
            name = names[num]
        else:
            name = None
        if not name:
            return s_num
        if format is None:
            return name
        if len(format) & 1:
            return format + s_num + format + "\n" + name
        half = len(format) // 2
        return format[:half] + s_num + format[half:] + "\n" + name

    def create_ui(self, input_scheme: str = '1', output_scheme: str = '1',
                        input_names=None,        output_names=None,
                        input_format=None,       output_format=None):
        """
        Create a GridLayout for controlling the crossbar.

        Optional arguments:
        - input_scheme: the crossbar's input naming scheme ('1'=numbers, 'A'=letters)
        - input_names: user-assigned names/labels for the inputs;
                       either a list or tuple, or a str->str dictionary
        - input_format: if a name has been assigned and this is not None,
                        the number or letter of the input is displayed as well;
                        if the format string has an even length, the first half
                        will be prepended to the number/letter, and the second
                        half will be appended; if the format string length is
                        odd, it will be prepended *and* appended
        - output_scheme: as input_scheme, but for the outputs
        - output_names:  as input_names,  but for the outputs
        - output_format: as input_format, but for the outputs
        """
        page = GridLayout()

        page.put(0,0, self.num_inputs * 2, 1, Label("INPUTS", valign=1, bar=3))
        page.locate(0,1)
        self.btn_in = [page.pack(2,2,
            Button(self.schemed_name(input_scheme, i, input_names, input_format),
                   manual=True, cmd=self._on_in_btn_click))
            for i in range(self.num_inputs)]

        page.put(0,3, self.num_outputs * 2, 1, Label("OUTPUTS", valign=1, bar=3))
        page.locate(0,4)
        self.btn_out = [page.pack(2,2,
            Button(self.schemed_name(output_scheme, i, output_names, output_format),
                   toggle=True))
            for i in range(self.num_outputs)]

        nbuttons = max(self.num_inputs, self.num_outputs)
        page.put(nbuttons * 2 - 4, 6, 4,1, Label("CONTROL", valign=1, bar=3))
        page.put(nbuttons * 2 - 4, 7, 2,2, Button("CANCEL", hue=30, sat=0.1, cmd=self._on_cancel_click))
        page.put(nbuttons * 2 - 2, 7, 2,2, Button("TAKE", hue=142, sat=0.1, cmd=self._on_take_click))
        return page

    def add_ui_page(self, parent: TabSheet, title: str = None, *args, **kwargs):
        """
        add a page to a TabSheet for controlling the crossbar;
        uses the same options as create_ui()
        """
        return parent.add_page(self.create_ui(*args, **kwargs), title or self.log.name.split('-', 1)[0])

    def _clear_buttons(self):
        for btn in self.btn_in:  btn.state = None
        for btn in self.btn_out: btn.state = None

    def _on_in_btn_click(self, env: ControlEnvironment, btn: Control):
        was_active = btn.state
        self._clear_buttons()
        if not was_active: btn.state = 'active'

    def _on_cancel_click(self, env: ControlEnvironment, btn: Control):
        self._clear_buttons()

    def _on_take_click(self, env: ControlEnvironment, btn: Control):
        tie = [i for i, btn in enumerate(self.btn_in) if btn.state]
        if len(tie) == 1:
            tie += [i for i, btn in enumerate(self.btn_out) if btn.state]
            self.tie(tie)
        self._clear_buttons()

###############################################################################

class TCPIPCrossbar(Crossbar):
    "base class for controlling video matrices via TCP/IP"
    default_port = 0  # overridden in derived classes

    def __init__(self, ip: str, port: int = 0, num_inputs: int = 0, num_outputs: int = 0, timeout: float = 0.1, name: str = None):
        super().__init__(num_inputs, num_outputs, name=(name or (self.__class__.__name__.replace("Crossbar","") + "-" + ip)))
        self.ip = ip
        self.port = port or self.default_port
        if not self.port: raise ValueError("no port specified")
        self.timeout = timeout
        self.sock = None
        self.cancel = False
        self.receiver = None
        self.connect()

    def _receiver_thread(self):
        buf = b''
        self.log.debug("receiver thread started")
        while not self.cancel:
            try:
                buf += self.sock.recv(1024).replace(b'\r', b'\n')
            except EnvironmentError:
                pass
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                if line:
                    self.log.debug("RECV %r", line)
                    self.on_receive(line)
        self.log.debug("receiver thread exited (cancel=%r)", self.cancel)

    def connect(self):
        "establish a connection to the device"
        if self.sock: return
        self.log.info("connecting to %s:%d", self.ip, self.port)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
        except EnvironmentError as e:
            self.log.error("connection failed - %s", str(e))
            self.sock = None
            return
        self.cancel = False
        self.receiver = threading.Thread(target=self._receiver_thread, name=self.log.name+"-ReceiverThread")
        self.receiver.daemon = True
        self.receiver.start()
        self.clear_status()
        self.on_connect()

    def disconnect(self):
        "disconnect from the device"
        if not self.sock: return
        self.cancel = True
        self.on_disconnect()
        self.receiver.join(self.timeout * 2)
        self.receiver = None
        self.sock = None
        self.log.info("disconnected from %s:%d", self.ip, self.port)

    def __del__(self):
        self.disconnect()

    def send(self, data, allow_reconnect=True, wait=True):
        "send a command, and optionally wait for a response"
        if not self.sock:
            self.connect()
            res = self.wait(self.timeout)
            if self.sock and not(res):
                self.log.error("reconnect didn't succeed, trying to send anyway")
            if not self.sock:
                self.log.error("reconnect attempt failed, can't send command")
                return False
        self.clear_status()
        if isinstance(data, str):
            data = data.encode('ascii', 'replace')
        self.log.debug("SEND %r", data)
        try:
            self.sock.sendall(data)
        except EnvironmentError as e:
            if allow_reconnect:
                self.log.error("connection lost (%s), reconnecting and retrying", str(e))
                self.disconnect()
                return self.send(data, allow_reconnect=False, wait=wait)
            else:
                self.log.error("connection lost (%s)", str(e))
                self.disconnect()
                return False
        if wait:
            res = self.wait(self.timeout)
            if res is None:
                if allow_reconnect:
                    self.log.error("no reaction from device, reconnecting and retrying")
                    self.disconnect()
                    return self.send(data, allow_reconnect=False, wait=wait)
                else:
                    self.log.error("no reaction from device")
            elif not res:
                self.log.error("device reports error")
            return res

    def on_connect(self):
        "callback after connecting; overridden in derived classes"
        self.notify_success()

    def on_disconnect(self):
        "callback before disconnecting; overridden in derived classes"
        pass

    def on_receive(self, line):
        "callback after receiving a response line; overridden in derived classes"
        pass

###############################################################################

class LightwareCrossbar(TCPIPCrossbar):
    "crossbar switch using the Lightware LW1 protocol"
    # see: https://lightware.com/products/matrices-switchers/mx8x8hdmi-pro
    # in particular: https://lightware.com/media/lightware/User_Manuals/MX8x8HDMI-Pro/MX8x8HDMI-Pro_Series_UsersManual.html#_C7
    default_port = 10001

    def on_connect(self):
        if not self.geometry_known():
            self.send(b'{i}')
        else:
            self.notify_success()

    def receive(self, line):
        if line.startswith(b'(') and line.endswith(b')'):
            if line.startswith(b'(MX'):
                self.set_geometry_str(line)
            self.notify_success()

    def on_tie(self, ties):
        self.send(b''.join(b'{%d@%d}\r\n' % (pin+1, pout+1) for pin, pout in self.flatten_ties(ties)))

class ExtronCrossbar(TCPIPCrossbar):
    "crossbar switch using the Extron DXP SIS protocol"
    # see: https://www.extron.com/product/dxphdmi
    # in particular: https://media.extron.com/public/download/files/userman/68-1370-50_C_DXP_DVI_Pro_HDMI_SUG.pdf
    default_port = 23

    def on_connect(self):
        if not self.geometry_known():
            self.send(b'I')
        else:
            self.notify_success()

    def on_receive(self, line):
        line = line.lower()
        if line.startswith((b"login ", b"qik", b"out")):
            self.notify_success()
        elif line.startswith(b'v') and line[1:2].isdigit() and (b' a' in line):
            self.set_geometry_str(line)
            self.notify_success()

    def on_tie(self, ties):
        if (len(ties) == 1) and (len(ties[0]) == 2):
            self.send(b'%d*%d!' % (ties[0][0]+1, ties[0][1]+1))
        else:
            self.send(b'\x1b+Q' + b''.join(b'%d*%d!' % (pin+1, pout+1) for pin, pout in self.flatten_ties(ties)) + b'\r\n')

###############################################################################

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    dev = ExtronCrossbar("127.0.0.1", 2323)
    #dev = ExtronCrossbar("10.0.1.88")
    try:
        while True:
            ties = input("ties> ")
            dev.tie(*[[int(p,36)-1 for p in tie] for tie in ties.split(',')])
    except (KeyboardInterrupt, EOFError):
        pass
    dev.disconnect()
