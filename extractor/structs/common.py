from struct import calcsize
from struct import unpack

class DataBytesInterpreter:
    @classmethod
    @property
    def SIZE_OF_STRUCT(cls):
        return calcsize(cls.DATA_FORMAT)

    @classmethod
    def parse_bytes_static(cls, all_bytes:bytearray, offset:int, format_str:str):
        struct_size = calcsize(format_str)
        these_bytes = all_bytes[offset:offset+struct_size]

        if len(these_bytes) != struct_size:
            raise ValueError(f'Ran out of bytes to interpret in {cls.__name__}, needed {cls.SIZE_OF_STRUCT}, received {len(these_bytes)}')

        return unpack(format_str, these_bytes)

    def parse_bytes(self, all_bytes:bytearray, offset:int):
        return self.parse_bytes_static(all_bytes, offset, self.DATA_FORMAT)

class Vec(DataBytesInterpreter):

    DATA_FORMAT = ">fff"

    def __init__(self, b: bytes, offset: int) -> None:
        self.x, self.y, self.z = self.parse_bytes(b, offset)

    def __repr__(self) -> str:
        return f"\n    x: {self.x}\n    y: {self.y}\n    z: {self.z}\n"
    
    def to_dict(self):
        return {"X": self.x, "Y": self.y, "Z": self.z}
    
class DSTree(DataBytesInterpreter):
    DATA_FORMAT = '>xxxxI'

    def __init__(self, b:bytes, offset:int) -> None:
        self.offsetToRoot \
        = self.parse_bytes(b, offset)[0]
    
    def add_offset(self, offset:int) -> None:
        if self.offsetToRoot != 0:
            self.offsetToRoot += offset

    def __str__(self) -> str:
        return ''

class DSBranch(DataBytesInterpreter):
    DATA_FORMAT = '>IIII'

    def __init__(self, b:bytes, offset:int) -> None:
        self.offsetToPreviousBranch, \
        self.offsetToNextBranch, \
        self.offsetToParentBranch, \
        self.offsetToFirstChildBranch \
        = self.parse_bytes(b, offset)
    
    def add_offset(self, offset:int) -> None:
        if self.offsetToPreviousBranch:
            self.offsetToPreviousBranch += offset
        if self.offsetToNextBranch:
            self.offsetToNextBranch += offset
        if self.offsetToParentBranch:
            self.offsetToParentBranch += offset
        if self.offsetToFirstChildBranch:
            self.offsetToFirstChildBranch += offset

    def __str__(self) -> str:
        return ''
