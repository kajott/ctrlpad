# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import ctypes
import ctypes.util
import sys
import time
if sys.platform == 'win32':
    import _ctypes

from .opengl import gl

__all__ = ['GLAppWindow', 'Button', 'Mod', 'Cursor']

class Button:
    Left   = 1
    Right  = 2
    Middle = 3

class Mod:
    Shift  = 0x0003
    LShift = 0x0001
    RShift = 0x0002
    Ctrl   = 0x00C0
    LCtrl  = 0x0040
    RCtrl  = 0x0080
    Alt    = 0x0300
    LAlt   = 0x0100
    RAlt   = 0x0200
    Win    = 0x0C00
    LWin   = 0x0400
    RWin   = 0x0800
    Num    = 0x1000
    Caps   = 0x2000
    Mode   = 0x4000
    Scroll = 0x8000

class Cursor:
    Arrow     =  0
    IBeam     =  1
    Wait      =  2
    Crosshair =  3
    WaitArrow =  4
    SizeNWSE  =  5
    SizeNESW  =  6
    SizeWE    =  7
    SizeNS    =  8
    SizeAll   =  9
    No        = 10
    Hand      = 11

class SDL_WindowEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('windowID',  ctypes.c_uint),
    ('event',     ctypes.c_ubyte),
    ('padding1',  ctypes.c_ubyte),
    ('padding2',  ctypes.c_ubyte),
    ('padding3',  ctypes.c_ubyte),
    ('data1',     ctypes.c_int),
    ('data2',     ctypes.c_int),
]
class SDL_KeyboardEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('windowID',  ctypes.c_uint),
    ('state',     ctypes.c_ubyte),
    ('repeat',    ctypes.c_ubyte),
    ('padding2',  ctypes.c_ubyte),
    ('padding3',  ctypes.c_ubyte),
    ('scancode',  ctypes.c_uint),
    ('sym',       ctypes.c_int),
]
class SDL_MouseMotionEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('windowID',  ctypes.c_uint),
    ('which',     ctypes.c_uint),
    ('state',     ctypes.c_uint),
    ('x',         ctypes.c_int),
    ('y',         ctypes.c_int),
    # xrel, yrel: ignored
]
class SDL_MouseButtonEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('windowID',  ctypes.c_uint),
    ('which',     ctypes.c_uint),
    ('button',    ctypes.c_ubyte),
    ('state',     ctypes.c_ubyte),
    ('clicks',    ctypes.c_ubyte),
    ('padding1',  ctypes.c_ubyte),
    ('x',         ctypes.c_int),
    ('y',         ctypes.c_int),
]
class SDL_MouseWheelEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('windowID',  ctypes.c_uint),
    ('which',     ctypes.c_uint),
    ('x',         ctypes.c_int),
    ('y',         ctypes.c_int),
    ('direction', ctypes.c_uint),
    # preciseX, preciseY: ignored
]
class SDL_DropEvent(ctypes.Structure): _fields_ = [
    ('type',      ctypes.c_uint),
    ('timestamp', ctypes.c_uint),
    ('file',      ctypes.c_char_p),
    ('windowID',  ctypes.c_uint),
]
class SDL_Event(ctypes.Union): _fields_ = [
    ('type',    ctypes.c_uint),
    ('padding', ctypes.c_ubyte * 256),
    ('window',  SDL_WindowEvent),
    ('key',     SDL_KeyboardEvent),
    ('motion',  SDL_MouseMotionEvent),
    ('button',  SDL_MouseButtonEvent),
    ('wheel',   SDL_MouseWheelEvent),
    ('drop',    SDL_DropEvent),
]

