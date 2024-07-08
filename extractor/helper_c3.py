from __future__ import annotations
from helper_vector import *
from helper_rotation import *
from helper_string import warn
from struct import pack

from helper_mssb_data import DataBytesInterpreter

class SECTION_TYPES():
    ACT = 0
    GEO = 1
    texture = 2
    collision = 3
    type_count = 4

SECTION_TEMPLATES:dict[str, dict[int, int]] = {
    'Stadium': {
        'stadium': {
            SECTION_TYPES.ACT: 0,
            SECTION_TYPES.GEO: 3,
            SECTION_TYPES.texture: 5,
            SECTION_TYPES.collision: 2
        },
        'backdrop': {
            SECTION_TYPES.ACT: 1,
            SECTION_TYPES.GEO: 4
        }
    }
}

class GeoPaletteHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IIIII'

    def __init__(self, b:bytes, offset:int) -> None:
        
        self.versionNumber, \
        self.userDefinedDataSize, \
        self.offsetToUserDefinedData, \
        self.numberOfGeometryDescriptors, \
        self.offsetToGeometryDescriptorArray, \
        = self.parse_bytes(b, offset)

    def add_offset(self, offset:int):
        if self.offsetToGeometryDescriptorArray != 0 :
            self.offsetToGeometryDescriptorArray += offset

        if self.offsetToUserDefinedData != 0:
            self.offsetToUserDefinedData += offset

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Version Number: {self.versionNumber}\n"
        t += f"User Defined Data Size: {self.userDefinedDataSize}\n"
        t += f"pDefined Data: {hex(self.offsetToUserDefinedData)}\n"
        t += f"Number Of Geometry Descriptors: {self.numberOfGeometryDescriptors}\n"
        t += f"pGeometry Descriptor Array: {hex(self.offsetToGeometryDescriptorArray)}"

        return t

class GeoDescriptor(DataBytesInterpreter):
    DATA_FORMAT = '>II'

    def __init__(self, b:bytes, offset:int) -> None:

        self.offsetToDisplayObject, \
        self.offsetToName, \
        = self.parse_bytes(b, offset)

        self.name = None

    def add_offset(self, offset:int):
        if self.offsetToDisplayObject != 0:
            self.offsetToDisplayObject += offset
    
        if self.offsetToName != 0:
            self.offsetToName += offset
    
    def set_name(self, name:str):
        self.name = name
    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Name: {self.name}\n"
        t += f"pDisplay Object: {hex(self.offsetToDisplayObject)}\n"
        t += f"pName: {hex(self.offsetToName)}"
        
        return t

class DisplayObjectLayout(DataBytesInterpreter):
    DATA_FORMAT = '>IIIIIBxxx'

    def __init__(self, b:bytes, offset:int) -> None:

        self.OffsetToPositionData, \
        self.OffsetToColorData, \
        self.OffsetToTextureData, \
        self.OffsetToLightingData, \
        self.OffsetToDisplayData, \
        self.numberOfTextures, \
        = self.parse_bytes(b, offset)
        
    def add_offset(self, offset:int) -> None:
        if self.OffsetToPositionData != 0:
            self.OffsetToPositionData += offset

        if self.OffsetToColorData != 0:
            self.OffsetToColorData += offset
        
        if self.OffsetToTextureData != 0:
            self.OffsetToTextureData += offset

        if self.OffsetToLightingData != 0:
            self.OffsetToLightingData += offset

        if self.OffsetToDisplayData != 0:
            self.OffsetToDisplayData += offset
    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"pPosition Data: {hex(self.OffsetToPositionData)}\n"
        t += f"pColor Data: {hex(self.OffsetToColorData)}\n"
        t += f"pTexture Data: {hex(self.OffsetToTextureData)}\n"
        t += f"pLighting Data: {hex(self.OffsetToLightingData)}\n"
        t += f"pDisplay Data: {hex(self.OffsetToDisplayData)}"
        return t

class DisplayObjectPositionHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IHBB'

    QUANTIZE_INFO={
        "size info":{
            0x0:2, # presumably unshifted
            0x1:4, # float
            0x2:2, # u16
            0x3:2, # s16
            0x4:1, # u8
            0x5:1 # s8
        },
        "signed info":{
            0x0:False,
            0x1:True,
            0x2:False,
            0x3:True,
            0x4:False,
            0x5:True
        }
    }

    def __init__(self, b:bytes, offset) -> None:

        self.offsetToPositionArray, \
        self.numberOfPositions, \
        self.quantizeInfo, \
        self.numberOfComponents, \
        = self.parse_bytes(b, offset)
        
        self.format = self.quantizeInfo >> 4
        self.componentSize = self.QUANTIZE_INFO["size info"][self.format]
        self.componentShift = self.quantizeInfo & 0xf
        self.componentSigned = self.QUANTIZE_INFO["signed info"][self.format]


    def add_offset(self, offset:int)->None:
        if self.offsetToPositionArray != 0:
            self.offsetToPositionArray += offset
    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"pPositions: {hex(self.offsetToPositionArray)}\n"
        t += f"Position Count: {hex(self.numberOfPositions)}\n"
        t += f"Quantize Info: {hex(self.quantizeInfo)}\n"
        t += f"Component Count: {self.numberOfComponents}"

        return t


class DisplayObjectColorHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IHBB'

    QUANTIZE_INFO = {
        0x0:2,
        0x1:3,
        0x2:4,
        0x3:2,
        0x4:3,
        0x5:4,
    }

    def __init__(self, b:bytes, offset:int) -> None:

        self.offsetToColorArray, \
        self.numberOfColors, \
        self.quantizeInfo, \
        self.numberOfComponents, \
        = self.parse_bytes(b, offset)
        
        self.format = self.quantizeInfo >> 4
        self.alpha = self.format > 2
        self.componentSize = self.QUANTIZE_INFO[self.format]

    def add_offset(self, offset:int)->None:
        if self.offsetToColorArray != 0:
            self.offsetToColorArray += offset

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"pColors: {hex(self.offsetToColorArray)}\n"
        t += f"Color Count: {self.numberOfColors}\n"
        t += f"Format Info: {hex(self.quantizeInfo)}\n"
        t += f"Component Count: {self.numberOfComponents}"

        return t

class DisplayObjectTextureHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IHBBII'

    QUANTIZE_INFO={
        "size info":{
            0x0:2, # presumably unshifted
            0x1:4, # float
            0x2:2, # u16
            0x3:2, # s16
            0x4:1, # u8
            0x5:1 # s8
        },
        "signed info":{
            0x0:False,
            0x1:True,
            0x2:False,
            0x3:True,
            0x4:False,
            0x5:True
        }
    }

    def __init__(self, b:bytes, offset:int) -> None:

        self.offsetToTextureCoordinateArray, \
        self.numberOfCoordinates, \
        self.quantizeInfo, \
        self.numberOfComponents, \
        self.offsetToTexturePaletteFileName, \
        self.offsetToPalettePointer, \
        = self.parse_bytes(b, offset)
        
        self.format = self.quantizeInfo >> 4
        self.componentSize = self.QUANTIZE_INFO["size info"][self.format]
        self.componentShift = self.quantizeInfo & 0xf
        self.componentSigned = self.QUANTIZE_INFO["signed info"][self.format]

        self.name = None

    def add_offset(self, offset:int)->None:
        if self.offsetToTextureCoordinateArray != 0:
            self.offsetToTextureCoordinateArray += offset
        
        if self.offsetToTexturePaletteFileName != 0:
            self.offsetToTexturePaletteFileName += offset
        
        if self.offsetToPalettePointer != 0:
            self.offsetToPalettePointer += offset

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Name: {self.name}\n"
        t += f"pName: {hex(self.offsetToTexturePaletteFileName)}\n"
        t += f"pTexture Coords: {hex(self.offsetToTextureCoordinateArray)}\n"
        t += f"Coord Count: {self.numberOfCoordinates}\n"
        t += f"Format Info: {hex(self.quantizeInfo)}\n"
        t += f"Component Count: {self.numberOfComponents}"

        return t

class DisplayObjectDisplayHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IIHxx'

    def __init__(self, b:bytes, offset:int) -> None:

        self.offsetToPrimitiveBank, \
        self.offsetToDisplayStateList, \
        self.numberOfDisplayStateEntries, \
        = self.parse_bytes(b, offset)
    
    def add_offset(self, offset:int)->None:
        if self.offsetToPrimitiveBank != 0:
            self.offsetToPrimitiveBank += offset
        
        if self.offsetToDisplayStateList != 0:
            self.offsetToDisplayStateList += offset
    
    def __str__(self) -> str: 
        t= ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"pPrimitive Bank: {hex(self.offsetToPrimitiveBank)}\n"
        t += f"pDisplay States: {hex(self.offsetToDisplayStateList)}\n"
        t += f"Display State Count: {self.numberOfDisplayStateEntries}"
        return t


class DisplayObjectLightingHeader(DataBytesInterpreter):
    DATA_FORMAT = '>IHBBf'

    QUANTIZE_INFO={
        "size info":{
            0x0:2, # presumably unshifted
            0x1:4, # float
            0x2:2, # u16
            0x3:2, # s16
            0x4:1, # u8
            0x5:1 # s8
        },
        "signed info":{
            0x0:False,
            0x1:True,
            0x2:False,
            0x3:True,
            0x4:False,
            0x5:True
        }
    }

    def __init__(self, b:bytes, offset:int) -> None:

        self.offsetToNormalArray, \
        self.numberOfNormals, \
        self.quantizeInfo, \
        self.numberOfComponents, \
        self.ambientBrightness, \
        = self.parse_bytes(b, offset)
        
        self.format = self.quantizeInfo >> 4
        self.componentSize = self.QUANTIZE_INFO["size info"][self.format]
        self.componentShift = self.quantizeInfo & 0xf
        self.componentSigned = self.QUANTIZE_INFO["signed info"][self.format]


    def add_offset(self, offset:int)->None:
        if self.offsetToNormalArray != 0:
            self.offsetToNormalArray += offset

    def __str__(self) -> str: 
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"pNormals: {hex(self.offsetToNormalArray)}\n"
        t += f"Normal Count: {self.numberOfNormals}\n"
        t += f"Format Info: {hex(self.quantizeInfo)}\n"
        t += f"Component Count: {self.numberOfComponents}\n"
        t += f"Ambient Brightness: {self.ambientBrightness}"
        return t


class DisplayObjectDisplayState(DataBytesInterpreter):
    DATA_FORMAT = '>BxxxIII'
    
    def __init__(self, b:bytes, offset:int) -> None:

        self.stateID, \
        self.setting, \
        self.offsetToPrimitiveList, \
        self.byteLengthPrimitiveList, \
        = self.parse_bytes(b, offset)
    
    def add_offset(self, offset:int)->None:
        if self.offsetToPrimitiveList != 0:
            self.offsetToPrimitiveList += offset
    
    def __str__(self) -> str: 
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"State ID: {self.stateID}\n"
        t += f"Setting: {hex(self.setting)}\n"
        t += f"pPrimitive List: {hex(self.offsetToPrimitiveList)}\n"
        t += f"Primitive Byte Count: {self.byteLengthPrimitiveList}"
        
        return t

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

class ACTLayoutHeader(DataBytesInterpreter):
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

class ACTBoneLayoutHeader(DataBytesInterpreter):
    DATA_FORMAT = ''.join(''' \
    >I
    xxxx
    xxxx
    xxxx
    xxxx
    HHBBxx
    '''.split())

    def __init__(self, b:bytes, offset:int) -> None:
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
        self.CTRL:CTRLControl = None
    
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

# TODO: Add support for CTRLMTXControl types
class CTRLControl(DataBytesInterpreter):
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

class CTRLSRTControl(DataBytesInterpreter):
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
class CTRLMTXControl(DataBytesInterpreter):
    pass

def copyAttributesToDict(obj, dict, attrs):
    for attr in attrs:
        dict[attr] = getattr(obj, attr)