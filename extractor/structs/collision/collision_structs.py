from structs import DBI, Vec
from constants.collision import *
from struct import calcsize

class BoundingBox(DBI):
    DATA_FORMAT = ">ffffff"

    def __init__(self, b: bytes, offset: int) -> None:
        self.corner1 = Vec(b, offset)
        self.corner2 = Vec(b, offset + Vec.SIZE_OF_STRUCT)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:\nCorner 1: \n    {self.corner1}\nCorner 2: \n    {self.corner2}\n"

    def to_dict(self):
       return {
            "BoxCorner1": self.corner1.to_dict(),
            "BoxCorner2": self.corner2.to_dict()
        }
    
class Triangle(DBI):
    DATA_FORMAT = ">fffHH"

    def __init__(self, b: bytes, offset: int) -> None:
        self.x, self.y, self.z, self.triangleType, self.pad = self.parse_bytes(b, offset)

    def __repr__(self) -> str:
        return f"\n\nTriangle:\n    x: {self.x}\n    y: {self.y}\n    z: {self.z}\n    triangleType: {self.triangleType}\n    pad: {self.pad}\n"
    
    def to_dict(self):
        return {
            "CollisionType": self.triangleType,
            "Point": {
                "X": self.x,
                "Y": self.y,
                "Z": self.z
            }
        }
    
class TriangleGroup(DBI):
    DATA_FORMAT = ">HH"

    def __init__(self, b: bytes, offset: int) -> None:
        self.group_type, self.triangle_count = self.parse_bytes(b, offset)
        self.group_type = StadiumTriangleCollectionType(self.group_type)
        self.triangles = []
        if self.triangle_count != 0:
            self.parse_triangles(b, offset)

    def parse_triangles(self, b: bytes, offset: int) -> list:
        num_triangles = self.triangle_count + 2 if self.group_type == StadiumTriangleCollectionType.STRIP else self.triangle_count * 3
        for i in range(num_triangles):
            triangle_offset = offset + TriangleGroup.SIZE_OF_STRUCT + (i * Triangle.SIZE_OF_STRUCT)
            self.triangles.append(Triangle(b, triangle_offset))

    def __repr__(self) -> str:
        return f"TriangleGroup:\n    Type: {self.group_type}\n    Triangle Count: {self.triangle_count}\n"
    
    def to_dict(self):
        return {
            "CollectionType": self.group_type.value,
            "Points": [triangle.to_dict() for triangle in self.triangles]
        }

class Collision(DBI):
    DATA_FORMAT = ">HHII"

    def __init__(self, b: bytes, offset: int) -> None:
        self.count, self.unk, self.bounding_box_ptr, self.triangle_ptr_array_start = self.parse_bytes(b, offset)
        self.bounding_boxes = []
        self.triangle_collections = []
        self.parse_bounding_boxes(b, offset)
        self.parse_triangle_collections(b, offset)
        # print(self.triangle_collections)

    def parse_bounding_boxes(self, b, offset):
        bb_ptr = self.bounding_box_ptr + offset
        for i in range(self.count):
            box_ptr = bb_ptr + (i * BoundingBox.SIZE_OF_STRUCT)
            self.bounding_boxes.append(BoundingBox(b, box_ptr))

    def parse_triangle_collections(self, b, offset):
        offsets = []
        # get offsets
        for i in range(self.count):
            coll_offset = 0x8 + (i * 4)
            rev_offset = self.parse_bytes_static(b, offset + coll_offset, ">I")[0]
            offsets.append(rev_offset + offset)

        for i in range(self.count):
            collections = []

            tri_coll_ptr = offsets[i]
            while True:
                t = TriangleGroup(b, tri_coll_ptr)
                if t.triangle_count == 0:
                    break
                collections.append(t)
                group = t.group_type
                adjusted_tri_count = 0
                if group == StadiumTriangleCollectionType.STRIP:
                    adjusted_tri_count = 2 + t.triangle_count
                elif group == StadiumTriangleCollectionType.SINGLES:
                    adjusted_tri_count = t.triangle_count * 3
                tri_coll_ptr += calcsize(TriangleGroup.DATA_FORMAT) + (calcsize(Triangle.DATA_FORMAT) * adjusted_tri_count) 

            self.triangle_collections.append({
                "BoundingBox": self.bounding_boxes[i],
                "TriangleGroups": collections
            })

    def to_dict(self):
        return {
            "Triangle Collections": [
                {
                    **collection["BoundingBox"].to_dict(),
                    "Triangles": [group.to_dict() for group in collection["TriangleGroups"]]
                }
                for collection in self.triangle_collections
            ]
        }