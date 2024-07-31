#!/usr/bin/env python3
from ctrlpad.sdl import GLAppWindow, Button, Mod
from ctrlpad.opengl import gl

class MyApp(GLAppWindow):
    def on_init(self):
        gl.ClearColor(.12, .34, .56, .78)
    def on_draw(self):
        gl.Clear(gl.COLOR_BUFFER_BIT)

if __name__ == "__main__":
    MyApp(1024, 600, "ControlPad Test App").main_loop()
