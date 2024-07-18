from structs import DBI, DSBranch, CTRL

class ACTBoneLayoutHeader(DBI):
    DATA_FORMAT = ''.join(''' \
    >I
    xxxx
    xxxx
    xxxx
    xxxx
    HHBBxx
    '''.split())

    def __init__(self, b:bytes, offset:int) -> None:
        # Defer import to avoid circular dependency <- not needed if i change import order but will leave it just in case
        # from structs import CTRL

        self.offsetToCTRLControl, \
        self.GEOFileID, \
        self.boneID, \
        self.inheritanceFlag, \
        self.drawingPriority \
        = self.parse_bytes(b, offset)
        self.branch = DSBranch(b, offset + 0x4)
        self.previousBone:ACTBoneLayoutHeader = None
        self.nextBone:ACTBoneLayoutHeader = None
        self.parentBone:ACTBoneLayoutHeader = None
        self.firstChildBone:ACTBoneLayoutHeader = None
        self.CTRL:CTRL.CTRLControl = None
    
    def add_offset(self, offset:int) -> None:
        if self.offsetToCTRLControl:
            self.offsetToCTRLControl += offset
        self.branch.add_offset(offset)

    def __str__(self) -> str:
        t = ''
        t += f"=={self.__class__.__name__}==\n"
        t += f'GEO ID: {self.GEOFileID}\n'
        t += f'Bone ID: {self.boneID}\n'
        if self.CTRL:
            t += f'Orientation:\n{self.CTRL}'
        return t