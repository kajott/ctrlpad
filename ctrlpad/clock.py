# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import math
import time

from .sdl import GLAppWindow
from .renderer import Renderer
from .controls import Control, ControlEnvironment
from . import color

__all__ = ['Clock']

###############################################################################

class Clock(Control):
    """
    Studio clock.
    """

    bitmap = [s.strip().split('|') for s in """
    .###.|..#..|.###.|#####|...#.|#####|..##.|#####|.###.|.###.
    #...#|.##..|#...#|...#.|..##.|#....| #...|#...#|#...#|#...#
    #...#|..#..|....#|..#..|.#.#.|####.|#....|....#|#...#|#...#
    #...#|..#..|...#.|.###.|#..#.|....#|####.|...#.|.###.|.####
    #...#|..#..|..#..|....#|#####|....#|#...#|..#..|#...#|....#
    #...#|..#..|.#...|#...#|...#.|#...#|#...#|..#..|#...#|...#.
    .###.|.###.|#####|.###.|...#.|.###.|.###.|..#..|.###.|.##..
    """.strip().split('\n')]

    def __init__(self, **style):
        """
        Instantiate the clock with the following (mostly optional) parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - background    = background color
        - rounding      = rounding radius of the background (0.0=square, 1.0=circle)
        - color         = dot color
        - ambient       = alpha of inactive dots (0.0=invisible)
        - second_size   = size (relative to the total clock size) reserved for the seconds band
        - second_radius = radius of the seconds band dots (1.0=use maximum available space)
        - text_size     = relative size of the HH:MM text (1.0=use maximum available space)
        - text_radius   = radius of the HH:MM text dots (1.0=use maximum available space)
        - text_slant    = slant angle of the text (0.0=none)
        - text_space    = relative space between digits in the HH:MM text (1.0=normal dot width)
        """
        super().__init__(**style)

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        # colors
        c = color.parse(self.get('color', "f30"))
        self.dot_colors = [color.alpha(c, self.get('ambient', 0.15)), c]

        # overall layout
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        r = min(x1 - x0, y1 - y0) * 0.5
        self.background_radius = round(r * self.get('rounding', 1.0))

        # seconds
        ss = self.get('second_size', 0.2)
        if ss > 0.0:
            r_cen = r * (1.0 - ss * 0.5)
            self.second_dot_radius = min(r - r_cen, r_cen * math.pi / 60.0) * self.get('second_radius', 0.6)
            r *= 1.0 - ss
            self.second_dots = [
                (i, x-self.second_dot_radius, y-self.second_dot_radius, x+self.second_dot_radius, y+self.second_dot_radius)
                for i,x,y in ((i, cx + r_cen * math.sin(a), cy - r_cen * math.cos(a))
                for i,a in ((i, i * math.pi / 30.0) for i in range(60)))]
        else:
            self.second_dots = []

        # text metrics
        text_slant = -self.get('text_slant', 0.1)
        text_space = self.get('text_space', 0.75)
        self.dot_distance = r / math.hypot(2 * text_space + 3 * abs(text_slant) + 10.35, 3.35) * self.get('text_size', 1.0)
        self.dot_radius = self.dot_distance * self.get('text_radius', 0.8) * 0.5
        self.dot_slant = self.dot_distance * text_slant
        char_gap = self.dot_distance * text_space
        # create blinking colon
        self.dots = [(cx - self.dot_slant - self.dot_radius, cy - self.dot_distance - self.dot_radius,
                      cx - self.dot_slant + self.dot_radius, cy - self.dot_distance + self.dot_radius, 2, (0,1)),
                     (cx + self.dot_slant - self.dot_radius, cy + self.dot_distance - self.dot_radius,
                      cx + self.dot_slant + self.dot_radius, cy + self.dot_distance + self.dot_radius, 2, (0,1))]
        # shift coordinate to top row
        cx -= 3 * self.dot_slant
        cy -= 3 * self.dot_distance
        # add other characters
        self._add_char(cx - 10 * self.dot_distance - 2 * char_gap, cy, 0)
        self._add_char(cx -  5 * self.dot_distance - 1 * char_gap, cy, 1)
        self._add_char(cx +  1 * self.dot_distance + 1 * char_gap, cy, 3)
        self._add_char(cx +  6 * self.dot_distance + 2 * char_gap, cy, 4)

    def _add_char(self, tx: float, ty: float, idx: int):
        for y in range(7):
            self.dots.extend(
                (tx + x * self.dot_distance - self.dot_radius, ty - self.dot_radius,
                 tx + x * self.dot_distance + self.dot_radius, ty + self.dot_radius,
                 idx, tuple(int(self.bitmap[y][d][x] == '#') for d in range(10)))
                for x in range(5))
            ty += self.dot_distance
            tx += self.dot_slant

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        # parse the time into the local digit data structure
        t = env.draw_time
        frac = t - int(t)
        half = int(frac < 0.5)
        t = time.localtime(t)
        s = t.tm_sec
        t = (t.tm_hour // 10, t.tm_hour % 10, half, t.tm_min // 10, t.tm_min % 10)

        # draw everything
        env.renderer.box(x0,y0,x1,y1, self.get('background', "111"), radius=self.background_radius)
        for i, dx0, dy0, dx1, dy1 in self.second_dots:
            env.renderer.box(dx0,dy0,dx1,dy1, self.dot_colors[int(s >= i)], radius=self.second_dot_radius)
        for dx0, dy0, dx1, dy1, i, vmap in self.dots:
            env.renderer.box(dx0,dy0,dx1,dy1, self.dot_colors[vmap[t[i]]], radius=self.dot_radius)

        # order the next update
        return (1.0 - frac) if (frac > 0.5) else (0.5 - frac)
