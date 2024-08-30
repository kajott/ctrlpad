# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import logging
import os
import re
import socket
import threading
import time

from .renderer import Renderer
from .controls import ControlEnvironment, Control, Button
from . import color

###############################################################################

class MPDClient:
    "MPD (Music Player Daemon) client"

    def __init__(self, ip: str = "localhost", port: int = 6600, timeout: float = 0.1, name: str = None):
        self.log = logging.getLogger(name or ("MPD-" + ip))
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.lock = threading.Lock()
        self.cancel = False
        self.async_cmds = []
        self.async_quiet = False
        self.async_result = None
        self.async_trigger = threading.Event()
        self.async_done = threading.Event()
        self.async_done.set()
        self.async_thread = threading.Thread(target=self._async_thread_func, name=self.log.name+"-AsyncThread")
        self.async_thread.daemon = True
        self.async_thread.start()
        self.fade_trigger = threading.Event()
        self.fade_thread = threading.Thread(target=self._fade_thread_func, name=self.log.name+"-FadeThread")
        self.fade_thread.daemon = True
        self.fade_thread.start()
        self.fade_direction = 0  # 0 = auto, +1 = fade in, -1 = fade out
        self.fade_duration = 1.0
        self.fade_buttons = []
        self.fade_notify_window = None
        self.fading = False
        self.current_volume = 100
        self.target_volume = 100
        self.playing = False
        self.connect()

    def __del__(self):
        self.cancel = True
        self.fade_trigger.set()
        self.async_trigger.set()
        self.async_thread.join(self.timeout)
        self.fade_thread.join(self.timeout)
        self.disconnect()

    @property
    def connected(self) -> bool:
        return bool(self.sock)

    def connect(self):
        "connect to MPD"
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
        res = dict(self._read_response())
        if "OK" in res:
            self.log.info("connected to %s", res['OK'])
        else:
            self.log.error("invalid response from server")
            self.sock.close()
            self.sock = None

    def disconnect(self):
        "disconnect from MPD"
        if not self.sock: return
        try:
            self.sock.close()
        except EnvironmentError:
            pass
        self.sock = None
        self.log.info("disconnected from %s:%d", self.ip, self.port)

    def _read_response(self, quiet: bool = False):
        if not self.sock: return
        buf = b''
        end = False
        while not end:
            sep = buf.find(b'\n')
            if sep < 0:
                try:
                    block = self.sock.recv(4096)
                except EnvironmentError:
                    self.disconnect()
                    block = b''
                if block:
                    buf += block
                    continue
                else:
                    sep = len(buf)
                    end = True
            line = buf[:sep].decode('utf-8', 'replace')
            buf = buf[sep+1:]
            if not quiet:
                self.log.debug("RECV '%s'", line.rstrip())
            if line.startswith("OK"):  yield ("OK",  line[2:].strip()); break
            if line.startswith("ACK"): yield ("ACK", line[3:].strip()); break
            try:
                k, v = map(str.strip, line.split(':', 1))
            except ValueError:
                k, v = None, line
            try:
                v = int(v)
            except ValueError:
                try:
                    v = float(v)
                except ValueError:
                    pass
            yield (k, v)

    def send_commands(self, *cmds, allow_reconnect: bool = True, quiet: bool = False) -> dict:
        "send one or more commands synchronously; return last command's status"
        if not self.sock:
            self.connect()
        with self.lock:
            for cmd in cmds:
                if self.cancel or not(self.sock):
                    return {}
                if not quiet:
                    self.log.debug("SEND '%s'", cmd)
                try:
                    self.sock.sendall(cmd.encode('utf-8') + b'\n')
                except EnvironmentError:
                    self.disconnect()
                    if allow_reconnect:
                        return self.send_commands(*cmds, allow_reconnect=False, quiet=quiet)
                res = dict(self._read_response(quiet=quiet))
                if (cmd == 'status') and res:
                    self.current_volume = res.get('volume', self.current_volume)
                    self.playing = res.get('state') == 'play'
            return res

    def send_commands_async(self, *cmds, quiet: bool = False):
        "send one or more commands in a background thread"
        self.get_async_result(wait=True)
        self.async_result = None
        self.async_cmds = cmds
        self.async_quiet = quiet
        self.async_done.clear()
        self.async_trigger.set()

    def get_async_result(self, wait: bool = True):
        "get the result of the last asynchronously executed command"
        if wait:
            self.async_done.wait()
        res = self.async_result
        if res: self.async_result = None
        return res

    def _async_thread_func(self):
        while not self.cancel:
            self.async_trigger.wait()
            self.async_trigger.clear()
            if self.async_cmds:
                cmds = self.async_cmds
                self.async_cmds = None
                self.async_result = self.send_commands(*cmds, quiet=self.async_quiet)
            self.async_done.set()

    def _fade_thread_func(self):
        while not self.cancel:
            self.fade_trigger.wait()
            self.fading = True
            self.fade_trigger.clear()
            if self.cancel: return

            # update UI
            for btn in self.fade_buttons:
                if btn.fade_duration == self.fade_duration:
                    btn.state = 'active'
            if not(self.cancel) and self.fade_notify_window:
                self.fade_notify_window.redraw()

            # get current status, decide on fade direction, set up parameters
            self.send_commands('status', quiet=True)
            if not self.fade_direction:
                self.fade_direction = -1 if self.playing else +1
            start_cmds, end_cmds = [], []
            start_volume = current_volume = self.current_volume
            if self.fade_direction > 0:  # fade in
                fade_type = "in"
                end_volume = self.target_volume
                if not self.playing: start_cmds = ['play']
            else:  # fade out
                fade_type = "out"
                end_volume = 0
                if self.playing: end_cmds = ['pause 1']

            # perform actual fade
            if self.fading and self.connected and (start_volume != end_volume) and (self.fade_duration > 0.0):
                duration = self.fade_duration
                self.log.info("starting %.1f-second fade-%s", duration, fade_type)
                delay = duration / abs(start_volume - end_volume)
                t0 = time.time()
                self.send_commands(*([f'setvol {current_volume}'] + start_cmds), quiet=True)
                while self.fading and self.connected and not(self.cancel):
                    time.sleep(delay)
                    t = max(0.0, min(1.0, (time.time() - t0) / duration))
                    new_volume = round(start_volume * (1.0 - t) + end_volume * t)
                    if new_volume != current_volume:
                        current_volume = new_volume
                        cmd = f'setvol {current_volume}'
                        if current_volume == end_volume:
                            self.send_commands(cmd, *end_cmds, quiet=True)
                            break
                        else:
                            self.send_commands(cmd, quiet=True)

            # finish fade
            self.log.info("fade-%s stopped", fade_type)
            self.send_commands('status', quiet=True)
            for btn in self.fade_buttons:
                if btn.state == 'active':
                    btn.state = None
            if not(self.cancel) and self.fade_notify_window:
                self.fade_notify_window.redraw()
            self.fading = False

    def start_fade(self, direction: int = 0, duration: float = 0.0):
        "start a fading operation; direction=0 = auto, +1 = fade in, -1 = fade out"
        self.stop_fade()
        if duration > 0.0:
            self.fade_duration = duration
        self.fade_direction = direction
        self.fade_trigger.set()

    def stop_fade(self):
        "stop a fading operation"
        self.fade_trigger.clear()
        self.fading = False

    def _on_fade_button_click(self, env: ControlEnvironment, btn: Control):
        self.fade_notify_window = env.window
        if not self.fading:
            # no fade in progress -> start fading
            self.start_fade(0, btn.fade_duration)
        elif self.fade_duration == btn.fade_duration:
            # click on same fade button -> stop fading
            self.stop_fade()
        else:
            # click on other fade button -> re-trigger fading with new duration
            self.start_fade(self.fade_direction, btn.fade_duration)

    def create_fade_button(self, duration: float, text: str, **style) -> Button:
        "create a UI button that starts/stops a fade operation"
        btn = Button(text, cmd=self._on_fade_button_click, manual=True, **style)
        btn.fade_duration = duration
        self.fade_buttons.append(btn)
        return btn

    @staticmethod
    def shuffle_folders(*folders, single: bool = False):
        "generate commands to play one or more folders in shuffled order"
        return ['stop', 'clear', 'random 0'] \
             +(['single 1', 'repeat 0'] if single else ['single 0', 'repeat 1']) \
             + [f'add "{f}"' for f in folders] \
             + ['shuffle', 'play']

    def _restore_volume_if_not_playing_and(self, cmd: str):
        if self.playing:
            self.send_commands(cmd)
        else:
            self.send_commands('setvol 0', cmd, f'setvol {self.target_volume}')

    def play(self):
        "start or continue playback"
        self._restore_volume_if_not_playing_and('play')
    def pause(self):
        "pause playback"
        self.send_commands('pause 1')
    def prev(self):
        "navigate to the previous track"
        self._restore_volume_if_not_playing_and('previous')
    def next(self):
        "navigate to the next track"
        self._restore_volume_if_not_playing_and('next')
    def seek_rel(self, delta_seconds: int):
        "seek forward (positive) or backward (negative)"
        self.send_commands(f'seekcur {delta_seconds:+d}')
    def seek_bwd(self):
        "seek 10 seconds backward"
        self.seek_rel(-10)
    def seek_fwd(self):
        "seek 10 seconds forward"
        self.seek_rel(+10)

