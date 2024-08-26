from dataclasses import dataclass
import typing
from helper_vector import *
from os.path import join, exists
from os import mkdir, listdir, rename
from helper_c3 import SECTION_TYPES
from helper_c3_export import *
import numpy as np
import x3d
from helper_rotation import sqtTransform
import shutil, os

def x3d_export(output_folder:str, section_data:C3ExportGroup) -> None:
    for group_name in section_data.exports:
        # group_name is defined in the template
        export:C3Export = section_data.exports[group_name]
        this_output_folder = join(output_folder, group_name)
        if not exists(this_output_folder):
            mkdir(this_output_folder)
        x3dname = join(this_output_folder, f'{group_name}.x3d')
        if SECTION_TYPES.ACT in export.sections and SECTION_TYPES.GEO in export.sections:
            transformMeshByBones(export)
        if SECTION_TYPES.GEO in export.sections:
            GEOData:C3GEOSection = export.sections[SECTION_TYPES.GEO]
            scene = x3d.Scene()
            for GEOID, mesh in enumerate(GEOData.meshes):
                mesh_prefix = f"mesh_{GEOID}"
                coords = None
                texCoords = None
                normalCoords = None
                colors = None
                if mesh.positionList:
                    coords = x3d.Coordinate(point=mesh.positionList, DEF=f"{mesh_prefix}_coords")
                if mesh.normalList:
                    normalCoords = x3d.Normal(vector=mesh.normalList, DEF=f"{mesh_prefix}_normals")
                if mesh.texCoordList:
                    texCoords = x3d.TextureCoordinate(point=mesh.texCoordList, DEF=f"{mesh_prefix}_texcoords")
                if mesh.colorList:
                    colorData = np.array(mesh.colorList) / 255
                    colorData = [tuple(l) for l in colorData]
                    colors = x3d.ColorRGBA(color=colorData, DEF=f"{mesh_prefix}_colors")
                for group_ind, group in enumerate(mesh.drawGroups):
                    geometry = x3d.IndexedFaceSet()
                    if coords:
                        coordIndices = []
                        for f in group.faces:
                            coordIndices.extend([v.positionInd for v in f.vertices] + [-1])
                        geometry.coordIndex = coordIndices
                        if group_ind == 0:
                            geometry.coord = coords
                        else:
                            geometry.coord = x3d.Coordinate(USE=coords.DEF)
                    if normalCoords:
                        normalIndices = []
                        for f in group.faces:
                            normalIndices.extend([v.normalInd for v in f.vertices] + [-1])
                        geometry.normalIndex = normalIndices
                        if group_ind == 0:
                            geometry.normal = normalCoords
                        else:
                            geometry.normal = x3d.Normal(USE=normalCoords.DEF)
                    if texCoords:
                        texIndices = []
                        for f in group.faces:
                            texIndices.extend([v.texCoordInd for v in f.vertices] + [-1])
                        geometry.texCoordIndex = texIndices
                        if group_ind == 0:
                            geometry.texCoord = texCoords
                        else:
                            geometry.texCoord = x3d.TextureCoordinate(USE=texCoords.DEF)
                    if colors:
                        colorInds = []
                        for f in group.faces:
                            colorInds.extend([v.colorInd if v.colorInd is not None else 0 for v in f.vertices] + [-1])
                        geometry.colorIndex = colorInds
                        geometry.colorPerVertex = True
                        if group_ind == 0:
                            geometry.color = colors
                        else:
                            geometry.color = x3d.ColorRGBA(USE=colors.DEF)
                    shape = x3d.Shape()
                    shape.geometry = geometry
                    appearance = x3d.Appearance()
                    tex_ind = group.textureIndices.get(0)
                    if tex_ind is not None and SECTION_TYPES.texture in export.sections:
                        texture_part = export.sections[SECTION_TYPES.texture].part
                        img_path = os.path.join(output_folder, f"part {texture_part}/{tex_ind}.png")
                        new_path = os.path.join(this_output_folder, f"{tex_ind}.png")
                        if not os.path.isfile(new_path):
                            shutil.copy(img_path, new_path)
                        texture = x3d.ImageTexture(url=f"{tex_ind}.png")
                        appearance.texture = texture
                    appearance.material = x3d.Material()
                    shape.appearance = appearance
                    scene.children.append(shape)
            head = x3d.head()
            model = x3d.X3D(Scene=scene, head=head)

            with open(x3dname, 'w') as f:
                f.write(model.XML())