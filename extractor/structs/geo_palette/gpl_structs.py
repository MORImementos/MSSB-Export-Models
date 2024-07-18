from structs import DBI

class GeoPaletteHeader(DBI):
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

class GeoDescriptor(DBI):
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