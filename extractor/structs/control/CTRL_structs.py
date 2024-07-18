from structs import DBI
from struct import pack
from helpers.to_sort import warn
from helpers.rotation import quaternion_to_euler, sqtTransform
from structs import Vector3, Vector4


# TODO: Add support for CTRLMTXControl types
class CTRLControl(DBI):
    DATA_FORMAT = '>Bxxx'

    CTRL_NONE =      0
    CTRL_SCALE =     0b1
    CTRL_ROT_EULER = 0b10
    CTRL_ROT_QUAT =  0b100
    CTRL_ROT_TRANS = 0b1000
    CTRL_MTX =       0b10000

    def __init__(self, b:bytes, offset:int) -> None:
        self.MTX:CTRLMTXControl = None
        self.SRT:CTRLSRTControl = None
        self.type \
        = self.parse_bytes(b, offset)[0]
        if self.type & CTRLControl.CTRL_ROT_EULER or self.type & CTRLControl.CTRL_MTX:
            warn(f'Encountered unsupported CTRLControl type {self.type}')
            assert False
        elif self.type == 0:
            # Either this is the identity matrix or this bone has no control pointer
            # Feeding in the identity matrix is probably fine
            self.SRT = CTRLSRTControl(pack('>ffffffffff', 1, 1, 1, 0, 0, 0, 1, 0, 0, 0), 0)
        else:
            self.SRT = CTRLSRTControl(b, offset + 0x4)

    def __str__(self) -> str:
        if self.SRT:
            return str(self.SRT)
        elif self.MTX:
            return str(self.MTX)
        else:
            return ''

class CTRLSRTControl(DBI):
    DATA_FORMAT = '>ffffffffff'

    def __init__(self, b:bytes, offset:int, usesEulerRotation:bool = False):
        self.usesEulerRotation = usesEulerRotation
        self.scale:Vector3 = [1, 1, 1]
        self.eulerRotation:Vector3 = [0, 0, 0] if usesEulerRotation else None
        # X,Y,Z,W format
        self.quaternionRotation:Vector4 = [0, 0, 0, 1] if not usesEulerRotation else None
        self.translation:Vector3 = [0, 0, 0]
        if usesEulerRotation:
            floats = self.parse_bytes(b, offset)
            self.scale[:3] = floats[:3]
            self.eulerRotation[:3] = floats[3:6]
            self.quaternionRotation = None
            self.translation[:3] = floats[7:10]
        else:
            floats = self.parse_bytes(b, offset)
            self.scale[:3] = floats[:3]
            self.eulerRotation = None
            self.quaternionRotation[:4] = floats[3:7]
            self.translation[:3] = floats[7:10]
            # Not confident on this, but I had to do this in Mario Super Sluggers
            self.quaternionRotation[3] *= -1

    def getScale(self) -> Vector3:
        return self.scale

    def getEulerRotation(self) -> Vector3:
        if self.usesEulerRotation:
            return self.eulerRotation
        else:
            return Vector3(*quaternion_to_euler(self.quaternionRotation[3], *self.quaternionRotation[:3]))

    def getQuaternionRotation(self) -> Vector3:
        if self.usesEulerRotation:
            # Not going to add euler -> quaternion unless it ends up being necessary
            assert False
        else:
            return self.quaternionRotation

    def getTranslation(self) -> Vector3:
        return self.translation
    
    def getTransform(self) -> list[list[float]]:
        if self.usesEulerRotation:
            warn ("Euler rotations not supported")
            assert (0)
        return sqtTransform(self.getScale(), self.getQuaternionRotation(), self.getTranslation())

    def __str__(self) -> str:
        t = ''
        t += f'Scale: {self.getScale()}\n'
        t += f'Rotation (Euler): {self.getEulerRotation()}\n'
        t += f'Translation: {self.getTranslation()}'
        return t

# TODO
class CTRLMTXControl(DBI):
    pass