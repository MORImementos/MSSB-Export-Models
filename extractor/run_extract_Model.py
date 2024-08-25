from os.path import dirname, join, exists
from helper_vector import *
from helper_obj_file import *
from helper_c3 import *
from helper_mssb_data import *
from helper_c3_export import *

from helper_mssb_data import get_parts_of_file, float_from_fixedpoint
import os, json

def main():
    # file_name = input("Input file name: ")
    file_name = r"E:\MSSB\MSSB-Export-Models\extractor\data\test\06CFD000.dat"
    part_of_file = int(input("Input part of file: "))
    with open(file_name, 'rb') as f:
        file_bytes = f.read()
    export_model(file_bytes, dirname(file_name), part_of_file)

def log_to_file(log_file, message):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def export_model(file_bytes:bytearray, output_directory:str, part_of_file = 2, mtl_header:str = "") -> dict:
    log_file = join(output_directory, "model_export_log.txt")
    if os.path.exists(log_file):
        os.remove(log_file)
    with open(log_file, 'w') as f:
        pass

    parts_of_file = get_parts_of_file(file_bytes)

    base_gpl_address = parts_of_file[part_of_file]
    geo_header = GeoPaletteHeader(file_bytes, base_gpl_address)
    log_to_file(log_file, f"GeoPaletteHeader: {geo_header}")
    log_to_file(log_file, f"Base GPL Address: {hex(base_gpl_address)}")
    geo_header.add_offset(base_gpl_address)

    descriptors:list[GeoDescriptor] = []

    mesh_arr = []

    for i in range(geo_header.numberOfGeometryDescriptors):
        gd_offset = geo_header.offsetToGeometryDescriptorArray + i * GeoDescriptor.SIZE_OF_STRUCT
        d = GeoDescriptor(file_bytes, gd_offset)

        d.add_offset(base_gpl_address)
        MAX_NAME_LENGTH = 100
        
        d.name = get_c_str(file_bytes, d.offsetToName)
        log_to_file(log_file, f"GeoDescriptor {i}: {d}")

        descriptors.append(d)

        mesh_name = d.name

        dol_offset = d.offsetToDisplayObject
        dol = DisplayObjectLayout(file_bytes, dol_offset)
        dol.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectLayout {i}: {dol}")
        numberOfTextures = dol.numberOfTextures

        dop = DisplayObjectPositionHeader(file_bytes, dol.OffsetToPositionData)
        dop.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectPositionHeader {i}: {dop}")

        poss = parse_array_values(
            file_bytes[dop.offsetToPositionArray : dop.offsetToPositionArray + (dop.numberOfPositions * (dop.componentSize * dop.numberOfComponents))],
            3,
            dop.componentSize, 
            dop.componentSize * dop.numberOfComponents,
            dop.componentShift,
            dop.componentSigned,
            PositionVector
            )
        log_to_file(log_file, f"Positions for Descriptor {i}: {poss}")

        positionCoords = [list(x) for x in poss]
        if len(positionCoords) == 0:
            positionCoords = None

        doc = DisplayObjectColorHeader(file_bytes, dol.OffsetToColorData)
        doc.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectColorHeader {i}: {doc}")

        dot = []
        tex_coords = []
        for i in range(dol.numberOfTextures):
            dd = DisplayObjectTextureHeader(file_bytes, dol.OffsetToTextureData + i * DisplayObjectTextureHeader.SIZE_OF_STRUCT)
            dd.add_offset(dol_offset)

            dd.name = get_c_str(file_bytes, dd.offsetToTexturePaletteFileName)

            dot.append(dd)
            log_to_file(log_file, f"DisplayObjectTextureHeader {i}: {dd}")

            if i == 0:
                tex_coords = parse_array_values(
                    file_bytes[dd.offsetToTextureCoordinateArray:][:(dd.numberOfCoordinates * (dd.componentSize * dd.numberOfComponents))],
                    2,
                    dd.componentSize, 
                    dd.componentSize * dd.numberOfComponents,
                    dd.componentShift, 
                    dd.componentSigned,
                    TextureVector
                    )
        log_to_file(log_file, f"Texture coordinates for Descriptor {i}: {tex_coords}")

        texCoords = [list(x) for x in tex_coords]
        if len(texCoords) == 0:
            texCoords = None

        doli = DisplayObjectLightingHeader(file_bytes, dol.OffsetToLightingData)
        doli.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectLightingHeader {i}: {doli}")

        norms = parse_array_values(
            file_bytes[doli.offsetToNormalArray:][:(doli.numberOfNormals * (doli.componentSize * doli.numberOfComponents))],
            3,
            doli.componentSize, 
            doli.componentSize * doli.numberOfComponents, 
            doli.componentShift, 
            doli.componentSigned,
            NormalVector
            )
        log_to_file(log_file, f"Normals for Descriptor {i}: {norms}")
        normalCoords = [list(x) for x in norms]
        if len(normalCoords) == 0:
            normalCoords = None

        doc = DisplayObjectColorHeader(file_bytes, dol.OffsetToColorData)
        doc.add_offset(dol_offset)

        colors = parse_array_values_color(
            # 4 bytes per color max
            file_bytes[doc.offsetToColorArray:][:(doc.numberOfColors * 4)],
            doc.numberOfColors,
            doc.format
        )
        meshColors = [list(x) for x in colors]
        if len(meshColors) == 0:
            meshColors = None

        dod = DisplayObjectDisplayHeader(file_bytes, dol.OffsetToDisplayData)
        dod.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectDisplayHeader {i}: {dod}")

        dods = [DisplayObjectDisplayState(file_bytes, dod.offsetToDisplayStateList + i * DisplayObjectDisplayState.SIZE_OF_STRUCT) for i in range(dod.numberOfDisplayStateEntries)]
        all_draws = []

        drawGroups:list[GEODrawGroup] = []
        stateHelper:DisplayStateSettingHelper = DisplayStateSettingHelper(log_file)
        for dod_i, dod in enumerate(dods):
            dod.add_offset(dol_offset)
            log_to_file(log_file, f"DisplayObjectDisplayState {i}.{dod_i}: {dod}")

            stateHelper.setSetting(dod.stateID, dod.setting)

            if(dod.offsetToPrimitiveList != 0):
                textureInds = {}
                for layerInd in stateHelper.textureSettings:
                    textureInds[layerInd] = stateHelper.textureSettings[layerInd].textureIndex
                tris = parse_indices(file_bytes[dod.offsetToPrimitiveList:][:dod.byteLengthPrimitiveList], stateHelper.getComponents())
                all_draws.append((tris, stateHelper.getTextureIndex(), 
                    [f"Using Texture {stateHelper.getTextureIndex()}", 
                    f"Using Matrix {stateHelper.getSrcMtxIndex()}, {stateHelper.getDestMtxIndex()}",
                    f"Display Object {dod_i}"]))
                log_to_file(log_file, f"Primitive List for Descriptor {i}.{dod_i}: {tris}")
                faceList = []
                for face in tris:
                    vertexList = []
                    for point in face.obj_indices:
                        vertex = GEOMeshVertex(None, None, None, None)
                        if point.position_coordinate:
                            vertex.positionInd = point.position_coordinate.ind
                        if point.texture_coordinate:
                            vertex.texCoordInd = point.texture_coordinate.ind
                        if point.normal_coordinate:
                            vertex.normalInd = point.normal_coordinate.ind
                        if point.color:
                            vertex.colorInd = point.color.ind
                        vertexList.append(vertex)
                    faceObj = GEOMeshFace(vertexList)
                    faceList.append(faceObj)
                drawGroup = GEODrawGroup(textureInds, faceList)
                drawGroups.append(drawGroup)
        
        mesh_obj = GEOMesh(mesh_name, numberOfTextures, positionCoords, texCoords, normalCoords, meshColors, drawGroups)
        mesh_arr.append(mesh_obj)

        # Write to Obj
        coord_group = OBJGroup(
            positions=poss,
            textures=tex_coords,
            normals=norms,
            colors=colors,
            faces=[],
            comments=[]
            )

        draw_groups = [OBJGroup(positions=[], textures=[], normals=[], colors = [], faces=gg[0], mtl=f"mssbMtl.{gg[1]}" if gg[1] != None else None, name=f"group{obj_part}", comments=gg[2]) for obj_part, gg in enumerate(all_draws)]

        draw_groups = [coord_group] + draw_groups
        # assert False

        mtl_file = join(mtl_header, "mtl.mtl")
        obj_file = OBJFile(
            groups=draw_groups, 
            mtl_file=mtl_file
            )

        # if not obj_file.assert_valid():
        #     debug = 0

        write_text(str(obj_file), join(output_directory, d.name + ".obj"))
        log_to_file(log_file, f"Exported {d.name}.obj to {output_directory}")

    # json_file = join(output_directory, "model.json")
    # if os.path.exists(json_file):
    #     os.remove(json_file)
    # with open(json_file, 'w') as f:
    #     f.write(json.dumps(json_dict, indent=4))
    modelObj = C3GEOSection(mesh_arr)
    return modelObj

