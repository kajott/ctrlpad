# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import argparse
import logging
import os
import time

__all__ = ['run_application']

from .sdl import GLAppWindow, Cursor
from .opengl import gl
from .renderer import Renderer
from .color import set_global_gamma
from ctrlpad.controls import merge_time, ControlEnvironment, TabSheet


class CtrlPadAppWindow(GLAppWindow):
    invisible_quit_button_size = 20

    def on_init(self):
        self.quit_timeout = None
        self.tl_clock_last_minute = 0

    def on_resize(self, old_w, old_h):
        w, h = self.vp_width, self.vp_height
        logging.info("screen resized to %dx%d", w, h)
        self.env.update_scale()
        self.env.toplevel.layout(self.env, 0,0, w, h)
        self.request_frames(1)

    def on_draw(self, t):
        # update the clock
        res = None
        tm = time.localtime(t)
        if tm.tm_min != self.tl_clock_last_minute:
            self.env.toplevel.set_text(f"{tm.tm_hour}:{tm.tm_min:02d}")
            self.tl_clock_last_minute = tm.tm_min
        res = (60 - tm.tm_sec) + (1.0 - (t - int(t)))

        # actual drawing
        gl.Clear(gl.COLOR_BUFFER_BIT)
        self.env.begin_frame(t)
        res = merge_time(res, self.env.toplevel.draw(self.env))
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
        self.env.toplevel.on_click(self.env, x, y)



def run_application(title: str, init_func, **toplevel_kwargs):
    """
    High-level main function to run a control application.

    This function takes care of all the gory details of command-line argument
    parsing and application initialization, and provides a window with a
    top-level TabSheet control. The init_func callback function has the
    following signature:
        init_func(env: ControlEnvironment)
    The aforementioned top-level TabSheet control is available at env.toplevel.
    The initialization function instantiates the entire UI and controllers,
    and then run_application() takes over again and arranges for the main loop
    to run.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action='count', default=0,
                        help="show more verbose log messages")
    parser.add_argument("-q", "--quiet", action='count', default=0,
                        help="show less verbose log messages (only warnings and errors)")
    parser.add_argument("-f", "--fullscreen", action='store_true',
                        help="run in fullscreen mode")
    parser.add_argument("-c", "--no-cursor", action='store_true',
                        help="don't show mouse cursor")
    parser.add_argument("-r", "--fps-limit", metavar="FPS", type=float, default=0,
                        help="set frame rate limit")
    parser.add_argument("-g", "--geometry", metavar="WxH", default=(1024, 600),
                        type=lambda s: tuple(map(int, s.lower().split('x', 1))),
                        help="set initial window size")
    parser.add_argument("-G", "--gamma", type=float, default=1.0,
                        help="set global gamma correction")
    parser.add_argument("-D", "--data-dir", metavar="DIR", default="data",
                        help="set font data directory [default: %(default)s]")
    parser.add_argument("-F", "--primary-font", metavar="NAME", default="bahn",
                        help="set primary UI font [default: %(default)s]")
    args = parser.parse_args()

    log_levels = (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
    log_level_idx = log_levels.index(logging.INFO) + args.verbose - args.quiet
    log_level = log_levels[max(0, min(len(log_levels) - 1, log_level_idx))]

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    color.set_global_gamma(args.gamma)

    app = CtrlPadAppWindow(*args.geometry, title, fullscreen=args.fullscreen, fps_limit=args.fps_limit)
    app.env = ControlEnvironment(app, Renderer())
    app.env.renderer.add_font(os.path.join(args.data_dir, args.primary_font))
    if args.primary_font != "symbol":
        app.env.renderer.add_font(os.path.join(args.data_dir, "symbol"))

    final_tl_kwargs = {'color': "888"}
    final_tl_kwargs.update(toplevel_kwargs)
    app.env.toplevel = TabSheet(toplevel=True, **final_tl_kwargs)

    app.set_cursor(Cursor.Hand)
    if args.no_cursor:
        app.hide_cursor()

    init_func(app.env)
    app.env.toplevel.layout(app.env, 0,0, app.vp_width, app.vp_height)

    logging.info("initialization finished, starting main loop")
    app.main_loop()
    logging.info("quitting ...")
    del app
    logging.info("application exited")
