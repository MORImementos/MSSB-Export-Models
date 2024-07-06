from struct import pack, unpack, calcsize, unpack_from
from enum import Enum
import logging
import json
from helper_mssb_data import DataBytesInterpreter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# make handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('extractor/data/test/debug.log', mode='w')

# make formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# switch logging modes
def set_logging_mode(mode='both'):
    if mode == 'console':
        logger.removeHandler(file_handler)
        if console_handler not in logger.handlers:
            logger.addHandler(console_handler)
    elif mode == 'file':
        logger.removeHandler(console_handler)
        if file_handler not in logger.handlers:
            logger.addHandler(file_handler)
    elif mode == 'both':
        if console_handler not in logger.handlers:
            logger.addHandler(console_handler)
        if file_handler not in logger.handlers:
            logger.addHandler(file_handler)
    elif mode == 'none':
        logger.removeHandler(file_handler)
        logger.removeHandler(console_handler)
    else:
        raise ValueError("Invalid logging mode. Use 'console', 'file', 'both', or 'none'.")

# default logging mode
set_logging_mode('file')

def open_binary_get_bytes(file):
    with open(file, "rb") as f:
        return f.read()


class StadiumTriangleCollectionType(Enum):
    SINGLES = 0
    STRIP = 1

class StadiumTriangleType(Enum):
    GRASS = 0x1
    WALL = 0x2
    OOB = 0x3 # also labelled as structures somewhere
    FOUL_LINE_MARKERS = 0x4
    BACK = 0x5
    DIRT = 0x6
    PIT_WALL = 0x7
    PIT = 0x8
    ROUGH_TERRAIN = 0x9
    WATER = 0xA
    CHOMP_HAZARD = 0xB
    FOUL = 0x80

class Vec(DataBytesInterpreter):
    DATA_FORMAT = ">fff"

    def __init__(self, b: bytes, offset: int) -> None:
        self.x, self.y, self.z = self.parse_bytes(b, offset)

class BoundingBox(DataBytesInterpreter):
    DATA_FORMAT = ">ffffff"

    def __init__(self, b: bytes, offset: int) -> None:
        self.corner1 = Vec(b, offset)
        self.corner2 = Vec(b, offset + Vec.SIZE_OF_STRUCT)
        logger.debug(f"Parsed BoundingBox at offset {hex(offset)}: {self}")

    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Corner 1: \n    X: {self.corner1.x}\n    Y: {self.corner1.y}\n    Z: {self.corner1.z}\n"
        t += f"Corner 2: \n    X: {self.corner2.x}\n    Y: {self.corner2.y}\n    Z: {self.corner2.z}\n"
        return t

    def __repr__(self) -> str:
        t = ""
        t += f"{self.__class__.__name__}:\n"
        t += f"Corner 1: \n    X: {self.corner1.x}\n    Y: {self.corner1.y}\n    Z: {self.corner1.z}\n"
        t += f"Corner 2: \n    X: {self.corner2.x}\n    Y: {self.corner2.y}\n    Z: {self.corner2.z}\n"
        return t

    def to_dict(self):
        return {
            "BoxCorner1": {
                "X": self.corner1.x,
                "Y": self.corner1.y,
                "Z": self.corner1.z
            },
            "BoxCorner2": {
                "X": self.corner2.x,
                "Y": self.corner2.y,
                "Z": self.corner2.z
            }
        }

class Triangle(DataBytesInterpreter):
    DATA_FORMAT = ">fffHH"

    def __init__(self, b: bytes, offset: int) -> None:
        self.x, \
        self.y, \
        self.z, \
        self.triangleType, \
        self.pad, \
        = self.parse_bytes(b, offset)
        # self.is_foul = (self.triangleType & 0xF0) != 0
        # self.triangleType = StadiumTriangleType(self.triangleType & 0x0F)
        # self.triangleType = self.triangleType

        logger.debug(f"Parsed Triangle at offset {hex(offset)}: {self}")


    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Point: ({self.x}, {self.y}, {self.z})\n"
        t += f"Type: {self.triangleType}\n"
        return t

    def __repr__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Point: ({self.x}, {self.y}, {self.z})\n"
        t += f"Type: {self.triangleType}\n"
        return t

    def to_dict(self):
        return {
            "CollisionType": self.triangleType,
            "Point": {
                "X": self.x,
                "Y": self.y,
                "Z": self.z
            }
        }
    

