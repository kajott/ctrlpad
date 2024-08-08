#!/usr/bin/env python3
import logging

from ctrlpad.sdl import GLAppWindow, Cursor
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer
from ctrlpad.controls import ControlEnvironment, GridLayout, Label, Button


class MyApp(GLAppWindow):
    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("segoe")
        self.renderer.add_font("bahn")
        gl.ClearColor(.12, .34, .56, .78)
        self.set_cursor(Cursor.Hand)

        self.env = ControlEnvironment(self, self.renderer)
        self.grid = GridLayout(16,4, margin=20, padding=15)

        panic = self.grid.pack(2,2, Button("PANIC BUTTON", state='disabled', hue=20, sat=.2))
        panic.cmd = lambda e,b: setattr(panic, 'visible', False)
        self.grid.pack(2,2, Button("CLICK")).cmd = lambda e,b: setattr(panic, 'state', None)
        self.grid.pack(2,2, Button("TOGGLE", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)

        self.grid.put(0,2, 12,1, Label("COLORS", valign=1, bar=3))
        for i, name in enumerate("RED YELLOW GREEN CYAN BLUE MAGENTA".split()):
            hue, sat = 30 + i * 60, 0.1
            self.grid.put(i*2,3, 2,2, Button(name, hue=hue, sat=sat, toggle=True))
            self.grid.put(i*2,5, 1,1, Button(name[0], hue=hue, sat=sat, state='disabled'))

        self.grid.layout(self.env, 0,0, self.vp_width, self.vp_height)

    def on_resize(self, old_w, old_h):
        w, h = self.vp_width, self.vp_height
        logging.info("screen resized to %dx%d", w, h)
        self.env.update_scale()
        self.grid.layout(self.env, 0,0, w, h)
        self.request_frames(1)

    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.renderer.begin_frame(self.vp_width, self.vp_height)

        self.renderer.text(self.vp_width, self.vp_height, self.vp_height//4, "CAPTION", "0001", halign=1, valign=1)

        self.renderer.box(700,100, 900,200, "fff4")
        self.renderer.fitted_text(self.renderer.fit_text_in_box(700,100, 900,200, 20, "This is a very long text, which I'd like to flow nicely into its box."))

        self.grid.draw(self.env)

        self.renderer.end_frame()

    def on_key_down(self, sym: str):
        if sym == 'Q': self.quit()

    def on_mouse_down(self, x: int, y: int, button: int):
        logging.debug("click @ %d,%d", x, y)
        self.grid.on_click(self.env, x, y)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    MyApp(1024, 600, "ControlPad Test App").main_loop()
