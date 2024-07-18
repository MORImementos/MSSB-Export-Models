from structs import DSTree, DSBranch, DBI


class ACTLayoutHeader(DBI):
    DATA_FORMAT = '>IHHxxxxxxxxIHxxII'

    def __init__(self, b:bytes, offset:int) -> None:
        self.versionNumber, \
        self.actorID, \
        self.numberOfBones, \
        self.GEOPaletteName, \
        self.skinFileID, \
        self.userDefinedDataSize, \
        self.offsetToUserDefinedData, \
        = self.parse_bytes(b, offset)
        assert self.versionNumber == 0x7B7960
        self.boneTree = DSTree(b, offset + 0x8)

    def add_offset(self, offset:int) -> None:
        if self.offsetToUserDefinedData != 0:
            self.offsetToUserDefinedData += offset
        if self.GEOPaletteName != 0:
            self.GEOPaletteName += offset
        self.boneTree.add_offset(offset)

    def __str__(self) -> str: 
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Actor ID: {hex(self.actorID)}\n"
        t += f"Bone Count: {self.numberOfBones}\n"
        t += f"GEO Palette Name Offset: {hex(self.GEOPaletteName)}\n"
        t += f"Skin File ID: {self.skinFileID}\n"
        t += f"User Defined Data Offset: {self.offsetToUserDefinedData}\n"
        t += f"User Defined Data Size: {self.userDefinedDataSize}"
        return t

