from __future__ import annotations
from helper_vector import *
from helper_rotation import *
from helper_string import warn
from struct import pack, unpack

from helper_mssb_data import DataBytesInterpreter
def open_binary_get_bytes(file):
    with open(file, "rb") as f:
        return f.read()
    


def log_to_file(log_file, message):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

class ANIMBank(DataBytesInterpreter):
    DATA_FORMAT = ">I I H H H H I I"

    def __init__(self, b: bytes, offset: int) -> None:
        self.versionNumber, \
        self.offsetToSequenceArray, \
        self.bankID, \
        self.numberOfSequences, \
        self.numberOfTracks, \
        self.numberOfKeyframes, \
        self.userDefinedDataSize, \
        self.offsetToUserData \
        = self.parse_bytes(b, offset)
        
        self.add_offset(offset)
        self.sequences = [ANIMSequence(b, self.offsetToSequenceArray + i * ANIMSequence.SIZE_OF_STRUCT) for i in range(self.numberOfSequences)]

    def add_offset(self, offset: int) -> None:
        if self.offsetToSequenceArray != 0:
            self.offsetToSequenceArray += offset

        

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Version Number: {self.versionNumber}\n"
        t += f"Sequence Array Offset: {hex(self.offsetToSequenceArray)}\n"
        t += f"Bank ID: {self.bankID}\n"
        t += f"Number of Sequences: {self.numberOfSequences}\n"
        t += f"Number of Tracks: {self.numberOfTracks}\n"
        t += f"Number of Keyframes: {self.numberOfKeyframes}\n"
        t += f"User Data Offset: {self.offsetToUserData}\n"
        t += f"User Data Size: {self.userDefinedDataSize}\n"
        return t    
    
class ANIMSequence(DataBytesInterpreter):
    DATA_FORMAT = ">I I H H"

    def __init__(self, b: bytes, offset: int) -> None:
        self.offsetToSequenceName, \
        self.offsetToTrackArray, \
        self.numberOfTracks, \
        _ \
        = self.parse_bytes(b, offset)

        self.add_offset(offset)
        self.tracks = [ANIMTrack(b, self.offsetToTrackArray + i * 16) for i in range(self.numberOfTracks)]

        if self.offsetToSequenceName != 0:
            pass

    def add_offset(self, offset):
        if self.offsetToSequenceName != 0:
            self.offsetToSequenceName += offset


       
    def __str__(self) -> str:
            t = ""
            t += f"=={self.__class__.__name__}==\n"
            t += f"Offset to Sequence Name: {hex(self.offsetToSequenceName)}\n"
            t += f"Offset to track array: {hex(self.offsetToTrackArray)}\n"
            t += f"Number of Tracks: {self.numberOfTracks}\n"
            return t
    
class ANIMTrack(DataBytesInterpreter):
    DATA_FORMAT = '>f I H H BBBB'

    def __init__(self, b: bytes, offset: int) -> None:
        self.animationTime, \
        self.offsetToKeyframeArray, \
        self.numberOfKeyframes, \
        self.trackID, \
        self.paramQuantizationInfo, \
        self.animationType, \
        self.interpolationType, \
        _ \
        = self.parse_bytes(b, offset)

        self.animTypes = {
            'matrix': bool(self.animationType & 0b00010000),
            'quatRot': bool(self.animationType & 0b00001000),
            'eulerRot': bool(self.animationType & 0b00000100),
            'scale': bool(self.animationType & 0b00000010),
            'trans': bool(self.animationType & 0b00000001)
        }
        self.interpolationTypes = {
            'rotation': (self.interpolationType >> 4) & 0b111,
            'scale': (self.interpolationType >> 2) & 0b11,
            'translation': self.interpolationType & 0b11
        }
        self.interpolationDescriptions = {
            'rotation': self._describe_interpolation(self.interpolationTypes['rotation']),
            'scale': self._describe_interpolation(self.interpolationTypes['scale']),
            'translation': self._describe_interpolation(self.interpolationTypes['translation'])
        }


        self.keyframes = [ANIMKeyFrame(b, self.offsetToKeyframeArray + i * ANIMKeyFrame.SIZE_OF_STRUCT) for i in range(self.numberOfKeyframes)]
    
    def _describe_interpolation(self, interpType):
        interp_map = {
            0b00: "None",
            0b01: "Linear",
            0b10: "Bezier",
            0b11: "Hermite",
            0b100: "SQUAD",
            0b101: "SQUADEE",
            0b110: "SLERP"
        }
        return interp_map.get(interpType, "Unknown")

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Animation Time: {self.animationTime}\n"
        t += f"Number of Keyframes: {self.numberOfKeyframes}\n"
        t += f"Track ID: {self.trackID}\n"
        t += f"Quant Info: {self.paramQuantizationInfo}\n"
        t += f"Anim Type: {self.animTypes}\n"
        t += f"Interpolation Type: {self.interpolationDescriptions}\n"
        return t

    
class ANIMKeyFrame(DataBytesInterpreter):
    DATA_FORMAT = '>f I I'

    def __init__(self, b: bytes, offset: int) -> None:
        # try:
        self.time, \
        self.offsetToSettingBank, \
        self.offsetToInterpolationInfo \
        = self.parse_bytes(b, offset)

    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        if self.time is not None:
            t += f"Time: {self.time}\n"
        else:
            t += "Time: Not Parsed\n"
        t += f"Setting Bank Offset: {hex(self.offsetToSettingBank)}\n"
        t += f"Interpolation Info Offset: {hex(self.offsetToInterpolationInfo)}\n"
        return t



def copyAttributesToDict(obj, dict, attrs):
    for attr in attrs:
        dict[attr] = getattr(obj, attr)

if __name__ == "__main__":
    # bytes = open_binary_get_bytes("outputs/US/Referenced Files/0A1B1000/0A1B1000.dat")
    # bank = ANIMBank(bytes, 0x0)
    # print(bank)
    # print()
    # for i in bank.sequences:
    #     print(i)
    #     print() 
    #     for j in i.tracks:
    #         print("        ", j)
    #         print()

    bytes = open_binary_get_bytes("outputs/US/Referenced Files/09874800/09874800.dat")
    bank = ANIMBank(bytes, 0x0)
    print(bank)
    print()
    for i in bank.sequences:
        print(i)
        print() 
        for j in i.tracks:
            print(j)
            for k in j.keyframes:
                print(k)
        print()