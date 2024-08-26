from dataclasses import dataclass
import typing
from helper_vector import *
from os.path import join, exists
from os import mkdir, listdir, rename
from helper_c3 import SECTION_TYPES
from helper_c3_export import *
import numpy as np
import shutil

@dataclass
class OBJIndex:
    ind: 'typing.Any'=None

    def __str__(self) -> str:
        return f"{self.ind+1}" if self.ind != None else ""

@dataclass
class OBJIndices:
    position_coordinate: OBJIndex = None
    texture_coordinate: OBJIndex = None
    color:OBJIndex = None
    normal_coordinate: OBJIndex = None

    def __str__(self) -> str:
        return "/".join(str(x) if x != None else '' for x in [self.position_coordinate, self.texture_coordinate, self.normal_coordinate])

        
@dataclass
class OBJFace:
    obj_indices:list[OBJIndices]

    def __str__(self, colors=None) -> str:
        s = ''
        if colors is not None:
            inds = [index.color.ind if index.color is not None else None for index in self.obj_indices]
            if None not in inds:
                s += '# colors: ' + ', '.join(['(' + ','.join([str(y) for y in colors[x]]) + ')' for x in inds]) + '\n'
        s += "f " + " ".join(str(x) for x in self.obj_indices)
        return s

@dataclass
class OBJGroup:
    positions: list[Vector3]
    textures: list[Vector3]
    normals: list[Vector3]
    colors: list[Vector3]

    faces: list[OBJFace]
    comments:list[str]

    mtl:"typing.any" = None
    name:"typing.any" = None
    def __str__(self, colors=None) -> str:
        t = ""

        if self.name != None and self.name.isascii():
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
            t += p.__str__(colors) + '\n'

        return t

@dataclass        
class OBJFile:
    groups:list[OBJGroup]
    mtl_file:str = None

    # could probably calculate colors within the str method instead of passing it in
    def __str__(self, colors:list=None) -> str:
        t = ""

        if self.mtl_file != None:
            mtl = self.mtl_file.replace("\\", "\\\\")
            t+= f"mtllib {self.mtl_file}\n"
        
        for mtl in self.groups:
            t += mtl.__str__(colors) + '\n'
        
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

def obj_export(output_folder:str, section_data:C3ExportGroup) -> None:
    for group_name in section_data.exports:
        # group_name is defined in the template
        data_:C3Export = section_data.exports[group_name]
        dataGroups:list[OBJGroup] = []
        runningTotals = {
            'v': 0,
            'vt': 0,
            'vn': 0,
            'vc': 0,
        }
        this_output_folder = join(output_folder, group_name)
        if not exists(this_output_folder):
            mkdir(this_output_folder)
        objname = join(this_output_folder, f'{group_name}.obj')
        if SECTION_TYPES.ACT in data_.sections and SECTION_TYPES.GEO in data_.sections:
            transformMeshByBones(data_)
        allColors = []
        mesh:GEOMesh
        for mesh in data_.sections[SECTION_TYPES.GEO].meshes:
            positions = [PositionVector(*x) for x in mesh.positionList]
            normals = [NormalVector(*x) for x in mesh.normalList]
            textures = [TextureVector(*x) for x in mesh.texCoordList]
            colors = [ColorVector(*x) for x in mesh.colorList]
            allColors.extend(colors)
            mesh_name = mesh.name

            dataGroups.append(OBJGroup(positions, textures, normals, colors, [], []))
            for i, group in enumerate(mesh.drawGroups):
                faces:list[OBJFace] = []
                for face in group.faces:
                    face_indices:list[OBJIndices] = []
                    for vertex in face.vertices:
                        this_point = OBJIndices()
                        if vertex.positionInd is not None:
                            this_point.position_coordinate = OBJIndex(vertex.positionInd + runningTotals['v'])
                        if vertex.texCoordInd is not None:
                            this_point.texture_coordinate = OBJIndex(vertex.texCoordInd + runningTotals['vt'])
                        if vertex.normalInd is not None:
                            this_point.normal_coordinate = OBJIndex(vertex.normalInd + runningTotals['vn'])
                        if vertex.colorInd is not None:
                            this_point.color = OBJIndex(vertex.colorInd + runningTotals['vc'])
                        face_indices.append(this_point)
                    this_face = OBJFace(face_indices)
                    faces.append(this_face)
                this_group:OBJGroup = OBJGroup([], [], [], [], faces, comments=[], mtl=f"mssbMtl.{group.textureIndices.get(0, 'NONE')}", name=f'{mesh_name}_group_{i}')
                dataGroups.append(this_group)
            runningTotals['v'] += len(positions)
            runningTotals['vt'] += len(textures)
            runningTotals['vn'] += len(normals)
            runningTotals['vc'] += len(colors)
        objFile = OBJFile(dataGroups, f'{group_name}.mtl')
        with open(objname, 'w') as f:
            f.write(objFile.__str__(allColors))
        # copy the mtl file from the other folder
        if SECTION_TYPES.texture in data_.sections and data_.sections[SECTION_TYPES.texture] is not None:
            mtl_section = data_.sections[SECTION_TYPES.texture].part
            existing_mtl_path = join(output_folder, f'part {mtl_section}')
            for file in listdir(existing_mtl_path):
                if file[-4:] == '.mtl':
                    shutil.move(join(existing_mtl_path, file), join(this_output_folder, f'{group_name}.mtl'))
                else:
                    try:
                        shutil.move(join(existing_mtl_path, file), this_output_folder)
                    except shutil.Error:
                        continue
                # with open(existing_mtl_path, 'r') as f:
                #     existing_mtl_data = f.readlines()
                # mtl_path = join(this_output_folder, f'{group_name}.mtl')
                # with open(mtl_path, 'w+') as f:
                #     for line in existing_mtl_data:
                #         newline = line
                #         if line.find('map_kd') > -1:
                #             newline = line.replace('map_kd ', 'map_kd ' + f'part {mtl_section}/').strip() + '\n'
                #             print(newline)
                #         f.write(newline)