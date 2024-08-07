#!/usr/bin/env python3
import logging

from ctrlpad.sdl import GLAppWindow, Cursor
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer
from ctrlpad.controls import ControlEnvironment, GridLayout, Button


class MyApp(GLAppWindow):
    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("segoe")
        self.renderer.add_font("bahn")
        gl.ClearColor(.12, .34, .56, .78)
        self.set_cursor(Cursor.Hand)

        self.env = ControlEnvironment(self, self.renderer)
        self.grid = GridLayout(16,4, margin=20, padding=15)
        self.grid.put(0,0, 2,2, Button("PANIC BUTTON", disabled_fill1="777", disabled_fill2="999", disabled_text="444")).state = 'disabled'
        self.grid.put(2,0, 2,2, Button("CLICK", active_fill1="#ffc")).cmd = lambda e,b: print("Hellorld!")
        self.grid.put(4,0, 2,2, Button("TOGGLE", active_fill1="#ffc", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)
        self.grid.layout(self.env, 0,0, self.vp_width, self.vp_height)

    def on_resize(self):
        logging.info("screen resized to %dx%d", self.vp_width, self.vp_height)
        self.grid.layout(self.env, 0,0, self.vp_width, self.vp_height)

    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.renderer.begin_frame(self.vp_width, self.vp_height)

        self.renderer.text(self.vp_width, self.vp_height, self.vp_height//4, "CAPTION", "0001", halign=1, valign=1)

        self.renderer.box(400,100, 600,400, "fff4")
        self.renderer.text(400,100, 20, [l for l,w in self.renderer.wrap_text(200, 20, "This is a very long text, which I'd like to flow nicely into its box.")])

        self.renderer.box(700,100, 800,200, "fff4")
        self.renderer.fitted_text(self.renderer.fit_text_in_box(700,100, 800,200, 20, "Medium-Length Text Here"))

        self.renderer.box(700,300, 800,400, "fff4")
        self.renderer.fitted_text(self.renderer.fit_text_in_box(700,300, 800,400, 20, "Slightly Longer Text Here (needs resizing)"))

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
