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