def parse_array_values(b:bytes, component_count:int, component_width:int, struct_size:int, fixed_point:int, signed:bool, cls=None)->list:
    to_return = []
    offset = 0
    while offset < len(b):
        c = []
        these_b = b[offset:][:struct_size]
        for i in range(component_count):
            ii = int.from_bytes(these_b[i*component_width:][:component_width], 'big', signed=signed)
            f = float_from_fixedpoint(ii, fixed_point)
            c.append(f)
        to_return.append(c)
        offset += struct_size
    if cls == None:
        return to_return
    else:
        return [cls(*x) for x in to_return]

def parse_array_values_color(b:bytes, entry_count:int, format:int)->list:
    to_return = []
    if format >= 6 or format < 0:
        raise ValueError(f'Color format {format} is invalid')
    struct_size = [2, 3, 4, 2, 3, 4][format]
    bits_per = [[5, 6, 5, 0],
                 [8, 8, 8, 0],
                 [8, 8, 8, 0],
                 [4, 4, 4, 4],
                 [6, 6, 6, 6],
                 [8, 8, 8, 8]][format]    
    for i in range(entry_count):
        color = []
        these_bytes = int.from_bytes(b[(i*struct_size):][:struct_size], 'big', signed=False)
        shift = struct_size * 8
        for j in range(4):
            n = bits_per[j]
            if n:
                shift -= n
                mask = (1 << n) - 1
                val = (these_bytes >> shift) & mask
                val = int(val * 255 / mask)
                color.append(val)
            else:
                color.append(255)
        to_return.append(ColorVector(*color))
    return to_return