class TriangleGroup(DataBytesInterpreter):
    DATA_FORMAT = ">HH"

    def __init__(self, b: bytes, offset: int) -> None:
        self.group_type, \
        self.triangle_count, \
        = self.parse_bytes(b, offset)
        logger.debug(f"Parsed TriangleGroup header at offset {hex(offset)}: GroupType={self.group_type}, TriangleCount={self.triangle_count}")
        self.group_type = StadiumTriangleCollectionType(self.group_type)
        self.triangles = self.parse_triangles(b, offset + calcsize(self.DATA_FORMAT))
        logger.debug(f"TriangleGroup Triangle Count: {len(self.triangles)}")

    def parse_triangles(self, b: bytes, start_offset: int) -> list:
        num_triangles = self.triangle_count + 2 if self.group_type == StadiumTriangleCollectionType.STRIP else self.triangle_count * 3
        logger.debug(f"Num. triangles: {num_triangles}")
        triangles = []
        for i in range(num_triangles):
            triangle_offset = start_offset + i * calcsize(Triangle.DATA_FORMAT)
            logger.debug(f"Parsing Triangle at offset {hex(triangle_offset)}")
            triangles.append(Triangle(b, triangle_offset))
        logger.debug(f"Triangles: {triangles}\nLen. Triangles: {len(triangles)}")
        return triangles

    @property
    def size(self):
        return calcsize(self.DATA_FORMAT) + len(self.triangles) * calcsize(Triangle.DATA_FORMAT)
    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Triangle Collection Type: {StadiumTriangleCollectionType(self.collectionType).name}\n"
        t += f"Triangle Count: {self.count}\n"
        t += f"Triangles: {self.triangles}\n"
        return t

    def __repr__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Triangle Collection Type: {StadiumTriangleCollectionType(self.collectionType).name}\n"
        t += f"Triangle Count: {self.count}\n"
        t += f"Triangles: {self.triangles}\n"
        return t

    def to_dict(self):
        return {
            "CollectionType": StadiumTriangleCollectionType(self.group_type).value,
            "Triangles": [triangle.to_dict() for triangle in self.triangles]
        }

class Collision(DataBytesInterpreter):
    DATA_FORMAT = ">HHII"

    def __init__(self, b: bytes, offset: int, section_end) -> None:
        self.count, \
        self.unk, \
        self.bounding_box_ptr, \
        self.triangle_ptr_array_start, \
        = self.parse_bytes(b, offset)
        logger.debug(f"Parsed Collision header at offset {hex(offset)}: Count={self.count}, BoundingBoxPtr={hex(self.bounding_box_ptr)}, TrianglePtrArrayStart={hex(self.triangle_ptr_array_start)}")
        self.bounding_boxes = self.get_bounding_boxes(b, offset, section_end)
        self.triangle_groups = self.get_triangle_groups(b, offset, section_end)
        logger.debug(f"BoundingBoxes: {len(self.bounding_boxes)}, TriangleGroups: {len(self.triangle_groups)}")
        
    def get_bounding_boxes(self, b, offset, section_end):
        boxes = []
        for i in range(self.count):
            box_offset = offset + self.bounding_box_ptr + (i * BoundingBox.SIZE_OF_STRUCT)
            if box_offset + BoundingBox.SIZE_OF_STRUCT > section_end:
                logger.debug(f"Skipping BoundingBox at offset {hex(box_offset)}, exceeds section boundary.")
                break
            logger.debug(f"Parsing BoundingBox at offset {hex(box_offset)}")
            bounding_box = BoundingBox(b, box_offset)
            boxes.append(bounding_box)
        return boxes

    def get_triangle_groups(self, b, offset, section_end):
        groups = []
        for i in range(self.count):
            logger.debug(f"Parsing TriangleGroup index {i}")
            array_offset = offset + self.triangle_ptr_array_start + (i * 4)
            logger.debug(f"Array offset: {hex(array_offset)}")
            if array_offset + 4 > section_end:
                logger.debug(f"Skipping TriangleGroup pointer at offset {hex(array_offset)}, exceeds section boundary.")
                break
            adjusted_offset = array_offset
            if adjusted_offset >= section_end:
                logger.debug(f"Skipping TriangleGroup at offset {hex(adjusted_offset)}, out of bounds.")
                continue
            logger.debug(f"Parsing TriangleGroup at offset {hex(adjusted_offset)}")
            while True:
                if adjusted_offset >= len(b):
                    logger.debug(f"Skipping triangle group at offset {hex(adjusted_offset)}, out of bounds.")
                    break
                group = TriangleGroup(b, adjusted_offset)
                if group.triangle_count == 0:
                    logger.debug(f"Encountered TriangleGroup with 0 triangles at offset {hex(adjusted_offset)}, stopping parsing for this group.")
                    break
                groups.append(group)
                adjusted_offset += group.size
                logger.debug(f"Next TriangleGroup offset {hex(adjusted_offset)}")
        return groups
    
    def __str__(self) -> str:
        t = ""
        t += f"=={self.__class__.__name__}==\n"
        t += f"Count: {hex(self.count)}\n"
        t += f"Unk: {self.unk}\n"
        t += f"BB Pointer: {hex(self.boundingBoxPtr)}\n"
        t += f"Triangle Groups: {self.triangle_groups}\n"
        return t

    # def to_dict(self):
    #     return {
    #         "Triangle Collections": [
    #             {
    #                 "BoxCorner1": self.bounding_boxes[i].to_dict()["BoxCorner1"],
    #                 "BoxCorner2": self.bounding_boxes[i].to_dict()["BoxCorner2"],
    #                 "Triangles": self.triangle_groups[i].to_dict()["Triangles"]
    #             } for i in range(len(self.bounding_boxes))
    #         ]
    #     }
    def to_dict(self):
        return {
            "BoundingBoxes": [box.to_dict() for box in self.bounding_boxes],
            "TriangleGroups": [group.to_dict() for group in self.triangle_groups]
        }

def save_to_json(data, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == "__main__":
    bytes = open_binary_get_bytes(r'E:\MSSB\MSSB-Export-Models\extractor\data\test\06CFD000.dat')
    col = Collision(bytes, 0x167700, 0x168a68)
    save_to_json(col.to_dict(), r'E:\MSSB\MSSB-Export-Models\extractor\data\test\output2.json')