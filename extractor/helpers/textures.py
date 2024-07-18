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

# from dolphin

def make_RGBA(r: int, g: int, b: int, a: int):
    return (a << 24) | (b << 16) | (g << 8) | r

def DXTBlend(v1: int, v2: int):
    return ((v1 * 3 + v2 * 5) >> 3)