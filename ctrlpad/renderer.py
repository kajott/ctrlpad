import array
import ctypes
import json
import os
from PIL import Image

from .opengl import gl, GLProgram

###############################################################################
#MARK: shader

_rendershader = """
    varying vec2  vTC;
    varying float vMode;
    varying vec3  vSize;
    varying vec2  vBR;
    varying vec4  vColor;
[vert]
    attribute vec2  aPos;   // 0 1
    attribute vec2  aTC;    //     2 3
    attribute float aMode;  //         4
    attribute vec3  aSize;  //           5 6 7
    attribute vec2  aBR;    //                 8 9
    attribute vec4  aColor; //                     10 11 12 13   -> 14 total
    uniform vec4 uArea;
    uniform vec2 uTexSize;
    void main() {
        gl_Position = vec4(aPos * uArea.xy + uArea.zw, 0., 1.);
        vTC    = (aMode < 0.5) ? aTC : (aTC / uTexSize);
        vMode  = aMode;
        vSize  = aSize;
        vBR    = aBR;
        vColor = aColor;
    }
[frag]
    uniform sampler2D uTex;
    void main() {
        float d = 0.;
        if (vMode < 0.5) {  // box mode
            vec2 p = abs(vTC) - vSize.xy;
            d = (min(p.x, p.y) > (-vSize.z))
              ? (vSize.z - length(p + vec2(vSize.z)))
              : min(-p.x, -p.y);
        } else if (vMode < 1.5) {  // MSDF text mode
            vec3 s = texture2D(uTex, vTC).rgb;
            d = max(min(s.r, s.g), min(max(s.r, s.g), s.b)) - 0.5;
            d /= fwidth(d) * 1.25;
        } else {  // simple texture mode
            gl_FragColor = texture2D(uTex, vTC);
            return;
        }
        gl_FragColor = vec4(vColor.rgb, vColor.a * clamp((d - vBR.x) * vBR.y + 0.5, 0.0, 1.0));
    }
"""

###############################################################################
#MARK: texture atlas

class AtlasFullError(ValueError): pass

