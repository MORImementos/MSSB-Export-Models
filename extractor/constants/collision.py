from enum import Enum

class StadiumTriangleCollectionType(Enum):
    SINGLES = 0
    STRIP = 1

class StadiumTriangleType(Enum):
    GRASS = 0x1
    WALL = 0x2
    OOB = 0x3
    FOUL_LINE_MARKERS = 0x4
    BACK = 0x5
    DIRT = 0x6
    PIT_WALL = 0x7
    PIT = 0x8
    ROUGH_TERRAIN = 0x9
    WATER = 0xA
    CHOMP_HAZARD = 0xB
    FOUL = 0x80