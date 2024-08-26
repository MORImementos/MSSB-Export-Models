from helper_c3 import SECTION_TYPES
from helper_obj_file import PositionVector, NormalVector, ColorVector, TextureVector
from helper_vector import Vector3, Vector4
from helper_rotation import sqtTransform
import numpy as np

class C3ExportGroup():
    def __init__(self) -> None:
        self.exports:dict[str,C3Export] = {}

class C3Export():
    def __init__(self, name) -> None:
        self.name = name
        self.sections:dict[int,C3Section] = {}

class C3Section():
    def __init__(self, type:int) -> None:
        self.type = type

#-- GEO data --#
class GEOMeshVertex():
    def __init__(self, positionInd:int, normalInd:int, texCoordInd:int, colorInd:int) -> None:
        self.positionInd = positionInd
        self.normalInd = normalInd
        self.texCoordInd = texCoordInd
        self.colorInd = colorInd

class GEOMeshFace():
    def __init__(self, vertices:list[GEOMeshVertex]) -> None:
        self.vertices = vertices

class GEODrawGroup():
    def __init__(self, textureIndices:dict[int,int], faces:list[GEOMeshFace]) -> None:
        self.textureIndices = textureIndices
        self.faces = faces

class GEOMesh():
    def __init__(self, name:str, numberOfTextures:int, positionList:list[PositionVector], texCoordList:list[TextureVector], normalList:list[NormalVector], colorList:list[ColorVector], drawGroups:list[GEODrawGroup]) -> None:
        self.name = name
        self.numberOfTextures = numberOfTextures
        self.positionList = positionList
        self.texCoordList = texCoordList
        self.colorList = colorList
        self.normalList = normalList
        self.drawGroups = drawGroups 

class C3GEOSection(C3Section):
    def __init__(self, meshes:list[GEOMesh]) -> None:
        super().__init__(SECTION_TYPES.GEO)
        self.numberOfMeshes:int = len(meshes)
        self.meshes:list[GEOMesh] = meshes
#-- end GEO data --#

#-- texture data --#
class C3TextureSection(C3Section):
    def __init__(self, part:int) -> None:
        super().__init__(SECTION_TYPES.texture)
        self.part = part
#-- end texture data --#

#-- ACT data --#
class ACTCTRL():
    def __init__(self, scale:Vector3, quaternion:Vector4, translation:Vector3) -> None:
        self.scale = scale
        self.quaternion = quaternion
        self.translation = translation

class ACTBone():
    def __init__(self, GEOFileID, boneID, inheritanceFlag, drawingPriority, previousSibling, nextSibling, parent, firstChild, orientation:ACTCTRL) -> None:
        self.GEOFileID = GEOFileID
        self.boneID = boneID
        self.inheritanceFlag = inheritanceFlag
        self.drawingPriority = drawingPriority
        self.previousSibling = previousSibling
        self.nextSibling = nextSibling
        self.parent = parent
        self.firstChild = firstChild
        self.orientation = orientation

class C3ACTSection(C3Section):
    def __init__(self, actorID:int, skinFileID:int, GEOPaletteName:str, boneList:list[ACTBone]) -> None:
        super().__init__(SECTION_TYPES.ACT)
        self.actorID = actorID
        self.skinFileID = skinFileID
        self.GEOPaletteName = GEOPaletteName
        self.bones = boneList
#-- end ACT data --#

#-- collision data --#
class C3CollisionSection(C3Section):
    def __init__(self) -> None:
        super().__init__(SECTION_TYPES.collision)
#-- end collision data --#

def transformMeshByBones(data:C3Export) -> None:
    # This is not correct
    # At the time of writing this, the skin file is not being parsed
    # We're getting stadiums working, which aren't skinned so can be implemented using only the GEO file ID
    # Also, this will eventually need to respect the bones' inheritanceFlags
    # Stadiums (or at least Mario Stadium) have a flat bone tree
    transformByGEOID = {}
    bone:ACTBone
    for bone in data.sections[SECTION_TYPES.ACT].bones:
        geo_id = bone.GEOFileID
        s = np.array(bone.orientation.scale)
        q = bone.orientation.quaternion
        t = bone.orientation.translation
        transform = sqtTransform(s, q, t)
        transformByGEOID[geo_id] = transform
    mesh:GEOMesh
    for GEOID, mesh in enumerate(data.sections[SECTION_TYPES.GEO].meshes):
        transform = transformByGEOID[GEOID]
        transform_normals = np.linalg.inv(transform).transpose()
        # This seems too verbose but idk how to use numpy correctly
        mesh.positionList = [np.array(([*x, 1] @ transform))[0,:3] for x in mesh.positionList]
        if mesh.normalList:
            mesh.normalList = [np.array(([*x, 1] @ transform_normals))[0,:3] for x in mesh.normalList]