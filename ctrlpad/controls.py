import logging

from .sdl import GLAppWindow
from .renderer import Renderer

__all__ = [
    'ControlEnvironment',
    'Control', 'TextControl',
    'GridLayout',
    'Button'
]

###############################################################################
# MARK: ControlEnvironemnt

class ControlEnvironment:
    """
    Environment for control event handlers.

    This class holds references to some objects that an event handler may find
    useful, specifically the GLAppWindow and Renderer instances.
    It also contains other useful "global" functionality for layouting.
    """

    ref_scale = 1000  # pixels on the abstract reference screen

    def __init__(self, window: GLAppWindow, renderer: Renderer):
        self.window = window
        self.renderer = renderer
        self.update_scale()

    def update_scale(self):
        "update the scaling factor; make sure to call this after each window resize"
        self.control_scale = min(self.window.vp_width, self.window.vp_height) / self.ref_scale

    def scale(self, x):
        "convert size from abstract units to device pixels"
        return round(x * self.control_scale)

###############################################################################
# MARK: Control base

class Control:
    """
    Base class for a control.

    This manages the style, state and position ("geometry") of a control
    and its child controls.

    The state can be any string or None, but the canonical defaults are:
    - None     = no special state
    - active   = currently selected or highlighted
    - disabled = inactive; can't be interacted with
    """

    def __init__(self, **style):
        self.style = style
        self.state = None
        self.children = []
        self.geometry = (0,0,0,0)
        self.invalidate_layout()
        self.click_x, self.click_y = 0, 0

    def get(self, key: str, default=None):
        "get a style parameter, prefixed with the current state, if any"
        if self.state:
            return self.style.get(self.state + '_' + key, self.style.get(key, default))
        else:
            return self.style.get(key, default)

    def invalidate_layout(self):
        """mark the layout of this control and its children as "dirty"
        so that it's recomputed during the next frame"""
        self.layout_valid = False
        for child in self.children:
            child.invalidate_layout()

    def layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        """
        Re-compute the internal layout of the control.

        This is the interface function; the actual work is done in do_layout.
        Note that this function doesn't automatically descend to the children;
        it's the do_layout() function's responsibility to determine the
        position of the children and call layout() on them.
        """
        self.geometry = (x0, y0, x1, y1)
        self.do_layout(env, x0, y0, x1, y1)
        self.layout_valid = True

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        "actual control-specific layout function; to be overridden in subclasses"
        pass

    def draw(self, env: ControlEnvironment):
        """
        Draw the control.

        This is the interface function; the actual work is done in do_layout.
        This function also calls draw() on all children.
        Also updates the layout if it has been marked as dirty using
        invalidate_layout().
        """
        if not self.layout_valid:
            self.layout(env, *self.geometry)
        self.do_draw(env, *self.geometry)
        for child in self.children:
            child.draw(env)

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        "actual control-specific drawing function; to be overridden in subclasses"
        pass

    def on_click(self, env: ControlEnvironment, x: int, y: int):
        """
        Event handler for clicking on the control.

        This is the default implementation that simply stores the clicked
        coordinates and forwards the event to the affected client.
        Subclasses override this with control-specific functionality.
        """
        self.click_x, self.click_y = x, y
        for child in self.children:
            x0, y0, x1, y1 = child.geometry
            if (x0 <= x < x1) and (y0 <= y < y1):
                child.on_click(env, x, y)

    def on_drag(self, env: ControlEnvironment, x: int, y: int):
        """
        Event handler for dragging on the control (i.e. moving the cursor
        while a button is down).

        This is the default implementation that simply stores the clicked
        coordinates and forwards the event to the affected client.
        Subclasses override this with control-specific functionality.
        """
        self.click_x, self.click_y = x, y
        for child in self.children:
            x0, y0, x1, y1 = child.geometry
            if (x0 <= x < x1) and (y0 <= y < y1):
                child.on_drag(env, x, y)

class TextControl(Control):
    "base class for controls having a text"
    def __init__(self, text, **style):
        super().__init__(**style)
        self.text = text

    def set_text(self, text: str):
        "change the text and take care that the layout is recomputed"
        self.text = text
        self.invalidate_layout()

###############################################################################
# MARK: GridLayout

class GridLayout(Control):
    "A container control for a grid-like arrangement of other controls."

    def __init__(self, min_cells_x: int = 0, min_cells_y: int = 0, **style):
        """
        Instantiate the grid with the following optional parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - min_cells_x, min_cells_y = minimum grid size (will be enlarged
                                     automatically if more controls are added)
        - rectangular = False (default) to force square grid cells;
                        True to allow rectangular grid cells
        - margin  ~ = distance around the control's edges
        - padding ~ = distance between cells
        """
        super().__init__(**style)
        self.min_cells = (min_cells_x, min_cells_y)

    def put(self, grid_pos_x: int, grid_pos_y: int, grid_size_x: int, grid_size_y: int, control: Control):
        "put a child control on the grid at a specific position with a specific size"
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
        margin  = env.scale(self.get('margin',  0))
        padding = env.scale(self.get('padding', 0))
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

###############################################################################
# MARK: Button

class Button(TextControl):
    """
    Standard pushbutton or toggle button that lights up and calls a function
    when clicked.
    """

    default_delay = 1

    def __init__(self, text, cmd=None, **style):
        """
        Instantiate the button with the following (mostly optional) parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - text = text to display on the button
        - cmd = function to call when clicked; signature:
                    buttonCommand(env: ControlEnvironment, source: Button)
        - size ~ = default text size (will shrink automatically if text
                   doesn't fit)
        - halign = horizontal text alignment: 0=left, 1=right, 2=center (default)
        - valign = vertical text alignment: 0=top, 1=bottom, 2=middle (default)
        - border  ~ = border/outline width
        - radius  ~ = rounding radius
        - shadow  ~ = shadow size/offset
        - outline * = border/outline color
        - fill1   * = background color at the top
        - fill2   * = background color at the bottom
        - color   * = text color
        - font      = font to use for the text
        - manual = True to disable all automatic event handling and just call
                   cmd() when clicked;
                   False (default) to set the control's state to "active"
                   briefly and only fire cmd() after a delay of a few frames,
                   after the screen has been redrawn with the active state
        - delay = delay (in frames) after which to remove the "active" state
                  and call cmd()
        - toggle = False (default) to remove the "active" state immediately
                   after cmd() has been called;
                   True to retain the "active" state and toggle back to
                   normal state after the next click.
        """
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
        env.renderer.set_font(self.get('font'))
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
        env.renderer.set_font(self.get('font'))
        env.renderer.fitted_text(self.text_layout, self.get('color', "000"))

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
        delay = self.get('delay', self.default_delay) + 1
        self.delayed_click = delay
        env.window.request_frames(delay)
