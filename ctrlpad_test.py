#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import argparse
import logging
import time

from ctrlpad.sdl import GLAppWindow, Cursor
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer
from ctrlpad.controls import bind, merge_time, ControlEnvironment, \
                             GridLayout, TabSheet, Label, Button
from ctrlpad.clock import Clock
from ctrlpad.crossbar import Crossbar


class MyApp(GLAppWindow):
    invisible_quit_button_size = 20

    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("data/segoe")
        self.renderer.add_font("data/bahn")
        self.set_cursor(Cursor.Hand)
        self.quit_timeout = None

        self.env = ControlEnvironment(self, self.renderer)
        self.toplevel = TabSheet(toplevel=True, color="888")
        self.tl_clock_last_minute = 0

        page = self.toplevel.add_page(GridLayout(16,8), "Page One", label="WELCOME")
        page.pack(8,8, Clock())
        panic = page.pack(2,2, Button("PANIC BUTTON", state='disabled', hue=20, sat=.2))
        @bind(panic)
        def cmd(e,b):
            panic.visible = False
        page.pack(2,2, Button("CLICK")).cmd = lambda e,b: setattr(panic, 'state', None)
        page.pack(2,2, Button("TOGGLE", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)

        page = self.toplevel.add_page(GridLayout(16,8), "Colors", label="COLORFUL")
        page.put(0,0, 12,1, Label("COLORS", valign=1, bar=3))
        for i, name in enumerate("RED YELLOW GREEN CYAN BLUE MAGENTA".split()):
            hue, sat = 30 + i * 60, 0.1
            page.put(i*2,1, 2,2, Button(name, hue=hue, sat=sat, toggle=True))
            page.put(i*2,3, 1,1, Button(name[0], hue=hue, sat=sat, state='disabled'))

        self.xbar = Crossbar(8, 8)
        # https://keyj.emphy.de/photos/deadline2023/dl23_videosetup.png
        self.xbar.add_ui_page(self.toplevel, input_names={
            '1': "ATEM OUT 2",
            '2': "Stream Output",
            '3': "FOH HDMI",
            '4': "Old school",
            '5': "Compo1\n",
            '6': "Compo2\n",
            '7': "Screens\n",
            '8': "n/c\n"
        }, output_names=[
            "ATEM IN 1", "ATEM IN 2", "ATEM IN 3", "Stream Team",
            "Compo1 Monitor", "Compo2 Monitor",
            "Main Screen", "Bar Screen"
        ], input_format="\u203a\u2039", output_format="\u2039\u203a")

        self.toplevel.layout(self.env, 0,0, self.vp_width, self.vp_height)

    def on_resize(self, old_w, old_h):
        w, h = self.vp_width, self.vp_height
        logging.info("screen resized to %dx%d", w, h)
        self.env.update_scale()
        self.toplevel.layout(self.env, 0,0, w, h)
        self.request_frames(1)

    def on_draw(self, t):
        # update the clock
        res = None
        tm = time.localtime(t)
        if tm.tm_min != self.tl_clock_last_minute:
            self.toplevel.set_text(f"{tm.tm_hour}:{tm.tm_min:02d}")
            self.tl_clock_last_minute = tm.tm_min
        res = (60 - tm.tm_sec) + (1.0 - (t - int(t)))

        # actual drawing
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.env.begin_frame(t)
        res = merge_time(res, self.toplevel.draw(self.env))
        self.env.end_frame()
        return res

    def on_key_down(self, sym: str):
        if sym == 'Q': self.quit()

    def on_mouse_down(self, x: int, y: int, button: int):
        logging.debug("click @ %d,%d", x, y)
        if (x > (self.vp_width - self.invisible_quit_button_size)) and (y < self.invisible_quit_button_size):
            now = time.time()
            if self.quit_timeout and (now < self.quit_timeout):
                self.quit()
            else:
                logging.info("invisible quit button hit - double-click to quit the program")
                self.quit_timeout = now + 0.5
        else:
            self.quit_timeout = None
        self.toplevel.on_click(self.env, x, y)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fullscreen", action='store_true',
                        help="run in fullscreen mode")
    parser.add_argument("-c", "--no-cursor", action='store_true',
                        help="don't show mouse cursor")
    parser.add_argument("-r", "--fps-limit", type=float, default=0,
                        help="set frame rate limit")
    args = parser.parse_args()

    app = MyApp(1024, 600, "ControlPad Test App", fullscreen=args.fullscreen, fps_limit=args.fps_limit)
    if args.no_cursor: app.hide_cursor()
    app.main_loop()
    logging.info("quitting ...")
    del app
    logging.info("program exited")