class GLAppWindow:
    """
    Base class for an application window with SDL2+OpenGL rendering.

    This class creates a windows and an OpenGL rendering context. Events are
    forwarded to derived classes as callback methods (see "event handlers"
    section below).

    OpenGL viewport handling on resize is done automatically. The 'vp_width'
    and 'vp_height' member variables reflect the current viewport (= window)
    size at all times.
    """

    _keysyms = {  # SDL2 keysym-to-keyname mappings for non-ASCII keys
        8:  "BACKSPACE",
        9:  "TAB",
        13: "RETURN",
        27: "ESCAPE",
        32: "SPACE",
        (1<<30) +  57: "CAPSLOCK",
        (1<<30) +  70: "PRINTSCREEN",
        (1<<30) +  71: "SCROLLLOCK",
        (1<<30) +  72: "PAUSE",
        (1<<30) +  73: "INSERT",
        (1<<30) +  74: "HOME",
        (1<<30) +  75: "PAGEUP",
        (1<<30) +  76: "DELETE",
        (1<<30) +  77: "END",
        (1<<30) +  78: "PAGEDOWN",
        (1<<30) +  79: "RIGHT",
        (1<<30) +  80: "LEFT",
        (1<<30) +  81: "DOWN",
        (1<<30) +  82: "UP",
        (1<<30) +  83: "NUMLOCKCLEAR",
        (1<<30) +  84: "KP_DIVIDE",
        (1<<30) +  85: "KP_MULTIPLY",
        (1<<30) +  86: "KP_MINUS",
        (1<<30) +  87: "KP_PLUS",
        (1<<30) +  88: "KP_ENTER",
        (1<<30) +  98: "KP_0",
        (1<<30) +  99: "KP_PERIOD",
        (1<<30) + 100: "NONUSBACKSLASH",
        (1<<30) + 101: "APPLICATION",
        (1<<30) + 103: "KP_EQUALS",
        (1<<30) + 116: "EXECUTE",
        (1<<30) + 117: "HELP",
        (1<<30) + 118: "MENU",
        (1<<30) + 119: "SELECT",
        (1<<30) + 120: "STOP",
        (1<<30) + 121: "AGAIN",
        (1<<30) + 122: "UNDO",
        (1<<30) + 123: "CUT",
        (1<<30) + 124: "COPY",
        (1<<30) + 125: "PASTE",
        (1<<30) + 126: "FIND",
        (1<<30) + 127: "MUTE",
        (1<<30) + 128: "VOLUMEUP",
        (1<<30) + 129: "VOLUMEDOWN",
        (1<<30) + 133: "KP_COMMA",
        (1<<30) + 134: "KP_EQUALSAS400",
        (1<<30) + 224: "LCTRL",
        (1<<30) + 225: "LSHIFT",
        (1<<30) + 226: "LALT",
        (1<<30) + 227: "LGUI",
        (1<<30) + 228: "RCTRL",
        (1<<30) + 229: "RSHIFT",
        (1<<30) + 230: "RALT",
        (1<<30) + 231: "RGUI",
    }
    _keysym_ranges = [  # SDL2 keysym-to-keyname mappings for ranges of keys
        # base,         count, start, prefix
        ((1<<30) +  58, 12,    1,     "F"),
        ((1<<30) +  89, 9,     1,     "KP_"),
        ((1<<30) + 104, 12,    13,    "F"),
    ]
    def _translate_key(self, sym):
        if sym in self._keysyms: return self._keysyms[sym]
        if sym < 127: return chr(sym).upper()
        for base, count, start, prefix in self._keysym_ranges:
            i = sym - base
            if 0 <= i < count:
                return prefix + str(i + start)
        return f"?{sym}"

    def __init__(self, width: int, height: int, title: str, fullscreen: bool = False, fps_limit: float = 0.0):
        """create a window and OpenGL context with specified initial size and window title
        @note don't override this; override on_init() instead!"""
        self._lib = None
        self._win = None
        self._ctx = None
        libpath = ctypes.util.find_library("SDL2")
        if (sys.platform == 'win32') and libpath:
            self._lib = ctypes.CDLL(name=libpath, handle=_ctypes.LoadLibrary(libpath))
        else:
            self._lib = ctypes.CDLL(libpath or "SDL2")
        if not self._lib:
            raise RuntimeError("failed to load SDL library")
        self._lib.SDL_free.argtypes = [ctypes.c_void_p]
        self._lib.SDL_GL_CreateContext.restype = ctypes.c_void_p
        self._lib.SDL_GL_CreateContext.argtypes = [ctypes.c_void_p]
        self._lib.SDL_GL_GetProcAddress.restype = ctypes.c_void_p
        self._lib.SDL_GL_SwapWindow.argtypes = [ctypes.c_void_p]
        self._lib.SDL_GetMouseFocus.restype = ctypes.c_void_p
        self._lib.SDL_GetMouseState.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        self._lib.SDL_SetWindowTitle.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self._lib.SDL_CreateSystemCursor.restype = ctypes.c_void_p
        self._lib.SDL_SetCursor.argtypes = [ctypes.c_void_p]
        self._lib.SDL_FreeCursor.argtypes = [ctypes.c_void_p]
        self._lib.SDL_GetModState.restype = ctypes.c_uint32
        if self._lib.SDL_Init(0x21):  # SDL_INIT_TIMER + SDL_INIT_VIDEO
            self._lib = None
            raise RuntimeError("failed to initialize SDL")
        self._lib.SDL_CreateWindow.restype = ctypes.c_void_p
        self._win = self._lib.SDL_CreateWindow(
            ctypes.c_char_p(title.encode('utf-8')),
            0x1FFF0000, 0x1FFF0000,  # SDL_WINDOWPOS_UNDEFINED
            width, height,
            0x3003  # SDL_WINDOW_OPENGL + SDL_WINDOW_FULLSCREEN_DESKTOP + SDL_WINDOW_ALLOW_HIGHDPI
            if fullscreen else
            0x2022  # SDL_WINDOW_OPENGL + SDL_WINDOW_RESIZABLE + SDL_WINDOW_ALLOW_HIGHDPI
        )
        if not self._win:
            raise RuntimeError("failed to create window")
        self._ctx = self._lib.SDL_GL_CreateContext(self._win)
        if not self._ctx:
            raise RuntimeError("failed to create context")
        self._lib.SDL_GL_SetSwapInterval(1)
        self.active = True
        self.fps_limit = fps_limit
        self.requested_frames = 2
        gl._load(self._lib.SDL_GL_GetProcAddress)
        vp = (ctypes.c_int * 4)()
        gl.GetIntegerv(gl.VIEWPORT, vp)
        self.vp_width, self.vp_height = vp[2:]
        self.on_init()
        self.next_frame_at = 0

    def request_frames(self, nframes=1):
        "request to render at least 'nframes' frames before idling"
        self.requested_frames = max(self.requested_frames, nframes)

    def handle_event(self, wait=False):
        "handle a single SDL event, optionally with waiting"
        ev = SDL_Event()
        if not (self._lib.SDL_WaitEvent if wait else self._lib.SDL_PollEvent)(ctypes.byref(ev)):
            return False
        if ev.type == 0x0100:  # SDL_QUIT
            self.quit()
        elif ev.type == 0x0200:  # SDL_WINDOWEVENT
            if ev.window.event == 5:  # SDL_WINDOWEVENT_RESIZED
                old_vp_width, old_vp_height = self.vp_width, self.vp_height
                self.vp_width, self.vp_height = ev.window.data1, ev.window.data2
                if self._ctx:
                    gl.Viewport(0, 0, self.vp_width, self.vp_height)
                self.on_resize(old_vp_width, old_vp_height)
        elif ev.type == 0x0300:  # SDL_KEYDOWN
            self.on_key_down(self._translate_key(ev.key.sym))
        elif ev.type == 0x0301:  # SDL_KEYUP
            self.on_key_up(self._translate_key(ev.key.sym))
        elif ev.type == 0x0400:  # SDL_MOUSEMOTION
            self.on_mouse_motion(ev.motion.x, ev.motion.y, ev.motion.state << 1)
        elif ev.type == 0x0401:  # SDL_MOUSEBUTTONDOWN
            self.on_mouse_down(ev.button.x, ev.button.y, ev.button.button)
        elif ev.type == 0x0402:  # SDL_MOUSEBUTTONUP
            self.on_mouse_up(ev.button.x, ev.button.y, ev.button.button)
        elif ev.type == 0x0403:  # SDL_MOUSEWHEEL
            self.on_wheel(ev.wheel.x, ev.wheel.y)
        elif ev.type == 0x1002:  # SDL_DROPBEGIN
            self._drop = []
        elif ev.type == 0x1000:  # SDL_DROPFILE
            self._drop.append(bytes(ev.drop.file).decode('utf-8', 'replace'))
            # self._lib.SDL_free(ctypes.cast(ev.drop.file, ctypes.c_void_p))  # this crashes reliably, no idea why
        elif ev.type == 0x1003:  # SDL_DROPCOMPLETE
            self.on_drop(self._drop)
        return True

    def handle_events(self):
        "handle as many events as currently queued (without waiting)"
        any_events = False
        while self.handle_event(wait=False):
            any_events = True
        return any_events

    def main_loop(self):
        "run the application's main loop until it is quit"
        while self.active:
            any_events = self.handle_events()
            if self.requested_frames >= 0:
                self.requested_frames -= 1
            elif not any_events:
                self.handle_event(True)
                self.handle_events()
            if not self.active: break
            self.on_draw()
            if self.fps_limit > 0.0:
                now = time.monotonic()
                if now < self.next_frame_at:
                    time.sleep(self.next_frame_at - now)
                    now = time.monotonic()
                self.next_frame_at = now + 1.0 / self.fps_limit - 0.001
            self._lib.SDL_GL_SwapWindow(self._win)

    def set_title(self, title: str):
        "set the window title"
        self._lib.SDL_SetWindowTitle(self._win, ctypes.c_char_p(title.encode('utf-8')))

    def set_fps_limit(self, fps: float = 0.0):
        "set or clear the frame rate limit"
        self.fps_limit = float(fps)

    def show_cursor(self, mode: bool = True):
        "show (True) or hide (False) the mouse cursor"
        self._lib.SDL_ShowCursor(1 if mode else 0)
    def hide_cursor(self):
        "hide the mouse cursor"
        self.show_cursor(False)

    def set_cursor(self, cursor_id: int):
        "set mouse cursor to one of the system cursors (see Cursor class/enum)"
        c = self._lib.SDL_CreateSystemCursor(cursor_id)
        self._lib.SDL_SetCursor(c)
        self._lib.SDL_FreeCursor(c)

    def has_mouse_focus(self):
        "determine whether the mouse is inside the window"
        return bool(self._lib.SDL_GetMouseFocus())

    def get_mouse_pos(self):
        "get the current mouse position in window coordinates"
        x = ctypes.c_int()
        y = ctypes.c_int()
        self._lib.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
        return (x.value, y.value)

    def get_mod_state(self):
        "return the state of the keyboard modifiers as a bitmask"
        return self._lib.SDL_GetModState()

    def quit(self):
        "quit the application after handling events"
        self.active = False
        self.on_quit()

    def __del__(self):
        "cleanup"
        if not self._lib: return
        if self._ctx:
            self._lib.SDL_GL_DeleteContext.argtypes = [ctypes.c_void_p]
            self._lib.SDL_GL_DeleteContext(self._ctx)
        if self._win:
            self._lib.SDL_DestroyWindow.argtypes = [ctypes.c_void_p]
            self._lib.SDL_DestroyWindow(self._win)
        self._lib.SDL_Quit()

    ##### event handlers

    def on_init(self):
        "initialize client code"
        pass
    def on_quit(self):
        "application is about to quit"
        pass
    def on_draw(self):
        "draw a frame (called every time after handling pending events)"
        pass
    def on_resize(self, old_vp_width:int, old_vp_height:int):
        """notify about changed viewport size;
        self.vp_width and self.vp_height have been updated
        and glViewport() is re-configured already"""
        pass
    def on_key_down(self, sym:str):
        "key has been pressed down; sym = key name (all-uppercase)"
        pass
    def on_key_up(self, sym:str):
        "key has been released; sym = key name (all-uppercase)"
        pass
    def on_mouse_motion(self, x:int, y:int, buttons:int):
        "mouse has been moved to position x,y; buttons = bitmask: 1<<1 == LMB, 1<<2 = RMB, ..."
        pass
    def on_mouse_down(self, x:int, y:int, button:int):
        "mouse button has been pressed down; button = 1 for LMB, 2 for RMB, 3 for MMB"
        pass
    def on_mouse_up(self, x:int, y:int, button:int):
        "mouse button has been released; button = 1 for LMB, 2 for RMB, 3 for MMB"
        pass
    def on_wheel(self, dx:int, dy:int):
        "mouse wheel has been moved; dx/dy = relative movement (signed)"
        pass
    def on_drop(self, files):
        "receive a list of files dropped onto the window"
        pass
