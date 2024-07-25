from __future__ import annotations
from dataclasses import dataclass
from PIL.Image import Image, new as new_Image
from os.path import join
from helper_mssb_data import *
import struct

CMPR_BLOCK_SIZE = 8

VALID_IMAGE_FORMATS = {
    0: "I4",
    1: "I8",
    2: "IA4",
    3: "IA8",
    4: "RGB565",
    5: "RGB5A3",
    6: "RGBA32",
    8: "C4",
    9: "C8",
    0xa: "C14X2",
    0xe: "CMPR"
}

REV_VALID_IMAGE_FORMATS = {v: k for k, v in VALID_IMAGE_FORMATS.items()}

@dataclass
class ExtractedTexture:
    img:Image
    img_format:str

class ExtractedTextureCollection:
    def __init__(self, images : list[ExtractedTexture]) -> None:
        self.images = images

    def generate_outputs(self, path:str=None) -> list[tuple[str, ExtractedTexture]]:
        outputs = []
        for index, tex in enumerate(self.images):
            file_name = f"{index}.png"
            if path != None:
                file_name = join(path, file_name)
            outputs.append((file_name, tex))
        return outputs

    def write_images_to_folder(self, path:str = None):
        for file_name, tex in self.generate_outputs(path):
            ensure_dir(dirname(file_name))
            tex.img.save(file_name)

    def write_mtl_file(self, output_path:str, img_file_path:str):
        mtl_contents = self.get_mtl_file(img_file_path)
        write_text(mtl_contents, output_path)

    def get_mtl_file(self, img_files_path:str = None):
        output = ""
        for i, (path, tex) in enumerate(self.generate_outputs(img_files_path)):
            path:str

            path = path.replace("\\", "\\\\")

            output += (f"newmtl mssbMtl.{i}\n")
            output += (f"map_Kd {path}\n")
            output += (f"# Height: {tex.img.height}, Width: {tex.img.width}, Format: {tex.img_format}\n")
            output += ("\n")
    
        return output

@dataclass
class TPLTextureHeader(DataBytesInterpreter):
    address:int
    height:int
    width:int
    format:int
    palette:int
    palette_format:int
    DATA_FORMAT:str = '>IIHHxxxxxxxxxxxBxxBxxxxx'

    def __str__(self) -> str:
        t = ""
        format = VALID_IMAGE_FORMATS.get(self.format, hex(self.format))
        t += f"format: {format}\n"
        t += f"width: {self.width}\n"  
        t += f"height: {self.height}"
        return t

    def is_valid(self):
        return (
            self.format in VALID_IMAGE_FORMATS and 
            self.width % 4 == 0 and 
            self.height % 4 == 0 and 
            self.height > 0 and
            self.width > 0)

    def from_bytes(b:bytes, offset:int) -> TPLTextureHeader:

        this_address, \
        this_palette, \
        this_height, \
        this_width, \
        this_format, \
        this_palette_format, \
        = TPLTextureHeader.parse_bytes_static(b, offset, TPLTextureHeader.DATA_FORMAT)

        return TPLTextureHeader(
            address=this_address,
            palette=this_palette,
            height=this_height,
            width=this_width,
            format=this_format,
            palette_format=this_palette_format
        )

class TPLColor:
    @classmethod
    def from_bytes(cls, b:bytes):
        cls.from_int(int.from_bytes(b, 'big'))
        return cls

    @classmethod
    def to_bytes(cls) -> bytes:
        return cls.to_int().to_bytes(length=cls.SIZE, byteorder='big')
    
    @classmethod
    def has_alpha(cls) -> bool:
        return len(cls.data) == 4

class TPLColorIA8(TPLColor):
    SIZE = 1

    @classmethod
    def from_int(cls, i: int):
        a = i & 0xFF
        i = i >> 8
        # return i | (i << 8) | (i << 16) | (a << 24);
        
        cls.data = (i, i, i, a)
        
        return cls
    
    @classmethod
    def to_int(cls) -> int:
        return (cls.data[3] << 8) | (cls.data[0])

class TPLColorR5G6B5(TPLColor):
    SIZE = 2

    @classmethod
    def from_int(cls, i:int):
        cls.data = ((i >> 11) << 3, ((i >> 5) & 0b111111) << 2, (i & 0b11111) << 3)
        return cls
    
    @classmethod
    def to_int(cls) -> int:
        return ((cls.data[0] >> 3) << 11) | ((cls.data[1] >> 2) << 5) | (cls.data[2] >> 3)

