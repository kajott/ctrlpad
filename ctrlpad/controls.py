# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import logging

from .sdl import GLAppWindow
from .renderer import Renderer
from . import color

__all__ = [
    'bind',
    'ControlEnvironment',
    'Control', 'TextControl',
    'GridLayout', 'TabSheet',
    'Label', 'Button',
]

log = logging.getLogger("controls")

def bind(control):
    """
    Function decorator to conveniently bind events to controls.
    The decorator parameter is the control to bind the event to,
    the function itself shall be named after the member function to set.
    Example:
        button = Button("example")
        @bind(button)
        def cmd(env, btn):
            print("button has been clicked")
    """
    return lambda func: setattr(control, func.__name__, func)

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

    def __init__(self, state=None, visible=True, **style):
        self.style = style
        self.state = state
        self.visible = visible
        self.children = []
        self.geometry = (0,0,0,0)
        self.invalidate_layout()
        self.click_x, self.click_y = 0, 0
        self.drag_child = None

    def get(self, key: str, default=None):
        "get a style parameter, prefixed with the current state, if any"
        if self.state:
            return self.style.get(self.state + '_' + key, self.style.get(key, default))
        else:
            return self.style.get(key, default)

    def weak_set(self, key: str, value):
        "set a style parameter, unless it's already defined"
        if not(key in self.style):
            self.style[key] = value

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

        This is the interface function; the actual work is done in do_draw.
        This function also calls draw() on all children.
        Also updates the layout if it has been marked as dirty using
        invalidate_layout().
        """
        if not self.visible:
            return
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
            if child.visible and (x0 <= x < x1) and (y0 <= y < y1):
                self.drag_child = child
                child.on_click(env, x, y)

    def on_drag(self, env: ControlEnvironment, x: int, y: int):
        """
        Event handler for dragging on the control (i.e. moving the cursor
        while a button is down).

        This is the default implementation that simply stores the clicked
        coordinates and forwards the event to the affected client.
        Subclasses override this with control-specific functionality.
        """
        if self.drag_child:
            self.drag_child.on_drag(env, x, y)

class TextControl(Control):
    "base class for controls having a text"
    def __init__(self, text: str, **style):
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
        self.locate(0, 0)

    def put(self, grid_pos_x: int, grid_pos_y: int, grid_size_x: int, grid_size_y: int, control: Control):
        "put a child control on the grid, with a specific size, at a specific position "
        self.children.append(control)
        control.grid_start_x = grid_pos_x
        control.grid_start_y = grid_pos_y
        control.grid_end_x = grid_pos_x + grid_size_x
        control.grid_end_y = grid_pos_y + grid_size_y
        self.next_grid_x = control.grid_end_x
        self.next_grid_y = control.grid_start_y
        self.invalidate_layout()
        return control

    def pack(self, grid_size_x: int, grid_size_y: int, control: Control):
        "put a child control on the grid, with a specific size, next to the previously put() or pack()ed child"
        return self.put(self.next_grid_x, self.next_grid_y, grid_size_x, grid_size_y, control)

    def locate(self, grid_pos_x: int, grid_pos_y: int):
        "set the position of the next control to be pack()ed"
        self.next_grid_x = grid_pos_x
        self.next_grid_y = grid_pos_y

    def get_grid_max(self):
        "determine current grid size"
        maxx, maxy = self.min_cells
        for child in self.children:
            maxx = max(maxx, child.grid_end_x)
            maxy = max(maxy, child.grid_end_y)
        return (maxx, maxy)

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        if not self.children: return
        maxx, maxy = self.get_grid_max()

        # compute cell size (cs*) and actual grid start
        margin  = env.scale(self.get('margin',  20))
        padding = env.scale(self.get('padding', 15))
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
# MARK: TabSheet

class TabSheet(TextControl):
    """
    A control that hosts multiple child controls that can be toggled between
    with buttons.
    """
    # Note: this sets a few attributes and styles in the child controls for
    #       internal use; all of those are prefixed with 'tab_'

    def __init__(self, toplevel=False, text=None, **style):
        """
        Instantiate the button with the following (mostly optional) parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - toplevel = False (default) for a normal control,
                     True for a toplevel control that fills the entire screen
                     and hence doesn't need outside borders
        - text     = text to display at the upper-right edge
        - font     = font of the text on the upper-right edge
        - color    = color of the text on the upper-right edge
        - size   ~ = text size for the tab labels
        - padx   ~ = horizontal internal padding in the tab buttons
        - pady   ~ = vertical internal padding in the tab buttons
        - width  ~ = width of the outline borders around the tab buttons
        - radius ~ = rounding radius of the tab buttons
        - fading   = brightness factor for inactive tabs (0..1)
        """
        super().__init__(text, **style)
        self.toplevel = toplevel

    def add_page(self, control: Control, title: str, **style):
        """
        Add 'control' as a new page, titled with 'title'. The following style
        parameters are available: [~ = in abstract size units]
        - outline  = outline color
        - color    = tab button title text color
        - fill1    = fill color of the tab button and top end of the page
        - fill2    = fill color of the bottom end of the page (none = no gradient)
        - font     = font of the tab button title
        - label        = large background label text
        - label_color  = color of the label text
        - label_font   = font of the label text
        - label_size ~ = text size of the label text (shrunk automatically)
        - label_padx ~ = horizontal padding of the label text
        - label_pady ~ = vertical padding of the label text
        """
        if control.visible and any(c.visible for c in self.children):
            control.visible = False
        self.children.append(control)
        control.tab_title = title
        for k, v in style.items():
            control.style['tab_' + k] = v
        self.invalidate_layout()
        return control

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        # vertical and "global" geometry
        raw_text_size = self.get('size', 50)
        padx = env.scale(self.get('padx', raw_text_size))
        pady = env.scale(self.get('pady', raw_text_size // 2))
        self.button_outline = env.scale(self.get('width', 3))
        self.button_radius = env.scale(self.get('radius', 25))
        self.button_text_size = env.scale(raw_text_size)
        self.button_text_y = y0 + self.button_outline + pady
        self.bar_y0 = self.button_text_y + self.button_text_size + pady
        self.bar_y1 = self.bar_y0 + self.button_outline
        self.button_y1 = self.bar_y1 + self.button_radius + self.button_outline
        self.page_x0 = x0 + (0 if self.toplevel else self.button_outline)
        self.page_x1 = x1 - (0 if self.toplevel else self.button_outline)
        self.page_y1 = y1 - (0 if self.toplevel else self.button_outline)
        page_width = self.page_x1 - self.page_x0
        page_height = self.page_y1 - self.bar_y1

        # horizontal geometry and per-page stuff
        fading = self.get('fading', 0.5)
        bx = x0
        for page in self.children:
            env.renderer.set_font(page.get('tab_font'))
            page.tab_button_x0 = bx
            page.tab_button_text_x = bx + self.button_outline + padx
            bx = page.tab_button_text_x + env.renderer.text_line_width(page.tab_title, self.button_text_size) + padx
            page.tab_button_x1 = bx + self.button_outline

            # colors
            page.tab_active_outline = color.parse(page.get('tab_outline', "#fff"))
            page.tab_active_background = color.parse(page.get('tab_fill1', "#345"))
            page.tab_active_color = color.parse(page.get('tab_color', "#fff"))
            fill2 = page.get('tab_fill2')
            page.tab_gradient = color.parse(fill2) if fill2 else page.tab_active_background
            page.tab_inactive_outline    = color.scale(page.tab_active_outline,    fading)
            page.tab_inactive_background = color.scale(page.tab_active_background, fading)
            page.tab_inactive_color      = color.scale(page.tab_active_color,      fading)

            # label stuff
            label = page.get('tab_label')
            if label:
                page.tab_label_font = page.get('tab_label_font', page.get('tab_font'))
                env.renderer.set_font(page.tab_label_font)
                raw_text_size = page.get('tab_label_size', 200)
                lpadx = env.scale(page.get('tab_padx', raw_text_size // 6))
                lpady = env.scale(page.get('tab_pady', 0))
                max_height = page_height - 2 * lpady
                max_width = page_width - 2 * lpadx
                size = env.scale(raw_text_size)
                while size > 1:
                    height = env.renderer.text_line_height(size)
                    width = env.renderer.text_line_width(label, size)
                    page.tab_label_x = self.page_x1 - lpadx - width
                    page.tab_label_y = self.page_y1 - lpady - height
                    if (width < max_width) and (height < max_height): break
                    size = min(round(size * 0.9), size - 1)
                page.tab_label_size = size
                page.tab_label_color = color.parse(page.get('tab_label_color', "#fff1"))
            else:
                page.tab_label_size = 0
        if self.text:
            env.renderer.set_font(self.get('font'))
            self.text_x = x1 - self.button_text_size // 4 - \
                          env.renderer.text_line_width(self.text, self.button_text_size)

        # layout children
        for page in self.children:
            page.layout(env, x0, self.bar_y1, x1, y1)

    def _draw_button(self, env: ControlEnvironment, page: Control, y0: int):
        env.renderer.outline_box(
            page.tab_button_x0, y0, page.tab_button_x1, self.button_y1, 
            self.button_outline,
            page.tab_active_outline    if page.visible else page.tab_inactive_outline,
            page.tab_active_background if page.visible else page.tab_inactive_background,
            radius=self.button_radius)
        env.renderer.set_font(page.get('tab_font'))
        env.renderer.text_line(
            page.tab_button_text_x, self.button_text_y,
            self.button_text_size, page.tab_title,
            page.tab_active_color      if page.visible else page.tab_inactive_color)

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        current_page = None
        # upper-right text
        if self.text:
            env.renderer.set_font(self.get('font'))
            env.renderer.text_line(self.text_x, self.button_text_y, self.button_text_size, self.text, self.get('color', "fff"))
        # inactive tab buttons
        for page in self.children:
            if not page.visible:
                self._draw_button(env, page, y0)
            else:
                current_page = page
        if not current_page:
            return log.warning("no active page in TabSheet")
        # active tab button
        self._draw_button(env, current_page, y0)
        # page outline (if any) - drawn as lines to save on rasterized area
        if self.button_outline:
            c = current_page.tab_active_outline
            if x0 < current_page.tab_button_x0:
                env.renderer.box(x0, self.bar_y0, current_page.tab_button_x0 + self.button_outline, self.bar_y1, c)
            if current_page.tab_button_x1 < x1:
                env.renderer.box(current_page.tab_button_x1 - self.button_outline, self.bar_y0, x1, self.bar_y1, c)
            env.renderer.box(x0, self.bar_y0, self.page_x0, y1, c)
            env.renderer.box(self.page_x1, self.bar_y0, x1, y1, c)
            env.renderer.box(x0, self.page_y1, x1, y1, c)
        # page background
        env.renderer.box(
            self.page_x0, self.bar_y1, self.page_x1, self.page_y1,
            current_page.tab_active_background, current_page.tab_gradient)
        # page label
        if current_page.tab_label_size > 1:
            env.renderer.set_font(current_page.tab_label_font)
            env.renderer.text_line(
                current_page.tab_label_x, current_page.tab_label_y,
                current_page.tab_label_size, current_page.get('tab_label'),
                current_page.tab_label_color)

    def on_click(self, env: ControlEnvironment, x: int, y: int):
        self.click_x, self.click_y = x, y
        if self.geometry[1] <= y < self.bar_y1:
            prev_page = next_page = None
            for page in self.children:
                if page.visible:
                    prev_page = page
                if page.tab_button_x0 <= x < page.tab_button_x1:
                    next_page = page
            if next_page:
                if prev_page: prev_page.visible = False
                next_page.visible = True
        else:
            for child in self.children:
                x0, y0, x1, y1 = child.geometry
                if child.visible and (x0 <= x < x1) and (y0 <= y < y1):
                    self.drag_child = child
                    child.on_click(env, x, y)

###############################################################################
# MARK: Label

class Label(TextControl):
    """
    Text label to be put alongside other controls
    """

    def __init__(self, text, cmd=None, **style):
        """
        Instantiate the label with the following (mostly optional) parameters:
        [* = can be different for each control state; ~ = in abstract size units]
        - text   = text to display on the label
        - font   = font to use for the text
        - size ~ = default text size (will shrink automatically if text
                   doesn't fit)
        - halign = horizontal text alignment: 0=left, 1=right, 2=center (default)
        - valign = vertical text alignment: 0=top, 1=bottom, 2=middle (default)
        - color  = label color
        - bar    = width of horizontal bar next to the text
        """
        super().__init__(text, **style)

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        env.renderer.set_font(self.get('font'))
        font_size = env.scale(self.get('size', 50))
        self.text_layout = env.renderer.fit_text_in_box(
            x0, y0, x1, y1, font_size, self.text,
            self.get('halign', 2), self.get('valign', 2))
        bar_keepout = font_size // 3
        self.bar_left  = min(x0 for x0,y0,x1,y1,size,line in self.text_layout) - bar_keepout
        self.bar_right = max(x1 for x0,y0,x1,y1,size,line in self.text_layout) + bar_keepout
        self.bar_width = env.scale(self.get('bar', 0))
        self.bar_y0 = round((self.text_layout[0][1] + self.text_layout[-1][3] - self.bar_width) * 0.5)
        self.bar_y1 = self.bar_y0 + self.bar_width
        self.color = color.parse(self.get('color', "fffc"))

    def do_draw(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        env.renderer.set_font(self.get('font'))
        env.renderer.fitted_text(self.text_layout, self.color)
        if self.bar_width > 0:
            if self.bar_left > x0:
                env.renderer.box(x0, self.bar_y0, self.bar_left, self.bar_y1, self.color, self.color, self.bar_width)
            if self.bar_right < x1:
                env.renderer.box(self.bar_right, self.bar_y0, x1, self.bar_y1, self.color, self.color, self.bar_width)

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
        - text   = text to display on the button
        - cmd    = function to call when clicked; signature:
                       buttonCommand(env: ControlEnvironment, source: Button)
        - font   = font to use for the text
        - size ~ = default text size (will shrink automatically if text
                   doesn't fit)
        - halign = horizontal text alignment: 0=left, 1=right, 2=center (default)
        - valign = vertical text alignment: 0=top, 1=bottom, 2=middle (default)
        - border  ~ = border/outline width
        - radius  ~ = rounding radius
        - shadow  ~ = shadow size/offset
        - hue       = base hue in degrees (30 = red, 142 = green, 265 = blue)
        - sat       = base saturation (0.0 = monochrome, 0.37 = fully saturated)
        - light     = base lightness
        - color   * = text color
        - outline * = border/outline color
        - fill1   * = background color at the top
        - fill2   * = background color at the bottom
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
        The values of 'hue', 'sat' and 'light' are used to compute the other
        color values ('outline', 'fill1', 'fill2') for all major states (None,
        'active' and 'disabled') unless these are specified explicitly.
        """
        super().__init__(text, **style)
        self.cmd = cmd
        self.delayed_click = None

        # set colors based on Oklch values
        h = self.get('hue', 30)
        c = self.get('sat', 0.0)
        l = self.get('light', 0.75)
        lab_text = color.tooklab(color.parse(self.get('color', "000")))
        lab_light = color.lch2lab(0.98, 0.05, 100)
        t_light = 0.75
        lab_outline = color.lch2lab(l * 0.5,  c * 0.5, h)
        lab_fill1   = color.lch2lab(l + 0.05, c, h)
        lab_fill2   = color.lch2lab(l - 0.05, c, h)
        self.weak_set('outline', color.oklab(*lab_outline))
        self.weak_set('fill1',   color.oklab(*lab_fill1))
        self.weak_set('fill2',   color.oklab(*lab_fill2))
        self.weak_set('disabled_outline', color.oklch(l * 0.3, c * 0.25, h))
        self.weak_set('disabled_fill1',   color.oklch(l * 0.6 + 0.05, c * 0.5, h))
        self.weak_set('disabled_fill2',   color.oklch(l * 0.6 - 0.05, c * 0.5, h))
        self.weak_set('active_outline', color.oklab(*color.lerp(lab_outline, lab_light, t_light * 0.5)))
        self.weak_set('active_fill1',   color.oklab(*color.lerp(lab_fill1,   lab_light, t_light)))
        self.weak_set('active_fill2',   color.oklab(*color.lerp(lab_fill2,   lab_light, t_light)))
        self.weak_set('active_color',   color.oklab(*color.lerp(lab_text,    lab_light, t_light * 0.5)))

    @property
    def active(self):
        return (self.state == 'active')

    def do_layout(self, env: ControlEnvironment, x0: int, y0: int, x1: int, y1: int):
        self.border = env.scale(self.get('border', 3))
        self.shadow = env.scale(self.get('shadow', 15))
        self.radius = env.scale(self.get('radius', 25))
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
