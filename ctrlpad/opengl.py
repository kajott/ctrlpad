import ctypes
import sys
import re

__all__ = ['gl', 'GLShader', 'GLProgram']

class _OpenGL:
    "OpenGL loader and minimal OpenGL interface"
    # constants ("enums" in OpenGL)
    FALSE = 0
    TRUE = 1
    NO_ERROR = 0
    INVALID_ENUM = 0x0500
    INVALID_VALUE = 0x0501
    INVALID_OPERATION = 0x0502
    OUT_OF_MEMORY = 0x0505
    INVALID_FRAMEBUFFER_OPERATION = 0x0506
    VENDOR = 0x1F00
    RENDERER = 0x1F01
    VERSION = 0x1F02
    EXTENSIONS = 0x1F03
    VIEWPORT = 0x0BA2
    POINTS = 0x0000
    LINES = 0x0001
    LINE_LOOP = 0x0002
    LINE_STRIP = 0x0003
    TRIANGLES = 0x0004
    TRIANGLE_STRIP = 0x0005
    TRIANGLE_FAN = 0x0006
    BYTE = 0x1400
    UNSIGNED_BYTE = 0x1401
    SHORT = 0x1402
    UNSIGNED_SHORT = 0x1403
    INT = 0x1404
    UNSIGNED_INT = 0x1405
    FLOAT = 0x1406
    DEPTH_TEST = 0x0B71
    BLEND = 0x0BE2
    ZERO = 0
    ONE = 1
    SRC_COLOR = 0x0300
    ONE_MINUS_SRC_COLOR = 0x0301
    SRC_ALPHA = 0x0302
    ONE_MINUS_SRC_ALPHA = 0x0303
    DST_ALPHA = 0x0304
    ONE_MINUS_DST_ALPHA = 0x0305
    DST_COLOR = 0x0306
    ONE_MINUS_DST_COLOR = 0x0307
    DEPTH_BUFFER_BIT = 0x00000100
    COLOR_BUFFER_BIT = 0x00004000
    TEXTURE0 = 0x84C0
    TEXTURE_2D = 0x0DE1
    TEXTURE_RECTANGLE = 0x84F5
    TEXTURE_MAG_FILTER = 0x2800
    TEXTURE_MIN_FILTER = 0x2801
    TEXTURE_WRAP_S = 0x2802
    TEXTURE_WRAP_T = 0x2803
    NEAREST = 0x2600
    LINEAR = 0x2601
    NEAREST_MIPMAP_NEAREST = 0x2700
    LINEAR_MIPMAP_NEAREST = 0x2701
    NEAREST_MIPMAP_LINEAR = 0x2702
    LINEAR_MIPMAP_LINEAR = 0x2703
    CLAMP_TO_BORDER = 0x812D
    CLAMP_TO_EDGE = 0x812F
    REPEAT = 0x2901
    ALPHA = 0x1906
    RGB = 0x1907
    RGBA = 0x1908
    LUMINANCE = 0x1909
    LUMINANCE_ALPHA = 0x190A
    RED = 0x1903
    R8 = 0x8229
    ARRAY_BUFFER = 0x8892
    ELEMENT_ARRAY_BUFFER = 0x8893
    STREAM_DRAW = 0x88E0
    STATIC_DRAW = 0x88E4
    DYNAMIC_DRAW = 0x88E8
    FRAGMENT_SHADER = 0x8B30
    VERTEX_SHADER = 0x8B31
    COMPILE_STATUS = 0x8B81
    LINK_STATUS = 0x8B82
    INFO_LOG_LENGTH = 0x8B84
    UNPACK_ALIGNMENT = 0x0CF5
    MAX_TEXTURE_SIZE = 0x0D33
    _funcs = [  # function prototypes
        ("GetString",                ctypes.c_char_p, ctypes.c_uint),
        ("Enable",                   None, ctypes.c_uint),
        ("Disable",                  None, ctypes.c_uint),
        ("GetError",                 ctypes.c_uint),
        ("Viewport",                 None, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int),
        ("Clear",                    None, ctypes.c_uint),
        ("ClearColor",               None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float),
        ("BlendFunc",                None, ctypes.c_uint, ctypes.c_uint),
        ("GenTextures",              None, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)),
        ("BindTexture",              None, ctypes.c_uint, ctypes.c_int),
        ("ActiveTexture",            None, ctypes.c_uint),
        ("TexParameteri",            None, ctypes.c_uint, ctypes.c_uint, ctypes.c_int),
        ("TexImage2D",               None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p),
        ("TexSubImage2D",            None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p),        ("GenerateMipmap",           None, ctypes.c_uint),
        ("GenBuffers",               None, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)),
        ("BindBuffer",               None, ctypes.c_uint, ctypes.c_int),
        ("BufferData",               None, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint),
        ("CreateProgram",            ctypes.c_uint),
        ("DeleteProgram",            None, ctypes.c_uint),
        ("CreateShader",             ctypes.c_uint, ctypes.c_uint),
        ("DeleteShader",             None, ctypes.c_uint),
        ("ShaderSource",             None, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p),
        ("CompileShader",            None, ctypes.c_uint),
        ("GetShaderiv",              None, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)),
        ("GetShaderInfoLog",         None, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p),
        ("AttachShader",             None, ctypes.c_uint, ctypes.c_uint),
        ("LinkProgram",              None, ctypes.c_uint),
        ("GetProgramiv",             None, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)),
        ("GetProgramInfoLog",        None, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p),
        ("UseProgram",               None, ctypes.c_uint),
        ("BindAttribLocation",       None, ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p),
        ("GetAttribLocation",        ctypes.c_int, ctypes.c_uint, ctypes.c_char_p),
        ("GetUniformLocation",       ctypes.c_int, ctypes.c_uint, ctypes.c_char_p),
        ("Uniform1f",                None, ctypes.c_uint, ctypes.c_float),
        ("Uniform2f",                None, ctypes.c_uint, ctypes.c_float, ctypes.c_float),
        ("Uniform3f",                None, ctypes.c_uint, ctypes.c_float, ctypes.c_float, ctypes.c_float),
        ("Uniform4f",                None, ctypes.c_uint, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float),
        ("Uniform1i",                None, ctypes.c_uint, ctypes.c_int),
        ("Uniform2i",                None, ctypes.c_uint, ctypes.c_int, ctypes.c_int),
        ("Uniform3i",                None, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_int),
        ("Uniform4i",                None, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int),
        ("EnableVertexAttribArray",  None, ctypes.c_uint),
        ("DisableVertexAttribArray", None, ctypes.c_uint),
        ("VertexAttribPointer",      None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p),
        ("DrawArrays",               None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint),
        ("DrawElements",             None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p),
        ("PixelStorei",              None, ctypes.c_uint, ctypes.c_uint),
        ("GetIntegerv",              None, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)),
    ]
    _typemap = {  # OpenGL typecode to Python/ctypes mapping
                  BYTE: ctypes.c_int8,
         UNSIGNED_BYTE: ctypes.c_uint8,
                 SHORT: ctypes.c_int16,
        UNSIGNED_SHORT: ctypes.c_uint16,
                   INT: ctypes.c_int32,
          UNSIGNED_INT: ctypes.c_uint32,
                 FLOAT: ctypes.c_float
    }

    def __init__(self):
        self.good = False
        self.enabled_attribs = set()
    def __bool__(self):
        return self.good

    def _load(self, get_proc_address):
        "load function pointers using the provided get_proc_address function"
        GLFUNCTYPE = ctypes.WINFUNCTYPE if (sys.platform == 'win32') else ctypes.CFUNCTYPE
        for name, ret, *args in self._funcs:
            funcptr = None
            for suffix in ("", "ARB", "ObjectARB", "EXT", "OES"):
                funcptr = get_proc_address(ctypes.c_char_p(("gl" + name + suffix).encode()))
                if funcptr:
                    break
            if funcptr:
                funcptr = GLFUNCTYPE(ret, *args)(funcptr)
            else:
                raise ImportError("failed to import required OpenGL function 'gl%s'" % name)
            setattr(self, ('_' + name) if hasattr(self, name) else name, funcptr)
        self.enabled_attribs = set()
        self.good = True

    ##### convenience wrappers around functions that are cumbersome to use otherwise

    def GenTextures(self, n=1):
        "generate one or more textures and return them (as a list if n>1)"
        bufs = (ctypes.c_int * n)()
        self._GenTextures(n, bufs)
        if n == 1: return bufs[0]
        return list(bufs)

    def ActiveTexture(self, tmu):
        "as glActiveTexture(), but parameter may also be 0..n instead of GL_TEXTURE0...GL_TEXTUREn"
        if tmu < self.TEXTURE0:
            tmu += self.TEXTURE0
        self._ActiveTexture(tmu)

    def GenBuffers(self, n=1):
        "generate one or more buffer objects and return them (as a list if n>1)"
        bufs = (ctypes.c_int * n)()
        self._GenBuffers(n, bufs)
        if n == 1: return bufs[0]
        return list(bufs)

    def BufferData(self, target, size=0, data=None, usage=STATIC_DRAW, type=None):
        "as glBufferData(), but the 'data' parameter may be a Python list of numbers"
        if isinstance(data, list):
            if type:
                type = self._typemap[type]
            elif isinstance(data[0], int):
                type = ctypes.c_int32
            elif isinstance(data[0], float):
                type = ctypes.c_float
            else:
                raise TypeError("cannot infer buffer data type")
            size = len(data) * ctypes.sizeof(type)
            data = (type * len(data))(*data)
        self._BufferData(target, ctypes.cast(size, ctypes.c_void_p), ctypes.cast(data, ctypes.c_void_p), usage)

    def ShaderSource(self, shader, source):
        "glShaderSource(), but with the source being a single Python string"
        source = ctypes.c_char_p(source.encode())
        self._ShaderSource(shader, 1, ctypes.pointer(source), None)

    def GetShaderi(self, shader, pname):
        "glGetShaderiv() for queries that only return a single integer"
        res = (ctypes.c_uint * 1)()
        self.GetShaderiv(shader, pname, res)
        return res[0]

    def GetShaderInfoLog(self, shader):
        "return shader compiler info log as a Python string"
        length = self.GetShaderi(shader, self.INFO_LOG_LENGTH)
        if not length: return ""
        buf = ctypes.create_string_buffer(length + 1)
        self._GetShaderInfoLog(shader, length + 1, None, buf)
        return buf.raw.split(b'\0', 1)[0].decode(errors='replace')

    def GetProgrami(self, program, pname):
        "glGetProgramiv() for queries that only return a single integer"
        res = (ctypes.c_uint * 1)()
        self.GetProgramiv(program, pname, res)
        return res[0]

    def GetProgramInfoLog(self, program):
        "return program linker info log as a Python string"
        length = self.GetProgrami(program, self.INFO_LOG_LENGTH)
        if not length: return ""
        buf = ctypes.create_string_buffer(length + 1)
        self._GetProgramInfoLog(program, length + 1, None, buf)
        return buf.raw.split(b'\0', 1)[0].decode(errors='replace')

    ##### higher-level convenience functions

    def set_enabled_attribs(self, *attrs):
        """set which vertex attributes are enabled
        @note this only works reliably if this function is *always* used to manage vertex attribute state"""
        want = set(attrs)
        for a in (want - self.enabled_attribs):
            self.EnableVertexAttribArray(a)
        for a in (self.enabled_attribs - want):
            self.DisableVertexAttribArray(a)
        self.enabled_attribs = want

    def set_texture(self, target=TEXTURE_2D, tex=0, tmu=0):
        "combination of glActiveTexture() + glBindTexture()"
        self.ActiveTexture(self.TEXTURE0 + tmu)
        self.BindTexture(target, tex)

    def make_texture(self, target=TEXTURE_2D, wrap=CLAMP_TO_EDGE, filter=LINEAR_MIPMAP_NEAREST, min_filter=0, mag_filter=0):
        """create and configure a texture
        @note filter parameters can be specified either as a single 'filter' parameter,
              in which case the MIN_FILTER and MAG_FILTER parameters are derived from that,
              or separately as 'min_filter' and 'mag_filter' parameters
        """
        tex = self.GenTextures()
        if not min_filter:
            min_filter = filter
        if not mag_filter:
            mag_filter = filter if (filter < self.NEAREST_MIPMAP_NEAREST) \
                         else (self.NEAREST + (filter & 1))
        self.BindTexture(target, tex)
        self.TexParameteri(target, self.TEXTURE_WRAP_S, wrap)
        self.TexParameteri(target, self.TEXTURE_WRAP_T, wrap)
        self.TexParameteri(target, self.TEXTURE_MIN_FILTER, min_filter)
        self.TexParameteri(target, self.TEXTURE_MAG_FILTER, mag_filter)
        return tex

    def check_errors(self, context=None):
        "check for OpenGL errors and report them on the console"
        context = ("in " + context) if context else ""
        while True:
            err = self.GetError()
            if err: print(f"OpenGL error{context}: 0x{err:04X}")
            if not err: break

