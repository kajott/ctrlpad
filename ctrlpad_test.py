#!/usr/bin/env python3
from ctrlpad.sdl import GLAppWindow, Button, Mod
from ctrlpad.opengl import gl
from ctrlpad.renderer import Renderer

class MyApp(GLAppWindow):
    def on_init(self):
        self.renderer = Renderer()
        #self.renderer.add_font("segoe")
        self.renderer.add_font("bahn")
        gl.ClearColor(.12, .34, .56, .78)

    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.renderer.begin_frame(self.vp_width, self.vp_height)
        self.renderer.outline_box(100, 100, 200, 200, 2, "def", "789", "abc", 20, shadow_offset=2, shadow_blur=8, shadow_grow=8)
        #self.renderer.outline_box(100, 100, 200, 200, 2, "123", "789", "abc", 20)
        self.renderer.text(150, 150, 25, "PANIC\nBUTTON", "000", halign=2, valign=2)
        self.renderer.text(600, 300, 30, "This is fine.")
        self.renderer.text(600, 340, 120, "LARGE", "0004")
        self.renderer.flush()

    def on_key_down(self, sym: str):
        if sym == 'Q': self.quit()

if __name__ == "__main__":
    MyApp(1024, 600, "ControlPad Test App").main_loop()
