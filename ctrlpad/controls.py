import logging

from .sdl import GLAppWindow
from .renderer import Renderer


class ControlEnvironment:
    ref_scale = 1000

    def __init__(self, window: GLAppWindow, renderer: Renderer):
        self.window = window
        self.renderer = renderer
        self.update_scale()

    def update_scale(self):
        self.control_scale = min(self.window.vp_width, self.window.vp_height) / self.ref_scale

    def scale(self, x):
        return round(x * self.control_scale)


class Control:
    def __init__(self, **style):
        self.style = style
        self.state = None
        self.children = []
        self.geometry = (0,0,0,0)
        self.invalidate_layout()
        self.click_x, self.click_y = 0, 0

    def get(self, key: str, default=None):
        if self.state:
            return self.style.get(self.state + '_' + key, self.style.get(key, default))
        else:
            return self.style.get(key, default)

    def invalidate_layout(self):
        self.layout_valid = False
        for child in self.children:
            child.invalidate_layout()

    def layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        self.geometry = (x0, y0, x1, y1)
        self.do_layout(env, x0, y0, x1, y1)
        self.layout_valid = True

    def draw(self, env: ControlEnvironment):
        if not self.layout_valid:
            self.layout(env, *self.geometry)
        self.do_draw(env, *self.geometry)
        for child in self.children:
            child.draw(env)

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        pass

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        pass

    def on_click(self, env: ControlEnvironment, x: int, y: int):
        self.click_x, self.click_y = x, y
        for child in self.children:
            x0, y0, x1, y1 = child.geometry
            if (x0 <= x < x1) and (y0 <= y < y1):
                child.on_click(env, x, y)

    def on_drag(self, env: ControlEnvironment, x: int, y: int):
        self.click_x, self.click_y = x, y
        for child in self.children:
            x0, y0, x1, y1 = child.geometry
            if (x0 <= x < x1) and (y0 <= y < y1):
                child.on_drag(env, x, y)


class GridLayout(Control):
    def __init__(self, min_cells_x: int = 0, min_cells_y: int = 0, **style):
        super().__init__(**style)
        self.min_cells = (min_cells_x, min_cells_y)

    def put(self, grid_pos_x: int, grid_pos_y: int, grid_size_x: int, grid_size_y: int, control: Control):
        self.children.append(control)
        control.grid_start_x = grid_pos_x
        control.grid_start_y = grid_pos_y
        control.grid_end_x = grid_pos_x + grid_size_x
        control.grid_end_y = grid_pos_y + grid_size_y
        return control

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        if not self.children: return

        # determine grid size
        maxx, maxy = self.min_cells
        for child in self.children:
            maxx = max(maxx, child.grid_end_x)
            maxy = max(maxy, child.grid_end_y)

        # compute cell size (cs*) and actual grid start
        margin  = env.scale(self.get('margin',  0))  # outer margin 
        padding = env.scale(self.get('padding', 0))  # padding between cells
        csx = ((x1 - x0) - 2 * margin - (maxx - 1) * padding) // maxx + padding
        csy = ((y1 - y0) - 2 * margin - (maxy - 1) * padding) // maxy + padding
        if not self.get('rectangular'):
            csx = csy = min(csx, csy)
        x0 = (x0 + x1 - csx * maxx + padding) // 2
        y0 = (y0 + y1 - csy * maxy + padding) // 2

        # layout cells
        for child in self.children:
            child.layout(env,
                x0 + csx * child.grid_start_x,
                y0 + csy * child.grid_start_y,
                x0 + csx * child.grid_end_x - padding,
                y0 + csy * child.grid_end_y - padding)


class TextControl(Control):
    def __init__(self, text, **style):
        super().__init__(**style)
        self.text = text


class Button(TextControl):
    default_delay = 2

    def __init__(self, text, cmd=None, **style):
        super().__init__(text, **style)
        self.cmd = cmd
        self.text = text
        self.delayed_click = None

    @property
    def active(self):
        return (self.state == 'active')

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        self.border = env.scale(self.get('border', 3))
        self.shadow = env.scale(self.get('shadow', 15))
        self.radius = env.scale(self.get('radius', 30))
        self.text_layout = env.renderer.fit_text_in_box(
            x0 + self.border * 1.5, y0 + self.border,
            x1 - self.border * 1.5, y1 - self.border,
            env.scale(self.get('size', 50)), self.text,
            self.get('halign', 2), self.get('valign', 2))

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        # delayed click handler
        if self.delayed_click:
            self.delayed_click -= 1
        if self.delayed_click == 0:
            self.delayed_click = None
            if self.cmd: self.cmd(env, self)
            if not self.get('toggle'):
                self.state = None

        # actual drawing
        env.renderer.outline_box(
            x0,y0, x1,y1, self.border,
            colorO=self.get('outline', "666"),
            colorU=self.get('fill1', "aaa"),
            colorL=self.get('fill2', "ccc"),
            radius=self.radius,
            shadow_offset=self.shadow*0.25,
            shadow_blur=self.shadow,
            shadow_grow=self.shadow)
        env.renderer.fitted_text(self.text_layout, self.get('text', "000"))

    def on_click(self, env: ControlEnvironment, x: int, y: int):
        if self.get('manual'):
            if self.cmd: self.cmd(env, self)
            return
        if self.state == 'disabled':
            self.clicked = False
            return
        # queue handling of the click in the next frame
        # (so the visual state change can be seen)
        self.state = 'active' if (not(self.state) or not(self.get('toggle'))) else None
        delay = self.get('delay', self.default_delay)
        self.delayed_click = delay
        env.window.request_frames(delay)