gl = _OpenGL()  # global OpenGL instance

###############################################################################

class GLShader:
    "convenience class wrapper for an OpenGL shader object"
    def __init__(self, shader_type, src):
        """compile a shader of a specified type (GL_VERTEX_SHADER / GL_FRAGMENT_SHADER)
        @note this provides the following member variables:
        - obj        = OpenGL shader object number
        - attributes = list of "attribute" or "in" variables, in order of appearance
        - uniforms   = set of uniform variables
        """
        self.obj = gl.CreateShader(shader_type)
        gl.ShaderSource(self.obj, src)
        gl.CompileShader(self.obj)
        if gl.GetShaderi(self.obj, gl.COMPILE_STATUS) != gl.TRUE:
            err = {
                gl.VERTEX_SHADER:   "vertex",
                gl.FRAGMENT_SHADER: "fragment",
            }.get(shader_type, f"type{shader_type:04X}") + " shader compilation failed"
            print("\x1b[41;97;1m\x1b[K" + err + "\x1b[0m")
            for i, line in enumerate(src.rstrip().split('\n')):
                print(f"\x1b[2m{i+1:4d} \x1b[0m" + line.rstrip())
            print("\x1b[91m" + gl.GetShaderInfoLog(self.obj).rstrip() + "\x1b[0m")
            self.delete()
            raise ValueError(err)
        self.attributes = [name for kw,name in re.findall(r'\b(attribute|in)\b.*?\s+(\w+)\s*;', src, flags=re.S)]
        self.uniforms = set(re.findall(r'\buniform\b.*?\s+(\w+)\s*;', src, flags=re.S))
    def delete(self):
        "delete this shader object"
        if self.obj:
            gl.DeleteShader(self.obj)
            self.obj = None
    def __bool__(self):
        "check for validity"
        return bool(self.obj)