def parse_quads(l: list, cls=None) -> list:
    to_return = []
    assert(len(l) % 4 == 0)
    for i in range(len(l) // 4):
        ii = i*4
        to_return.append((l[ii+0], l[ii+1], l[ii+2]))
        to_return.append((l[ii+2], l[ii+3], l[ii+0]))
    if cls == None:
        return to_return
    else:
        return [cls(*x) for x in to_return]

def parse_triangles(l: list, cls=None) -> list:
    to_return = []
    assert(len(l) % 3 == 0)
    for i in range(len(l) // 3):
        ii = i*3
        to_return.append((l[ii+0], l[ii+1], l[ii+2]))
    if cls == None:
        return to_return
    else:
        return [cls(*x) for x in to_return]

def parse_fan(l: list, cls=None) -> list:
    to_return = []
    for i in range(len(l) - 2):
        to_return.append((l[0], l[i+1], l[i+2]))
    if cls == None:
        return to_return
    else:
        return [cls(*x) for x in to_return]

def parse_strip(l: list, cls=None) -> list:
    to_return = []
    for i in range(len(l) - 2):
        if i%2 == 0:
            to_return.append((l[i], l[i+1], l[i+2]))
        else:
            to_return.append((l[i+2], l[i+1], l[i]))
    if cls == None:
        return to_return
    else:
        return [cls(*x) for x in to_return]

def parse_indices(b: bytes, components) -> list[OBJFace]:
    vector_size = components["vector_size"]
    pos_size = components["pos_size"]
    pos_offset = components["pos_offset"]
    norm_size = components["norm_size"]
    norm_offset = components["norm_offset"]
    color_size = components["color_size"][0]
    color_offset = components["color_offset"][0]
    uv_size = components["uv_size"][0]
    uv_offset = components["uv_offset"][0]
    offset = 0

    faces_to_return = []
    while offset < len(b):
        command = b[offset]
        offset+=1
        
        if command == 0x61: # bp
            # print(hex(int_from_bytes(b[offset:offset+4])))
            offset+=4

            continue
        elif command == 0x00: # nop
            continue
        
        new_tris = []
        shifted_command = command >> 3
        if shifted_command in [0x10, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17]:
            assert(command & 0x7 == 0)
            count = int.from_bytes(b[offset:][:2], 'big')
            offset += 2
            for _ in range(count):
                v = b[offset:][:vector_size]
                if pos_size > 0:
                    pos = int.from_bytes(v[pos_offset:][:pos_size], 'big')
                else:
                    pos = None

                if norm_size > 0:
                    norm = int.from_bytes(v[norm_offset:][:norm_size], 'big')
                else:
                    norm = None

                if color_size > 0:
                    color = int.from_bytes(v[color_offset:][:color_size], 'big')
                else:
                    color = None

                if uv_size > 0:
                    uv = int.from_bytes(v[uv_offset:][:uv_size], 'big')
                else:
                    uv = None

                new_tris.append(OBJIndices(
                    position_coordinate=OBJIndex(pos),
                    normal_coordinate=OBJIndex(norm),
                    color=OBJIndex(color),
                    texture_coordinate=OBJIndex(uv)
                ))
                offset += vector_size
        else:
            print(f"Unrecognized command: {hex(command)}")
            assert(False)

        if shifted_command == 0x10: # Draw Quads
            new_tris = parse_quads(new_tris)
            # new_tris = []
        elif shifted_command == 0x12: # Draw Triangles
            new_tris = parse_triangles(new_tris)
            # new_tris = []
        elif shifted_command == 0x13: # Draw Triangle Strip
            new_tris = parse_strip(new_tris)
            # new_tris = []
        elif shifted_command == 0x14: # Draw Triangle Fan
            new_tris = parse_fan(new_tris)
            # new_tris = []
        elif shifted_command == 0x15: # Draw Lines
            print("Unimplemented Draw command")
            assert(False)
        elif shifted_command == 0x16: # Draw Line Strip
            print("Unimplemented Draw command")
            assert(False)
        elif shifted_command == 0x17: # Draw Points
            print("Unimplemented Draw command")
            assert(False)
        else:
            print("Unknown Draw command")
            assert(False)

        faces_to_return.extend(new_tris)
    
    return [OBJFace(face) for face in faces_to_return]

if __name__ == "__main__":
    main()