from structs import DBI
from helpers.file_handling import log_to_file

class DisplayStateTextureSetting(DBI):

    def from_setting(self, setting):
        self.textureIndex = setting & 0xff
        setting >>= 13
        self.layer = setting & 0b111
        setting >>= 3
        self.wrapS = setting & 0b1111
        setting >>= 4
        self.wrapT = setting & 0b1111
        setting >>= 4
        self.minFilter = setting & 0b1111
        setting >>= 4
        self.magFilter = setting & 0b1111

class DisplayStateVCDSetting(DBI):
    DATA_FORMAT = ">HHHHHHHHHHHHHxxxxxx"

    def from_setting(self, setting):
        self.setting = setting
        self.colors:list[int] = []
        self.textures:list[int] = []
        self.positionMatrixIndex = setting & 0b11
        setting >>= 2
        self.position = setting & 0b11
        setting >>= 2
        self.normal = setting & 0b11
        setting >>= 2
        for _ in range(2):
            self.colors.append(setting & 0b11)
            setting >>= 2
        for _ in range(8):
            self.textures.append(setting & 0b11)
            setting >>= 2

class DisplayStateMTXLoadSetting(DBI):
    DATA_FORMAT = ">II"

    def from_setting(self, setting):
        self.destinationMatrixIndex = setting & 0xffff
        self.sourceMatrixIndex = setting >> 16

class DisplayStateSettingHelper():
    DISPLAY_STATE_TEXTURE = 1
    DISPLAY_STATE_VCD = 2
    DISPLAY_STATE_MTXLOAD = 3

    def __init__(self, log_file):
        self.log_file = log_file
        self.VCDSetting:DisplayStateVCDSetting = DisplayStateVCDSetting()
        self.textureSettings:dict[int, DisplayStateTextureSetting] = {}
        self.mtxLoadSetting:DisplayStateMTXLoadSetting = DisplayStateMTXLoadSetting()

    def setVCDSetting(self, setting:DisplayStateVCDSetting) -> int:
        self.VCDSetting = setting

    def setTextureSetting(self, setting:DisplayStateTextureSetting) -> int:
        self.textureSettings[setting.layer] = setting

    def setMtxLoadSetting(self, setting:DisplayStateMTXLoadSetting) -> int:
        self.mtxLoadSetting = setting

    def getSrcMtxIndex(self) -> int:
        return self.mtxLoadSetting.sourceMatrixIndex

    def getDestMtxIndex(self) -> int:
        return self.mtxLoadSetting.destinationMatrixIndex

    def getTextureIndex(self, layer=0) -> int:
        return self.textureSettings[layer].textureIndex if layer in self.textureSettings else None
    
    def getComponents(self):
        size_conversion = {
            0:0,
            2:1,
            3:2
        }
        all_components = [(self.VCDSetting.setting >> (j * 2)) & 3 for j in range(13)]
        all_sizes = [size_conversion[j] for j in all_components]
        comps = {
            "vector_size": sum(all_sizes),
            "pos_size": all_sizes[1],
            "pos_offset": sum(all_sizes[:1]),
            "norm_size": all_sizes[2],
            "norm_offset": sum(all_sizes[:2]),
            "uv_size": [all_sizes[i] for i in range(5, len(all_sizes))],
            "uv_offset": [sum(all_sizes[:i]) for i in range(5, len(all_sizes))],
        }
        return comps

    def setSetting(self, stateID:int, setting:int):
        if stateID == self.DISPLAY_STATE_TEXTURE:
            s = DisplayStateTextureSetting()
            s.from_setting(setting)
            self.textureSettings[s.layer] = s
            log_to_file(self.log_file, f"Loading Texture {s.textureIndex}")
        elif stateID == self.DISPLAY_STATE_MTXLOAD:
            self.mtxLoadSetting.from_setting(setting)
            log_to_file(self.log_file, f"Matrix Load: Source {self.mtxLoadSetting.sourceMatrixIndex}, Destination {self.mtxLoadSetting.destinationMatrixIndex}")
        elif stateID == self.DISPLAY_STATE_VCD:
            self.VCDSetting.from_setting(setting)
            log_to_file(self.log_file, f"Vertex Description: {hex(self.VCDSetting.setting)}")
        else:
            raise ValueError(f"Unknown Display Call: {stateID}")