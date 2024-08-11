#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import argparse
import logging

from ctrlpad.sdl import GLAppWindow, Cursor
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer
from ctrlpad.controls import ControlEnvironment, GridLayout, TabSheet, Label, Button


class MyApp(GLAppWindow):
    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("segoe")
        self.renderer.add_font("bahn")
        self.set_cursor(Cursor.Hand)

        self.env = ControlEnvironment(self, self.renderer)
        self.toplevel = TabSheet(toplevel=True)

        page = self.toplevel.add_page(GridLayout(8,4), "Page One", label="WELCOME")
        panic = page.pack(2,2, Button("PANIC BUTTON", state='disabled', hue=20, sat=.2))
        panic.cmd = lambda e,b: setattr(panic, 'visible', False)
        page.pack(2,2, Button("CLICK")).cmd = lambda e,b: setattr(panic, 'state', None)
        page.pack(2,2, Button("TOGGLE", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)

        page = self.toplevel.add_page(GridLayout(16,8), "Colors", label="COLORFUL")
        page.put(0,0, 12,1, Label("COLORS", valign=1, bar=3))
        for i, name in enumerate("RED YELLOW GREEN CYAN BLUE MAGENTA".split()):
            hue, sat = 30 + i * 60, 0.1
            page.put(i*2,1, 2,2, Button(name, hue=hue, sat=sat, toggle=True))
            page.put(i*2,3, 1,1, Button(name[0], hue=hue, sat=sat, state='disabled'))

        self.toplevel.layout(self.env, 0,0, self.vp_width, self.vp_height)

    def on_resize(self, old_w, old_h):
        w, h = self.vp_width, self.vp_height
        logging.info("screen resized to %dx%d", w, h)
        self.env.update_scale()
        self.toplevel.layout(self.env, 0,0, w, h)
        self.request_frames(1)

    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.renderer.begin_frame(self.vp_width, self.vp_height)
        self.toplevel.draw(self.env)
        self.renderer.end_frame()

    def on_key_down(self, sym: str):
        if sym == 'Q': self.quit()

    def on_mouse_down(self, x: int, y: int, button: int):
        logging.debug("click @ %d,%d", x, y)
        self.toplevel.on_click(self.env, x, y)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fullscreen", action='store_true',
                        help="run in fullscreen mode")
    parser.add_argument("-c", "--no-cursor", action='store_true',
                        help="don't show mouse cursor")
    args = parser.parse_args()

    app = MyApp(1024, 600, "ControlPad Test App", fullscreen=args.fullscreen)
    if args.no_cursor: app.hide_cursor()
    app.main_loop()