###############################################################################

class MPDControl(Control):
    "control widget to show status of an MPD client"

    # button registry:    [0]       [1]        [2]         [3]       [4]         [5]
    button_cmds        = ('play',   'pause',   'prev',     'next',   'seek_bwd', 'seek_fwd')
    button_positions   = (2,        2,         0,          4,        1,          3)
    button_icons       = ("\u23f5", "\u23f8",  "\u23ee",   "\u23ed", "\u23ea",   "\u23e9")
    button_set_playing = (1,2,3,4,5)
    button_set_paused  = (0,2,3,4,5)
    buttons_that_navigate = (0,2,3)

    def __init__(self, mpd: MPDClient, **style):
        """
        Instantiate the control with the following (mostly optional) parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - mpd = the MPDClient instance to control
        - background  = background color
        - font        = metadata text font
        - size      ~ = default text size
        - margin    ~ = outer margin
        - icondist  ~ = distance between icon and text
        - radius    ~ = rounding radius
        - color       = text color
        - icons       = title/artist/album icon color
        - buttons     = button color
        - time_color  = color of time and track number displays
        - time_size   = relatize size of the time and track number displays
        - alpha       = transparency of disabled buttons
        - controls    = size (height) of the controls relative to the metadata
                        text lines (1.0=same as text)
        """
        super().__init__(**style)
        self.mpd = mpd
        self.button_set = self.button_set_paused
        self.next_update = 0
        self.waiting_for_data = None
        self.was_connected = False
        self._on_connection_lost()

    def _on_connection_lost(self):
        self.text = [""] * 3
        self.track = "\u2013/\u2013"
        self.time = "\u2013/\u2013"
        self.status_data = { 'status': {}, 'currentsong': {} }
        self.curr_songid = -1

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        self.bg_color = color.parse(self.get('background', "111"))
        self.bg_radius = env.scale(self.get('radius', 20))
        self.c_text = color.parse(self.get('color', "fff"))
        self.c_icon = color.parse(self.get('icons', "888"))
        self.c_time = color.parse(self.get('time_color', "ccc"))
        c = color.parse(self.get('buttons', "fff"))
        self.c_buttons = [color.alpha(c, self.get('alpha', 0.5)), c]
        base_size = env.scale(self.get('size', 50))
        margin = env.scale(self.get('margin', 20))
        x0 += margin
        y0 += margin
        x1 -= margin
        y1 -= margin
        row_height = int((y1 - y0) / (3 + self.get('controls', 1.0)))

        # layout metadata fields
        env.renderer.set_font("symbol")
        self.icon_layout = []
        for i, icon in enumerate("\u266B\u263A\u2680"):
            self.icon_layout.extend(env.renderer.fit_text_in_box(
                x0, y0 + i * row_height, x0 + row_height, y0 + i * row_height + row_height, base_size,
                icon, 0,2
            ))
        env.renderer.set_font(self.get('font'))
        text_x0 = max(x1 for x0,y0,x1,y1,sz,tx in self.icon_layout) \
                + env.scale(self.get('icondist', 20))
        self.text_layout = []
        for item in self.text:
            self.text_layout.extend(env.renderer.fit_text_in_box(
                text_x0, y0, x1, y0 + row_height, base_size,
                item, 0,2
            ))
            y0 += row_height

        # layout buttons
        env.renderer.set_font("symbol")
        row_height = y1 - y0
        bx0 = (x0 + x1 - 5 * row_height) // 2
        self.button_rect = [(bx0 + i * row_height, y0, bx0 + (i + 1) * row_height, y1) for i in self.button_positions]
        self.button_layout = [env.renderer.fit_text_in_box(*coords, row_height, icon)
                              for coords, icon in zip(self.button_rect, self.button_icons)]

        # layout track/time text
        env.renderer.set_font(self.get('font'))
        self.tt_size = int(min(row_height, base_size) * self.get('time_size', 0.75))
        self.tt_x0 = x0
        self.tt_x1 = x1
        self.tt_y = (y0 + y1 - env.renderer.text_line_height(self.tt_size)) / 2

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        # process aynchronously requested data
        next_frame_after = 1.0
        if self.waiting_for_data:
            #self.mpd.log.debug("waiting for %s", self.waiting_for_data)
            res = self.mpd.get_async_result()
            if res:
                #self.mpd.log.debug("received %s", self.waiting_for_data)
                slot = self.waiting_for_data
                self.status_data[slot] = res
                self.waiting_for_data = None
                if slot == 'status':
                    songid = res.get('songid', self.curr_songid)
                    if songid != self.curr_songid:
                        self.curr_songid = songid
                        self._request_data('currentsong')
                    track = self.status_data['status'].get('song', "\u2013")
                    if isinstance(track, int): track = str(track + 1)
                    self.track = track + " / " + \
                                 str(self.status_data['status'].get('playlistlength', "\u2013"))
                    elapsed = self.status_data['status'].get('elapsed')
                    if elapsed:
                        next_frame_after = 1.0 - (elapsed - int(elapsed))
                    self.time = self._fmt_time(elapsed) + " / " + \
                                self._fmt_time(self.status_data['status'].get('duration'))
                    self.button_set = self.button_set_playing if self.mpd.playing else self.button_set_paused
                elif slot == 'currentsong':
                    filename = os.path.splitext(os.path.basename(self.status_data['currentsong'].get('file', "")))[0]
                    parts = [part.replace("_", " ").strip().title() for part \
                             in re.split(r'-{2,}|[ _]-+[ _]', filename)]
                    if len(parts) == 1:   fallback = [parts[0], "", ""]
                    elif len(parts) == 2: fallback = [parts[1], parts[0], ""]
                    else:                 fallback = [parts[2], parts[0], parts[1]]
                    self.text = [self.status_data['currentsong'].get(k, fb) \
                                 for k, fb in zip(('Title', 'Artist', 'Album'), fallback)]
                    self.layout(env, x0,y0,x1,y1)
        if self.was_connected and not(self.mpd.connected):
            self._on_connection_lost()
            self.layout(env, x0,y0,x1,y1)

        # draw the control
        env.renderer.box(x0, y0, x1, y1, self.bg_color, radius=self.bg_radius)
        env.renderer.set_font(self.get('font'))
        env.renderer.fitted_text(self.text_layout, self.c_text)
        env.renderer.text_line(self.tt_x0, self.tt_y, self.tt_size, self.track, self.c_time)
        env.renderer.text_line(self.tt_x1, self.tt_y, self.tt_size, self.time, self.c_time, align=1)
        env.renderer.set_font('symbol')
        env.renderer.fitted_text(self.icon_layout, self.c_icon)
        c = self.c_buttons[int(self.mpd.connected)]
        for i in self.button_set:
            env.renderer.fitted_text(self.button_layout[i], c)

        # schedule metadata update
        if self.mpd.connected and (env.draw_time >= self.next_update):
            self.next_update = env.draw_time + 0.1
            self._request_data('status')
        if self.waiting_for_data:
            env.window.request_frames(1)
        self.was_connected = self.mpd.connected
        if self.mpd.connected:
            return next_frame_after

    def on_click(self, env: ControlEnvironment, x: int, y: int):
        if not self.mpd.connected: return
        for btn in self.button_set:
            x0,y0, x1,y1 = self.button_rect[btn]
            if (x0 <= x < x1) and (y0 <= y < y1):
                getattr(self.mpd, self.button_cmds[btn])()
                if btn in self.buttons_that_navigate:
                    self.curr_songid = -1

    def send_commands(self, *cmds):
        "send commands to MPD and ensure that the UI state is refreshed immediately"
        self.mpd.send_commands(*cmds)
        self.next_update = 0

    def _request_data(self, cmd_slot: str):
        #self.mpd.log.debug("requesting %s", cmd_slot)
        self.status_data[cmd_slot] = {}
        self.mpd.send_commands_async(cmd_slot, quiet=True)
        self.waiting_for_data = cmd_slot

    @staticmethod
    def _fmt_time(t):
        if t is None: return "\u2013"
        t = int(t)
        return f"{t//60}:{t%60:02d}"

###############################################################################

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    mpd = MPDClient()
    mpd.send_commands('update', 'clear', 'single 0', 'repeat 1', 'random 1', 'add "calm"', 'add "semicalm"', 'add "trance"', 'shuffle', 'play')
    try:
        songid = 0
        while mpd.connected:
            mpd.send_commands_async('status', quiet=True)
            status = mpd.get_async_result()
            if status.get('songid', songid) != songid:
                songid = status['songid']
                print("---------- NEW TRACK ----------")
                mpd.send_commands_async('currentsong', quiet=True)
                info =  mpd.get_async_result()
                for k in ("file", "Title", "Artist", "Album", "Genre", "Date"):
                    if k in info: print((k + ':').ljust(8) + str(info[k]))
                continue
            sys.stdout.write(f"{status.get('elapsed',0):.0f}/{status.get('duration',0):.0f}\r")
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        print()
    mpd.send_commands('stop')
    mpd.disconnect()
