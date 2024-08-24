# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT
"""
Conversion to and operations on color values represented as RGBA 4-tuples
of normalized floating point sRGB values.
"""
import logging
import math

__all__ = ['import']

_importcache = {}

def parse(c):
    "import a color from a hex code into the standard format"
    if isinstance(c, (tuple, list)):
        if len(c) == 4: return c
        if len(c) == 3: return (*c, 1.0)
    try:
        return _importcache[c]
    except KeyError:
        pass
    res = None
    if isinstance(c, str):
        if c.startswith('#'): c = c[1:]
        res = None
        try:
            if len(c) == 3: res = (int(c[0],16)/15, int(c[1],16)/15, int(c[2],16)/15, 1.0)
            if len(c) == 4: res = tuple(int(_,16)/15 for _ in c)
            if len(c) == 6: res = (int(c[0:2],16)/255, int(c[2:4],16)/255, int(c[4:6],16)/255, 1.0)
            if len(c) == 8: res = (int(c[0:2],16)/255, int(c[2:4],16)/255, int(c[4:6],16)/255, int(c[6:8],16)/255)
        except ValueError:
            pass
    if not res:
        logging.error("invalid color %s", repr(c))
        res = (1.0, 0.0, 1.0, 1.0)
    _importcache[c] = res
    return res


def linear2srgb(x: float):
    "convert a single component from normalized linear to normalized sRGB"
    return (x * 12.92) if (x <= 0.0031308) else (1.055 * (x ** (1.0/2.4)) - 0.055)

def srgb2linear(x: float):
    "convert a single component from normalized sRGB to normalized linear"
    return (x / 12.92) if (x <= 0.04045) else (((x + 0.055) / 1.055) ** 2.4)


def oklab(l: float, a: float = 0.0, b: float = 0.0, alpha: float = 1.0):
    "generate a color by converting it from the Oklab color space"
    l_ = l + 0.3963377774 * a + 0.2158037573 * b;  l_ *= l_ * l_
    m_ = l - 0.1055613458 * a - 0.0638541728 * b;  m_ *= m_ * m_
    s_ = l - 0.0894841775 * a - 1.2914855480 * b;  s_ *= s_ * s_
    return (
        linear2srgb(+4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_),
        linear2srgb(-1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_),
        linear2srgb(-0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_),
        alpha)


def oklch(l: float, c: float, h: float, alpha: float = 1.0):
    "generate a color by converting it from the Oklch color space"
    a = math.radians(h)
    return oklab(l, c * math.cos(a), c * math.sin(a), alpha)


def lch2lab(l: float, c: float, h: float):
    "convert Lch color coordinate into Lab color coordinate"
    a = math.radians(h)
    return (l, c * math.cos(a), c * math.sin(a))


def lerp(a, b, t: float):
    "linearly interpolate values from a to b; inputs can be scalars or sequences"
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    else:
        return tuple((xa + (xb - xa) * t) for xa, xb in zip(a, b))


def scale(c, t: float):
    "scale all RGB components (but not alpha) by t, to darken / brighten"
    return (c[0]*t, c[1]*t, c[2]*t, c[3])


def alpha(c, a: float):
    "scale the alpha component by a"
    return (c[0], c[1], c[2], c[3]*a)


def tohex(c):
    "convert a color tuple back to a hexadecimal representation"
    return '#' + ''.join("{:02x}".format(min(255, max(0, round(x * 255.0)))) for x in c)


def tooklab(c):
    "convert a color tuple to an Oklab (l,a,b) tuple"
    r_, g_, b_ = map(srgb2linear, c[:3])
    l_ = (0.4122214708 * r_ + 0.5363325363 * g_ + 0.0514459929 * b_) ** (1.0/3.0)
    m_ = (0.2119034982 * r_ + 0.6806995451 * g_ + 0.1073969566 * b_) ** (1.0/3.0)
    s_ = (0.0883024619 * r_ + 0.2817188376 * g_ + 0.6299787005 * b_) ** (1.0/3.0)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


###############################################################################

if __name__ == "__main__":  # unit test
    # compare some colors against references
    def _hex2ansibg(c): return '\x1b[48;2;' + ';'.join(str(int(c[p:p+2], 16)) for p in (1,3,5)) + 'm'
    def rgb(r,g,b): return (r/255, g/255, b/255, 1.0)
    for csp, a,b,c, wanted in [
        # from https://observablehq.com/@shan/oklab-color-wheel
        (oklab,  0.800,  0.250,  0.000, rgb(255, 99, 183)),
        (oklab,  0.800,  0.000,  0.250, rgb(252, 175, 0)),
        (oklab,  0.800, -0.250,  0.000, rgb(0, 237, 196)),
        (oklab,  0.800,  0.000, -0.250, rgb(130, 171, 255)),
        (oklab,  0.530, -0.068, -0.048, rgb(33, 120, 138)),
        # from https://oklch.com/
        (oklch,  0.65, 0.24,  33, parse("#ff3600")),
        (oklch,  0.67, 0.08, 245, parse("#6b9bc4")),
    ]:
        got = tohex(csp(a,b,c))[:7]
        wanted = tohex(wanted)[:7]
        diff = [int(got[p:p+2], 16) - int(wanted[p:p+2], 16) for p in (1,3,5)]
        dist = math.sqrt(sum(d*d for d in diff))
        print(f"{_hex2ansibg(got)} {_hex2ansibg(wanted)} \x1b[0m {csp.__name__:>9s}({a:6.2f}, {b:6.2f}, {c:6.2f}): got {got}, wanted {wanted} -> delta {dist:4.1f}")