class GLProgram:
    "convenience class wrapper for an OpenGL program object"
    def __init__(self, combined_or_vs_src:str, fs_src=None):
        """compile a program from vertex and fragment shader sources
        @note sources can be either provided as separate vertex and fragment
              shader sources, or as a single string using special markers
              to select which part is which shader, or which parts shall be
              present in both shaders; the markers are:
                [vs] [vert] [vertex] [fs] [frag] [fragment] [common]
              in addition, if the shader is #version 130 or higher, the keyword
              "varying" is replaced by "out" in the VS and "in" in the FS,
              and "attribute" is replaced by "in" in the VS
        @note this provides the following member variables:
        - obj  = OpenGL program object number
        - attributes = {name: location} mapping for all vertex attributes
                       (attributes will be bound to locations with ascending numbers
                       in order of appearance, starting with 0)
        - uniforms = set of uniform variables
        - for each uniform variable, a member variable is provided, containing its location
        @note this makes the newly creates program active immediately (with glUseProgram()) 
        """
        if fs_src:
            vs_src = combined_or_vs_src
        else:
            fs_src = ""
            vs_src = ""
            pos = 0
            mode = 'c'
            for m in re.finditer(r'\[(vs|vert|vertex|fs|frag|fragment|common)\]', combined_or_vs_src):
                text = combined_or_vs_src[pos:m.start()]
                white = ('\n' * text.count('\n')) or ' '
                comment = "/*" + m.group(1) + "*/"
                newmode = m.group(1)[0]
                vs_src += (white if (mode == 'f') else text) + ('' if (newmode == 'f') else comment)
                fs_src += (white if (mode == 'v') else text) + ('' if (newmode == 'v') else comment)
                mode = newmode
                pos = m.end()
            if mode != 'f': vs_src += combined_or_vs_src[pos:]
            if mode != 'v': fs_src += combined_or_vs_src[pos:]
            def postproc(src, *sar):
                src = '\n'.join(map(str.rstrip, src.rstrip().split('\n'))) + '\n'
                firstline = src.lstrip().split('\n', 1)[0].replace('\t', ' ')
                if firstline.startswith("#version ") and (firstline.split()[1] >= "130"):
                    for old, new in sar:
                        src = re.sub(r'\b' + old + r'\b', new, src)
                return src
            vs_src = postproc(vs_src, ("varying", "out"), ("attribute", "in"))
            fs_src = postproc(fs_src, ("varying", "in"))
        vs = GLShader(gl.VERTEX_SHADER, vs_src)
        fs = GLShader(gl.FRAGMENT_SHADER, fs_src)
        self.obj = gl.CreateProgram()
        gl.AttachShader(self.obj, vs.obj); vs.delete()
        gl.AttachShader(self.obj, fs.obj); fs.delete()
        self.uniforms = vs.uniforms | fs.uniforms
        self.attributes = {a:i for i,a in enumerate(vs.attributes)}
        for a,i in self.attributes.items():
            gl.BindAttribLocation(self.obj, i, a.encode())
        gl.LinkProgram(self.obj)
        if gl.GetProgrami(self.obj, gl.LINK_STATUS) != gl.TRUE:
            err = "shader program linking failed"
            print("\x1b[41;97;1m\x1b[K" + err + "\x1b[0m")
            print("\x1b[91m" + gl.GetProgramInfoLog(self.obj).rstrip() + "\x1b[0m")
            self.delete()
            raise ValueError(err)
        for u in self.uniforms:
            setattr(self, u, gl.GetUniformLocation(self.obj, u.encode()))
        self.use()
    def use(self):
        "make the program active"
        gl.UseProgram(self.obj)
    def delete(self):
        "delete this program object"
        if self.obj:
            gl.DeleteProgram(self.obj)
            self.obj = None
    def __bool__(self):
        "check for validity"
        return bool(self.obj)