class TPLColorRGB5A3(TPLColor):
    SIZE = 2
    
    @classmethod
    def from_int(cls, a:int):
        if a & 0x8000 != 0: # default 255 alpha
            cls.data = (((a >> 10) & 0b11111) << 3, ((a >> 5) & 0b11111) << 3, (a & 0b11111) << 3, 0xff)
        else: # has alpha bits
            cls.data = ((a >> 8) & 0b1111) << 4, ((a >> 4) & 0b1111) << 4, (a & 0b1111) << 4, (((a >> 12) & 0b1111) << 5)
        return cls

    @classmethod
    def to_int(cls) -> int:
        if cls.data[3] == 255:
            return 0x8000 | cls.data[0] << 7 | cls.data[1] << 2 | cls.data[2] >> 3
        else:
            return cls.data[0] << 4 | cls.data[1] | cls.data[2] >> 4 | cls.data[3] << 7


# works as far as extracting image, doesn't seem to work converting color palette yet
class TPLFileI4:
    @staticmethod
    def get_pixel(src:bytes, s:int, t:int, width:int, palette):
        sBlock = s >> 3
        tBlock = t >> 3
        widthBlocks = (width + 7) // 8
        base = (tBlock * widthBlocks + sBlock) << 5
        blockS = s & 7
        blockT = t & 7
        blockOff = (blockT << 3) + blockS

        offset = base + (blockOff >> 1)
        if blockOff & 1:
            val = src[offset] & 0x0f
        else:
            val = (src[offset] >> 4) & 0x0f

        # v = expand_to_8_bits(val, 4)
        intensity = expand_to_8_bits(val, 4)
        return (intensity, intensity, intensity, 0xFF)
    
    @staticmethod
    def parse_source(source:bytes, header: TPLTextureHeader) -> Image.Image:
        width, height = (header.width, header.height)
        image_data = source[header.address:]

        palette_data = source[header.palette:][:0x200]
        palette = [int.from_bytes(palette_data[i * 2:i * 2 + 2], 'big') for i in range(0x100)]

        # if header.palette_format == 0: # RGB565
        #     func = TPLColorR5G6B5
        #     pixel_format = "RGBA"
        # elif header.palette_format == 1: # IA8
        #     func = TPLColorIA8
        #     pixel_format = "RGB"
        # elif header.palette_format == 2: # RGB5A3
        
        func = TPLColorRGB5A3
        pixel_format = "RGBA"
        # else:
        #     assert(False)

        palette = [func.from_int(x).data for x in palette]

        image = new_Image(pixel_format, (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileI4.get_pixel(image_data, s, t, width, palette)
                image.putpixel((s,t), p)
        
        return image


# haven't found one that uses it yet, so not sure if it works
class TPLFileI8:
    @staticmethod
    def get_pixel(src:bytes, s:int, t:int, width:int, palette):
        offset = t * width + s
        val = src[offset]

        color = (val, val, val, 0xFF) if not palette else palette[val]

        return color
    
    @staticmethod
    def parse_source(source:bytes, header: TPLTextureHeader) -> Image.Image:
        width, height = header.width, header.height
        image_data = source[header.address:header.address + width * height]     
        
        if header.palette:
            palette_data = source[header.palette:header.palette + 0x200]
            palette = [int.from_bytes(palette_data[i * 2:i * 2 + 2], 'big') for i in range(0x100)]
            func = TPLColorRGB5A3
            palette = [func.from_int(x).data for x in palette]
        else:
            palette = None

        pixel_format = "RGBA"
        image = Image.new(pixel_format, (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileI8.get_pixel(image_data, s, t, width, palette)
                image.putpixel((s, t), p)
        
        return image  
# haven't found one that uses it yet, so not sure if it works

class TPLFileIA4:
    @staticmethod
    def get_pixel(src: bytes, s: int, t: int, width: int):
        sBlock = s >> 3
        tBlock = t >> 2
        widthBlocks = (width + 7) / 8
        base = (tBlock * widthBlocks + sBlock) << 5
        blockS = s & 7
        blockT = t & 3
        blockOff = (blockT << 3) + blockS

        offset = base + blockOff
        val = src[offset]

        intensity = expand_to_8_bits(val & 0x0f, 4)
        alpha = expand_to_8_bits(val >> 4, 4)

        return (intensity, intensity, intensity, alpha)
    
    @staticmethod
    def parse_source(source: bytes, header: 'TPLTextureHeader') -> Image.Image:
        width, height = header.width, header.height
        image_data = source[header.address:header.address + (width * height)]

        image = Image.new("RGBA", (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileIA4.get_pixel(image_data, s, t, width)
                image.putpixel((s, t), p)
        
        return image

# haven't found one that uses it yet, so not sure if it works
class TPLFileIA8:
    @staticmethod
    def get_pixel(src: bytes, s: int, t: int, width: int):
        offset = (t * width + s) * 2
        texel = struct.unpack('>H', src[offset:offset+2])[0]
        intensity = texel >> 8
        alpha = texel & 0xFF

        return (intensity, intensity, intensity, alpha)
    
    @staticmethod
    def parse_source(source: bytes, header: 'TPLTextureHeader') -> Image.Image:
        width, height = header.width, header.height
        image_data = source[header.address:header.address + (width * height * 2)]

        image = Image.new("RGBA", (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileIA8.get_pixel(image_data, s, t, width)
                image.putpixel((s, t), p)
        
        return image

class TPLFileRGB565:
    pass

class TPLFileRGB5A3:
    pass

class TPLFileRGBA32:
    pass

class TPLFileC4:
    @staticmethod
    def get_pixel(src:bytes, s:int, t:int, width:int, palette):
        sBlk = s >> 3
        tBlk = t >> 3
        widthBlks = (width >> 3)
        base = (tBlk * widthBlks + sBlk) << 5
        blkS = s & 7
        blkT = t & 7
        blkOff = (blkT << 3) + blkS

        rs = 0 if (blkOff & 1) else 4
        offset = base + (blkOff >> 1)

        val = ((src[offset]) >> rs) & 0xF
        return palette[val]
    
    @staticmethod
    def parse_source(source:bytes, header: TPLTextureHeader) -> Image.Image:
        width, height = (header.width, header.height)
        blocks_to_read = (width//4) * (height//4) * 8
        image_data = source[header.address:][:blocks_to_read]

        byt = source[header.palette:][:0x20]
        palette = [int.from_bytes(byt[i*2:i*2+2], 'big') for i in range(0x10)]

        if header.palette_format == 0:
            func = TPLColorIA8
            pixel_format = "RGBA"
        elif header.palette_format == 1:
            func = TPLColorR5G6B5
            pixel_format = "RGB"
        elif header.palette_format == 2:
            func = TPLColorRGB5A3
            pixel_format = "RGBA"
        else:
            assert(False)

        # print(', '.join(hex(x) for x in palette))
        palette = [func.from_int(x).data for x in palette]
        # print(', '.join(['(' + ','.join(str(y) for y in x) + ')' for x in palette]))

        image = new_Image(pixel_format, (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileC4.get_pixel(image_data, s, t, width, palette)
                image.putpixel((s,t), p)
        
        return image

class TPLFileC8:
    @staticmethod
    def get_pixel(src:bytes, s:int, t:int, width:int, palette):
        sBlk = s >> 3
        tBlk = t >> 2
        widthBlks = (width >> 3)
        base = (tBlk * widthBlks + sBlk) << 5
        blkS = s & 7
        blkT = t & 3
        blkOff = (blkT << 3) + blkS

        val = src[base+blkOff]

        return palette[val]
    
    @staticmethod
    def parse_source(source:bytes, header: TPLTextureHeader) -> Image.Image:
        width, height = (header.width, header.height)
        # blocks_to_read = (width//4) * (height//4) * 8
        image_data = source[header.address:]

        byt = source[header.palette:][:0x200]
        palette = [int.from_bytes(byt[i*2:i*2+2], 'big') for i in range(0x100)]

        # if header.palette_format == 0: # RGB565
        #     func = TPLColorR5G6B5
        #     pixel_format = "RGBA"
        # elif header.palette_format == 1: # IA8
        #     func = TPLColorIA8
        #     pixel_format = "RGB"
        # elif header.palette_format == 2: # RGB5A3
        func = TPLColorRGB5A3
        pixel_format = "RGBA"
        # else:
        #     assert(False)

        palette = [func.from_int(x).data for x in palette]

        image = new_Image(pixel_format, (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileC8.get_pixel(image_data, s, t, width, palette)
                image.putpixel((s,t), p)
        
        return image

class TPLFileC14X2:
    pass

class TPLFileCMPR:
    @staticmethod
    def dxt_blend(v1, v2):
        return ((v1 * 3 + v2 * 5) >> 3)

    @staticmethod
    def parse_source(source:bytes, header: TPLTextureHeader) -> Image.Image:
        width, height = (header.width, header.height)
        blocks_to_read = (width//4) * (height//4) * 8

        image_data = source[header.address:][:blocks_to_read]
        image = new_Image("RGBA", (width, height))

        for t in range(height):
            for s in range(width):
                p = TPLFileCMPR.get_pixel(image_data, s, t, width)
                image.putpixel((s,t), p)
        return image


    @staticmethod
    def get_pixel(src:bytes, s:int, t:int, width:int):
        sDxt = s >> 2
        tDxt = t >> 2
        
        sBlock = sDxt >> 1
        tBlock = tDxt >> 1
        width_blocks = (width >> 3)
        base = (tBlock * width_blocks + sBlock) << 2
        blockS = sDxt & 1
        blockT = tDxt & 1
        block_offset = (blockT << 1) + blockS
        
        offset = (base + block_offset) << 3

        dxt_block = src[offset:offset+8]

        c1 = TPLColorR5G6B5().from_bytes(dxt_block[0:2]).data
        c2 = TPLColorR5G6B5().from_bytes(dxt_block[2:4]).data

        ss = s & 3
        tt = t & 3

        color_select = dxt_block[4:][tt]
        rs = 6 - (ss << 1)

        color_select = (color_select >> rs) & 3

        color_select |= 0 if c1 > c2 else 4

        if color_select in [0,4]:
            return (c1[0], c1[1], c1[2], 255)
        elif color_select in [1,5]:
            return (c2[0], c2[1], c2[2], 255)
        elif color_select in [2]:
            return (TPLFileCMPR.dxt_blend(c2[0], c1[0]), TPLFileCMPR.dxt_blend(c2[1], c1[1]), TPLFileCMPR.dxt_blend(c2[2], c1[2]), 255)
        elif color_select in [3]:
            return (TPLFileCMPR.dxt_blend(c1[0], c2[0]), TPLFileCMPR.dxt_blend(c1[1], c2[1]), TPLFileCMPR.dxt_blend(c1[2], c2[2]), 255)
        elif color_select in [6]:
            return ((c1[0] + c2[0]) // 2, (c1[1] + c2[1]) // 2, (c1[2] + c2[2]) // 2, 255)
        elif color_select in [7]:
            return ((c1[0] + c2[0]) // 2, (c1[1] + c2[1]) // 2, (c1[2] + c2[2]) // 2, 0)
        else:
            return (0,0,0,0)

# Helper functions implemented from https://github.com/encounter/aurora/blob/main/lib/gfx/texture_convert.cpp

def expand_to_8_bits(val: int, num_bits: int) -> int:
    if num_bits == 4:
        return (val << 4) | val
    if num_bits == 3:
        return (val << 5) | (val << 2) | (val >> 1)
    else:
        return (val << (8 - num_bits)) | (val >> ((num_bits * 2) - 8))

    
def S3TCBlend(a: int, b: int):
    return ((((a << 1) + a) + ((b << 2) + b)) >> 3)

def halfBlend(a: int, b: int):
    return (a + b) >> 1

def computeMippedTexelCount(width: int, height: int, mips: int):
    ret = width * height
    for _ in range(mips - 1):
        if width > 1:
            width //= 2
        if height > 1:
            height //= 2
        ret += width * height
    return ret

def computeMippedBlockCountDXT1(width: int, height: int, mips: int):
    width //= 4
    height //= 4
    ret = width * height
    for _ in range(mips - 1):
        if width > 1:
            width //= 2
        if height > 1:
            height //= 2
        ret += width * height
    return ret

def bswap16(val: int) -> int:
    # swap endianness
    return ((val & 0xFF) << 8) | ((val >> 8) & 0xFF)

    
@dataclass
class RGBA8:
    # each is uint8_t
    r: int
    g: int
    b: int
    a: int

class DXT1Block:
    color1: int # u16
    color2: int # u16
    lines: list # u8[4]


def dummyImage():
    return new_Image('1', (1, 1))

# from dolphin

def make_RGBA(r: int, g: int, b: int, a: int):
    return (a << 24) | (b << 16) | (g << 8) | r

def DXTBlend(v1: int, v2: int):
    return ((v1 * 3 + v2 * 5) >> 3)