from dataclasses import dataclass
import typing
from helper_vector import *
from os.path import join
from helper_c3 import SECTION_TYPES
import numpy as np
from helper_rotation import sqtTransform

# need to check the Z for position/normal, might be oriented wrong direction
class PositionVector(Vector3):
    def __str__(self) -> str:
        return f"v {self.X} {-self.Y} {self.Z}" 

class TextureVector(Vector2):
    def __str__(self) -> str:
        return f"vt {self.U} {-self.V}" 

class NormalVector(Vector3):
    def __str__(self) -> str:
        return f"vn {self.X} {-self.Y} {self.Z}" 
    
@dataclass
class OBJIndex:
    ind: 'typing.Any'=None

    def __str__(self) -> str:
        return f"{self.ind+1}" if self.ind != None else ""

@dataclass
class OBJIndices:
    position_coordinate: OBJIndex = None
    texture_coordinate: OBJIndex = None
    normal_coordinate: OBJIndex = None

    def __str__(self) -> str:
        return "/".join(str(x) for x in [self.position_coordinate, self.texture_coordinate, self.normal_coordinate] if x != None)

        
@dataclass
class OBJFace:
    obj_indices:list[OBJIndices]

    def __str__(self) -> str:
        return "f " + " ".join(str(x) for x in self.obj_indices)

@dataclass
class OBJGroup:
    positions: list[PositionVector]
    textures: list[TextureVector]
    normals: list[NormalVector]

    faces: list[OBJFace]
    comments:list[str]

    mtl:"typing.any" = None
    name:"typing.any" = None
    def __str__(self) -> str:
        t = ""

        if self.name != None:
            t += f"g {self.name}\n"
    
        if self.mtl != None:
            t += f"usemtl {self.mtl}\n"

        if self.comments is not None:
            for c in self.comments:
                t += f"# {c}\n"

        for p in self.positions:
            t += f"{p}\n"
        for p in self.normals:
            t += f"{p}\n"
        for p in self.textures:
            t += f"{p}\n"
        for p in self.faces:
            t += f"{p}\n"

        return t

@dataclass        
class OBJFile:
    groups:list[OBJGroup]
    mtl_file:str = None

    def __str__(self) -> str:
        t = ""

        if self.mtl_file != None:
            mtl = self.mtl_file.replace("\\", "\\\\")
            t+= f"mtllib {self.mtl_file}\n"
        
        for mtl in self.groups:
            t += f"{mtl}\n"
        
        return t
    
    def assert_valid(self):
        poss = []
        uvs = []
        norms = []
        for g in self.groups:
            if g.positions != None:
                poss.extend(g.positions)
            if g.normals != None:
                norms.extend(g.positions)
            if g.textures != None:
                uvs.extend(g.positions)
        
            for f in g.faces:
                for o in f.obj_indices:

                    if o.position_coordinate.ind != None and o.position_coordinate.ind >= len(poss):
                        return False
                                            
                    if o.normal_coordinate.ind != None and o.normal_coordinate.ind >= len(norms):
                        return False

                    if o.texture_coordinate.ind != None and o.texture_coordinate.ind >= len(uvs):
                        return False
        return True

def obj_export(output_folder:str, section_data:dict) -> None:
    for group_name in section_data:
        # group_name is defined in the template
        data_ = section_data[group_name]
        fname = join(output_folder, f'{group_name}.obj')
        mtlname = join(output_folder, f'{group_name}.mtl')
        with open(mtlname, 'w') as f:
            pass
        dataGroups:list[OBJGroup] = []
        runningTotals = {
            'v': 0,
            'vt': 0,
            'vn': 0
        }
        transformMeshByBones(data_)
        for mesh in data_[SECTION_TYPES.GEO]['meshes']:
            positions = [PositionVector(*x) for x in mesh['positionCoords']]
            normals = [NormalVector(*x) for x in mesh['normals']]
            textures = [TextureVector(*x) for x in mesh['textureCoords']]
            mesh_name = mesh['name']

            dataGroups.append(OBJGroup(positions, textures, normals, [], []))
            for i, group in enumerate(mesh['groups']):
                faces:list[OBJFace] = []
                for face in group['triangles']:
                    face_indices:list[OBJIndices] = []
                    for point in face['points']:
                        this_point = OBJIndices()
                        if point['position'] is not None:
                            this_point.position_coordinate = OBJIndex(point['position'] + runningTotals['v'])
                        if point['texture'] is not None:
                            this_point.texture_coordinate = OBJIndex(point['texture'] + runningTotals['vt'])
                        if point['normal'] is not None:
                            this_point.normal_coordinate = OBJIndex(point['normal'] + runningTotals['vn'])
                        face_indices.append(this_point)
                    this_face = OBJFace(face_indices)
                    faces.append(this_face)
                this_group:OBJGroup = OBJGroup([], [], [], faces, comments=[], mtl=f"{group['textureIndex']}", name=f'{mesh_name}_group_{i}')
                dataGroups.append(this_group)
            runningTotals['v'] += len(positions)
            runningTotals['vt'] += len(textures)
            runningTotals['vn'] += len(normals)
            objFile = OBJFile(dataGroups, f'{group_name}.mtl')
            with open(fname, 'w') as f:
                f.write(str(objFile))

def transformMeshByBones(data:dict) -> None:
    # This is not correct
    # At the time of writing this, the skin file is not being parsed
    # We're getting stadiums working, which aren't skinned so can be implemented using only the GEO file ID
    # Also, this will eventually need to respect the bones' inheritanceFlags
    # Stadiums (or at least Mario Stadium) have a flat bone tree
    transformByGEOID = {}
    for bone in data[SECTION_TYPES.ACT]["bones"]:
        geo_id = bone['GEOFileID']
        s = np.array(bone['orientation']['scale'])
        q = bone['orientation']['quaternion']
        t = bone['orientation']['translation']
        transform = sqtTransform(s, q, t)
        transformByGEOID[geo_id] = transform
    for GEOID, mesh in enumerate(data[SECTION_TYPES.GEO]['meshes']):
        transform = transformByGEOID[GEOID]
        transform_normals = np.linalg.inv(transform).transpose()
        # This seems too verbose but idk how to use numpy correctly
        mesh['positionCoords'] = [np.array(([*x, 1] @ transform))[0,:3] for x in mesh['positionCoords']]
        mesh['normals'] = [np.array(([*x, 1] @ transform_normals))[0,:3] for x in mesh['normals']]
        pass