class TextureAtlas:
    def __init__(self):
        self.img = Image.new('RGBA', (16, 16))
        self.tex = gl.make_texture(filter=gl.LINEAR)

    def __init__(self, initsize=(512, 512), maxsize=None):
        self.img = Image.new('RGBA', initsize)
        self.tex = gl.make_texture(filter=gl.LINEAR) if gl else 0
        self.tex_valid = False
        if not(maxsize) and gl:
            res = (ctypes.c_int * 1)()
            gl.GetIntegerv(gl.MAX_TEXTURE_SIZE, res)
            maxsize = res[0]
        self.maxsize = maxsize or 32768
        self.front = [(0,0)]

    def _fit(self, img: Image, x0: int, y0: int):
        sx, sy = self.img.size
        x1 = x0 + img.size[0]
        y1 = y0 + img.size[1]
        while x1 > sx: sx *= 2
        while y1 > sy: sy *= 2
        return ((sx, sy), sx*sy)

    def put(self, img):
        if isinstance(img, str):
            img = Image.open(img)
        img.load()
        img = img.convert('RGBA')

        # find the best spot along the front to add the image
        x0, y0 = -1, -1
        min_waste = 999999999
        curr_size = self.img.size[0] * self.img.size[1]
        for i in range(len(self.front)):
            x, y = self.front[i]
            yend = y + img.size[1]
            consider = [j for j in range(i, len(self.front)) if self.front[j][1] < yend]
            x = max(self.front[j][0] for j in consider)
            xend = x + img.size[0]
            if max(xend, yend) > self.maxsize:
                continue  # exceeds max atlas size
            waste = self._fit(img, x, y)[1] - curr_size
            #print(f"     {self.front[i][0]},{self.front[i][1]}? would end up at {x},{y}, wasting {waste}")
            for j in consider:
                jx, jystart = self.front[j]
                jyend = self.front[j+1][1] if ((j+1) < len(self.front)) else yend
                jwaste = (x - jx) * (min(jyend, yend) - jystart)  # waste due to padded pixels on the left
                ewaste = ((xend - jx) * (jyend - yend)) if ((jyend - img.size[1]) < yend < jyend) else 0  # extra waste if creating flat remaining space
                #print(f"          F{j:02d} {jx=} {jystart=} {jyend=} {jwaste=} {ewaste=}")
                waste += jwaste + (ewaste // 4)
            #print(f"     {self.front[i][0]},{self.front[i][1]}? total waste={waste} considering {consider}")
            if waste < min_waste:
                x0, y0 = x, y
                min_waste = waste
        if min(x0, y0) < 0:
            raise AtlasFullError("no space left in texture atlas")

        # update the front to match the new atlas
        x1 = x0 + img.size[0]
        y1 = y0 + img.size[1]
        newfront = [p for p in self.front if p[1] < y0] + [(x1, y0)]
        # add a new point at the lower end of the new image, unless there's
        # already one
        for i in range(1, len(self.front)):
            y = self.front[i][1]
            if y < y1: continue
            if (y > y1) and (self.front[i-1][1] >= y0):
                newfront.append((self.front[i-1][0], y1))
            if y >= y1: break
        end = [p for p in self.front if p[1] >= y1]
        if not end:
            newfront.append((0, y1))
        self.front = newfront + end

        # paste into atlas, enlarge if needed
        newsize = self._fit(img, x0, y0)[0]
        if newsize > self.img.size:
            img2 = Image.new('RGBA', newsize)
            img2.paste(self.img, (0,0))
            self.img = img2
            self.tex_valid = False
        self.img.paste(img, (x0, y0))

        # upload texture
        if gl:
            gl.BindTexture(gl.TEXTURE_2D, self.tex)
            if self.tex_valid:
                gl.TexSubImage2D(gl.TEXTURE_2D, 0, x0, y0, img.size[0], img.size[1], gl.RGBA, gl.UNSIGNED_BYTE, img.tobytes())
            else:
                gl.TexImage2D(gl.TEXTURE_2D, 0, gl.RGBA, self.img.size[0], self.img.size[1], 0, gl.RGBA, gl.UNSIGNED_BYTE, self.img.tobytes())
                self.tex_valid = True
        return (x0, y0)

if 0:  # texture atlas unit test
    import random; random.seed(0x13375EED)
    a = TextureAtlas(maxsize=1024)
    predefined = ["bahn.png", "segoe.png"]
    n = 0
    while n<4e9:
        try:
            img = Image.open(predefined.pop(0))
        except IndexError:
            w = random.randrange(10, 100)
            h = random.randrange(10, 100)
            rgb = [random.randrange(64, 128), random.randrange(128, 192), random.randrange(192, 256)]
            random.shuffle(rgb)
            img = Image.new('RGB', (w,h), tuple(c^0xFF for c in rgb))
            img.paste(Image.new('RGB', (w-2, h-2), tuple(rgb)), (1,1))
        #print(f"#{n:02d}: {img.size[0]}x{img.size[1]} ...")
        try:
            x,y = a.put(img)
        except AtlasFullError:
            break
        print(f"#{n:02d}: {img.size[0]}x{img.size[1]} @ {x},{y} / {a.img.size[0]}x{a.img.size[1]}")
        #print(a.front)
        n += 1
    print("fitted", n, "images into", a.img.size, "pixels")
    a.img.show()
    import sys; sys.exit(0)

###############################################################################
#MARK: font loader

class MSDFFont:
    _nullglyph = (0.5, False, 0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0)

    def __init__(self, filename: str, attex: TextureAtlas):
        basename = os.path.splitext(filename)[0]
        with open(basename + ".json") as f:
            data = json.load(f)
        #import pprint; pprint.pprint(data)
        self.name = data.get('name', "???")

        atlas = data.get('atlas', {})
        img_width  = atlas.get('width',  100)
        img_height = atlas.get('height', 100)
        self.atlas = attex
        img_x0, img_y0 = self.atlas.put(basename + ".png")

        metrics = data.get('metrics', {})
        asc  = metrics.get('ascender', 1.0)
        desc = metrics.get('descender', 0.0)
        self.line_height = metrics.get('lineHeight', 1.0)
        self.max_height = asc - desc
        ult = metrics.get('underlineThickness', 0.01)
        uly = metrics.get('underlineY', -0.02)
        self.underline_y0 = asc - uly - 0.5 * ult
        self.underline_y1 = asc - uly + 0.5 * ult
        self.baseline = asc

        self.glyphs = {}  # cp: (advance, has_image_flag, x0,y0, x1,y1, u0,v0, u1,v1)
        for glyph in data.get('glyphs', []):
            cp = glyph.get('unicode', 0)
            adv = glyph.get('advance', 0.0)
            ab = glyph.get('atlasBounds')
            pb = glyph.get('planeBounds')
            if ab and pb:
                self.glyphs[cp] = (adv, True,
                    pb['left'],  asc - pb['top'],
                    pb['right'], asc - pb['bottom'],
                    img_x0 +              ab['left'],
                    img_y0 + img_height - ab['top'],
                    img_x0 +              ab['right'],
                    img_y0 + img_height - ab['bottom'])
            else:
                self.glyphs[cp] = (adv, False, 0.0,0.0,0.0,0.0, 0.0,0.0,0.0,0.0)
        # for cp, g in sorted(self.glyphs.items()): print(cp, g)

        self.fallback = self._nullglyph
        for cp in (0xFFFD, ord('?'), 32):
            if cp in self.glyphs:
                self.fallback = self.glyphs[cp]
                break

        self.kern = {}
        for pair in data.get('kerning', []):
            self.kern[(pair.get('unicode1', 0), pair.get('unicode2', 0))] = pair.get('advance', 0.0)

    def width(self, text: str, size: float = 1.0):
        x = 0.0
        prev = 0
        for cp in map(ord, text):
            x += self.kern.get((prev, cp), 0.0) + self.glyphs.get(cp, self.fallback)[0]
            prev = cp
        return x * size

class NullFont:
    def __init__(self, atlas: TextureAtlas):
        self.atlas = atlas
        self.line_height = self.max_height = self.baseline = 0.0
        self.fallback = MSDFFont._nullglyph
        self.glyphs = {}
        self.kern = {}
    def __bool__(self):
        return False

###############################################################################
#MARK: renderer

class Renderer:
    vertex_attrib_count = 14
    vertex_size = vertex_attrib_count * 4
    batch_size = 65536 // (vertex_size * 4)
    vbo_items_per_quad = vertex_attrib_count * 4
    max_vbo_items = batch_size * vbo_items_per_quad
    _colorcache = {}

    def __init__(self):
        self.prog = GLProgram(_rendershader)
        self.ibo, self.vbo = gl.GenBuffers(2)
        gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.ibo)
        gl.BufferData(gl.ELEMENT_ARRAY_BUFFER, type=gl.UNSIGNED_SHORT, usage=gl.STATIC_DRAW,
                      data=[i+o for i in range(0, self.batch_size * 4, 4) for o in (0,2,1,1,2,3)])

        gl.BindBuffer(gl.ARRAY_BUFFER, self.vbo)
        gl.set_enabled_attribs(*self.prog.attributes.values())
        gl.VertexAttribPointer(self.prog.attributes['aPos'],   2, gl.FLOAT, gl.FALSE, self.vertex_size,  0 * 4)
        gl.VertexAttribPointer(self.prog.attributes['aTC'],    2, gl.FLOAT, gl.FALSE, self.vertex_size,  2 * 4)
        gl.VertexAttribPointer(self.prog.attributes['aMode'],  1, gl.FLOAT, gl.FALSE, self.vertex_size,  4 * 4)
        gl.VertexAttribPointer(self.prog.attributes['aSize'],  3, gl.FLOAT, gl.FALSE, self.vertex_size,  5 * 4)
        gl.VertexAttribPointer(self.prog.attributes['aBR'],    2, gl.FLOAT, gl.FALSE, self.vertex_size,  8 * 4)
        gl.VertexAttribPointer(self.prog.attributes['aColor'], 4, gl.FLOAT, gl.FALSE, self.vertex_size, 10 * 4)
        gl.BindBuffer(gl.ARRAY_BUFFER, 0)
        gl.Disable(gl.DEPTH_TEST)
        gl.Enable(gl.BLEND)
        gl.BlendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)

        self.data = array.array('f')
        self.tex = 0
        self.atlas = TextureAtlas()
        self.set_texture(self.atlas)
        self.fonts = {}
        self.fallback_font = NullFont(self.atlas)
        self.font = self.fallback_font

    def begin_frame(self, viewport_width: int, viewport_height: int):
        self.prog.use()
        gl.Uniform4f(self.prog.uArea, 2.0 / viewport_width, -2.0 / viewport_height, -1.0, 1.0)
        self.data = array.array('f')

    def flush(self):
        if not len(self.data): return
        assert not(len(self.data) % self.vbo_items_per_quad)
        self.prog.use()
        addr, size = self.data.buffer_info()
        gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.ibo)
        gl.BindBuffer(gl.ARRAY_BUFFER, self.vbo)
        gl.BufferData(gl.ARRAY_BUFFER, type=gl.FLOAT, usage=gl.STATIC_DRAW, data=addr, size=size*self.data.itemsize)
        gl.BindTexture(gl.TEXTURE_2D, self.tex)
        gl.DrawElements(gl.TRIANGLES, len(self.data) // self.vbo_items_per_quad * 6, gl.UNSIGNED_SHORT, ctypes.c_void_p(0))
        self.data = array.array('f')

    def _new_quad(self):
        if len(self.data) > self.max_vbo_items:
            self.flush()

    def set_texture(self, tex, w:int=1, h:int=1):
        if isinstance(tex, TextureAtlas):
            return self.set_texture(tex.tex, *tex.img.size)
        if tex == self.tex: return
        self.flush()
        self.prog.use()
        gl.Uniform2f(self.prog.uTexSize, w, h)
        self.tex = tex

    def add_font(self, filename):
        try:
            self.font = MSDFFont(filename, self.atlas)
        except Exception as e:
            print(f"ERROR: can not load font '{filename}' - {e}")
            return None
        # the atlas might have been resized -> force coordinate update
        self.tex = 0
        self.set_texture(self.font.atlas)
        self.fonts[self.font.name] = self.font
        if not self.fallback_font:
            self.fallback_font = self.font
        return self.font.name

    def set_font(self, font):
        if isinstance(font, str):
            self.font = self.fonts.get(font, self.fallback_font)
        else:
            self.font = font
        return self.font

    @staticmethod
    def color(c):
        if isinstance(c, (tuple, list)):
            if len(c) == 4: return c
            if len(c) == 3: return (*c, 1.0)
        elif isinstance(c, str):
            try:
                return Renderer._colorcache[c]
            except KeyError:
                pass
            if c.startswith('#'): c = c[1:]
            res = None
            if len(c) == 3: res = (int(c[0],16)/15, int(c[1],16)/15, int(c[2],16)/15, 1.0)
            if len(c) == 4: res = tuple(int(_,16)/15 for _ in c)
            if len(c) == 6: res = (int(c[0:2],16)/255, int(c[2:4],16)/255, int(c[4:6],16)/255, 1.0)
            if len(c) == 8: res = (int(c[0:2],16)/255, int(c[2:4],16)/255, int(c[4:6],16)/255, int(c[6:8],16)/255)
            if res:
                Renderer._colorcache[c] = res
                return res
        raise TypeError("invalid color " + repr(c))

    def box(self, x0, y0, x1, y1, colorU, colorL=None, radius=0.0, blur=1.0, offset=0.0):
        colorU = self.color(colorU)
        colorL = self.color(colorL) if not(colorL is None) else colorU
        self._new_quad()
        w = (x1 - x0) * 0.5
        h = (y1 - y0) * 0.5
        r = min(min(w, h), radius)
        s = 1.0 / max(blur, 1.0/256)
        self.data.extend([
            # X,Y,  tcX,tcY,mode,szX,szY,szR, offset,blur, color
            x0, y0,  -w, -h, 0.0,  w,  h,  r, offset,   s, *colorU,
            x1, y0,   w, -h, 0.0,  w,  h,  r, offset,   s, *colorU,
            x0, y1,  -w,  h, 0.0,  w,  h,  r, offset,   s, *colorL,
            x1, y1,   w,  h, 0.0,  w,  h,  r, offset,   s, *colorL,
        ])

    def outline_box(self, x0, y0, x1, y1, width, colorO, colorU, colorL=None, radius=0.0, shadow_offset=0.0, shadow_blur=0.0, shadow_alpha=1.0, shadow_grow=0.0):
        if ((shadow_offset > 0.0) or (shadow_grow > 0.0)) and (shadow_alpha > 0.0):
            black = (0.0, 0.0, 0.0, shadow_alpha)
            self.box(x0 + shadow_offset - shadow_grow,
                     y0 + shadow_offset - shadow_grow,
                     x1 + shadow_offset + shadow_grow,
                     y1 + shadow_offset + shadow_grow,
                     black,
                     radius = radius + shadow_grow,
                     blur   = shadow_blur + 1.0,
                     offset = shadow_blur)
        self.box(x0, y0, x1, y1, colorO, radius=radius)
        self.box(x0 + width, y0 + width, x1 - width, y1 - width, colorU, colorL, radius=radius-width)

    def text_line(self, x, y, size, text:str, colorU="fff", colorL=None, align=0):
        self.set_texture(self.font.atlas)
        colorU = self.color(colorU)
        colorL = self.color(colorL) if not(colorL is None) else colorU
        if align:
            x -= self.font.width(text, size) / align
        prev = 0
        for cp in map(ord, text):
            x += self.font.kern.get((prev, cp), 0.0) * size
            adv, valid, px0,py0,px1,py1, tx0,ty0,tx1,ty1 = self.font.glyphs.get(cp, self.font.fallback)
            if valid:
                self._new_quad()
                self.data.extend([
                    # x,          y,             tcX,tcY, mode, szX,szY,szR, off,blur, color
                    x + px0*size, y + py0*size,  tx0,ty0,  1.0, 0.0,0.0,0.0, 0.0,1.33, *colorU,
                    x + px1*size, y + py0*size,  tx1,ty0,  1.0, 0.0,0.0,0.0, 0.0,1.33, *colorU,
                    x + px0*size, y + py1*size,  tx0,ty1,  1.0, 0.0,0.0,0.0, 0.0,1.33, *colorL,
                    x + px1*size, y + py1*size,  tx1,ty1,  1.0, 0.0,0.0,0.0, 0.0,1.33, *colorL,
                ])
            x += adv * size
            prev = cp 

    def text(self, x, y, size, text, color="fff", halign=0, valign=0, line_spacing=1.0):
        if isinstance(text, str):
            text = text.split('\n')
        line_spacing *= self.font.line_height * size
        if valign:
            y -= (line_spacing * (len(text) - 1) + self.font.max_height * size) / valign
        for line in text:
            self.text_line(x, y, size, line, color, align=halign)
            y += line_spacing

###############################################################################
#MARK: font importer

def PrepareFont(name, fontfile=None, msdf_atlas_gen=None, size=32):
    import re
    import subprocess
    import tempfile
    if not fontfile:
        fontfile = name.capitalize()
    if not os.path.isfile(fontfile):
        res = subprocess.run(["fc-match", "-v", fontfile], capture_output=True)
        m = re.search(r'file: "(.*?)"', res.stdout.decode(errors='replace'))
        fontfile = m.group(1)
        assert fontfile, "no font file found"
    if not msdf_atlas_gen:
        import shutil
        msdf_atlas_gen = shutil.which("msdf-atlas-gen")
        assert msdf_atlas_gen, "msdf-atlas-gen not found"
    subprocess.run([msdf_atlas_gen,
        "-font", fontfile,
        "-chars", "[0x20, 0x7E], [0xA0, 0xFF], 0xFFFD",
        "-fontname", os.path.basename(name),
        "-type", "msdf",
        "-size", str(size),
        "-format", "png",
        "-imageout", os.path.splitext(name)[0] + ".png",
        "-json", os.path.splitext(name)[0] + ".json"])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='cmd')
    mkfont = subs.add_parser('preparefont', help="convert a .ttf font into .png+.json using msdf-atlas-gen")
    mkfont.add_argument("font_name",
                        help="name of the font and the output files", nargs=1)
    mkfont.add_argument("-i", "--infile", metavar="input.ttf",
                        help="input font file name, or fontconfig spec (e.g. 'Arial:style=Bold')")
    mkfont.add_argument("-p", "--prog", metavar="PATH",
                        help="specify full path to msdf-atlas-gen(.exe); get it from https://github.com/Chlumsky/msdf-atlas-gen")
    mkfont.add_argument("-s", "--size", metavar="PIXELS", type=int, default=32,
                        help="base font size to render")
    args = parser.parse_args()
    if args.cmd == 'preparefont':
        PrepareFont(name=args.font_name[0], fontfile=args.infile, msdf_atlas_gen=args.prog, size=args.size)
