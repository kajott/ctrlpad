#!/usr/bin/env python3
import logging

from ctrlpad.sdl import GLAppWindow, Cursor
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer

class MyApp(GLAppWindow):
    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("segoe")
        self.renderer.add_font("bahn")
        gl.ClearColor(.12, .34, .56, .78)
        self.set_cursor(Cursor.Hand)

    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.renderer.begin_frame(self.vp_width, self.vp_height)
        self.renderer.text(self.vp_width, self.vp_height, self.vp_height//4, "CAPTION", "0001", halign=1, valign=1)
        self.renderer.outline_box(100, 100, 200, 200, 2, "def", "789", "abc", 20, shadow_offset=2, shadow_blur=8, shadow_grow=8)
        #self.renderer.outline_box(100, 100, 200, 200, 2, "123", "789", "abc", 20)
        self.renderer.text(150, 150, 25, "PANIC\nBUTTON", "000", halign=2, valign=2)
        self.renderer.text(600, 300, 30, "This is fine.")
        self.renderer.end_frame()

    def on_key_down(self, sym: str):
        if sym == 'Q': self.quit()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    MyApp(1024, 600, "ControlPad Test App").main_loop()
