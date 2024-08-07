"""
Conversion to and operations on color values represented as RGBA 4-tuples
of normalized floating point sRGB values.
"""
import logging

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
