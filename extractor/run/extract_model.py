from os.path import dirname, join, exists
from structs import GPL, DO, DS, OBJ
from helpers import get_parts_of_file, float_from_fixedpoint, get_c_str, copyAttributesToDict, write_text
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

    json_dict = dict()

    base_gpl_address = parts_of_file[part_of_file]
    geo_header = GPL.GeoPaletteHeader(file_bytes, base_gpl_address)
    log_to_file(log_file, f"GeoPaletteHeader: {geo_header}")
    log_to_file(log_file, f"Base GPL Address: {hex(base_gpl_address)}")
    geo_header.add_offset(base_gpl_address)

    descriptors:list[GPL.GeoDescriptor] = []

    json_dict['numberOfMeshes'] = geo_header.numberOfGeometryDescriptors

    mesh_arr = json_dict['meshes'] = []

    for i in range(geo_header.numberOfGeometryDescriptors):
        gd_offset = geo_header.offsetToGeometryDescriptorArray + i * GPL.GeoDescriptor.SIZE_OF_STRUCT
        d = GPL.GeoDescriptor(file_bytes, gd_offset)

        d.add_offset(base_gpl_address)
        MAX_NAME_LENGTH = 100
        
        d.name = get_c_str(file_bytes, d.offsetToName)
        log_to_file(log_file, f"GeoDescriptor {i}: {d}")

        descriptors.append(d)

        mesh_dict = dict()
        mesh_arr.append(mesh_dict)
        mesh_dict['name'] = d.name

        dol_offset = d.offsetToDisplayObject
        dol = DO.DisplayObjectLayout(file_bytes, dol_offset)
        dol.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectLayout {i}: {dol}")
        copyAttributesToDict(dol, mesh_dict, ['numberOfTextures'])

        dop = DO.DisplayObjectPositionHeader(file_bytes, dol.OffsetToPositionData)
        dop.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectPositionHeader {i}: {dop}")

        poss = parse_array_values(
            file_bytes[dop.offsetToPositionArray : dop.offsetToPositionArray + (dop.numberOfPositions * (dop.componentSize * dop.numberOfComponents))],
            3,
            dop.componentSize, 
            dop.componentSize * dop.numberOfComponents,
            dop.componentShift,
            dop.componentSigned,
            OBJ.PositionVector
            )
        log_to_file(log_file, f"Positions for Descriptor {i}: {poss}")

        mesh_dict['positionCoords'] = [list(x) for x in poss]

        doc = DO.DisplayObjectColorHeader(file_bytes, dol.OffsetToColorData)
        doc.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectColorHeader {i}: {doc}")

        dot = []
        tex_coords = []
        for i in range(dol.numberOfTextures):
            dd = DO.DisplayObjectTextureHeader(file_bytes, dol.OffsetToTextureData + i * DO.DisplayObjectTextureHeader.SIZE_OF_STRUCT)
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
                    OBJ.TextureVector
                    )
        log_to_file(log_file, f"Texture coordinates for Descriptor {i}: {tex_coords}")

        mesh_dict['textureCoords'] = [list(x) for x in tex_coords]

        doli = DO.DisplayObjectLightingHeader(file_bytes, dol.OffsetToLightingData)
        doli.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectLightingHeader {i}: {doli}")

        norms = parse_array_values(
            file_bytes[doli.offsetToNormalArray:][:(doli.numberOfNormals * (doli.componentSize * doli.numberOfComponents))],
            3,
            doli.componentSize, 
            doli.componentSize * doli.numberOfComponents, 
            doli.componentShift, 
            doli.componentSigned,
            OBJ.NormalVector
            )
        log_to_file(log_file, f"Normals for Descriptor {i}: {norms}")
        mesh_dict['normals'] = [list(x) for x in norms]

        dod = DO.DisplayObjectDisplayHeader(file_bytes, dol.OffsetToDisplayData)
        dod.add_offset(dol_offset)
        log_to_file(log_file, f"DisplayObjectDisplayHeader {i}: {dod}")

        dods = [DO.DisplayObjectDisplayState(file_bytes, dod.offsetToDisplayStateList + i * DO.DisplayObjectDisplayState.SIZE_OF_STRUCT) for i in range(dod.numberOfDisplayStateEntries)]
        all_draws = []

        groups_arr = mesh_dict['groups'] = []
        stateHelper = DS.DisplayStateSettingHelper(log_file)
        for dod_i, dod in enumerate(dods):
            dod.add_offset(dol_offset)
            log_to_file(log_file, f"DisplayObjectDisplayState {i}.{dod_i}: {dod}")

            stateHelper.setSetting(dod.stateID, dod.setting)

            if(dod.offsetToPrimitiveList != 0):
                tris = parse_indices(file_bytes[dod.offsetToPrimitiveList:][:dod.byteLengthPrimitiveList], stateHelper.getComponents())
                # these_tris.extend(tris)
                all_draws.append((tris, stateHelper.getTextureIndex(), 
                    [f"Using Texture {stateHelper.getTextureIndex()}", 
                    f"Using Matrix {stateHelper.getSrcMtxIndex()}, {stateHelper.getDestMtxIndex()}",
                    f"Display Object {dod_i}"]))
                log_to_file(log_file, f"Primitive List for Descriptor {i}.{dod_i}: {tris}")
                group_dict = dict()
                groups_arr.append(group_dict)
                group_dict['textureIndex'] = stateHelper.getTextureIndex(0)
                group_dict['matrixSrc'] = stateHelper.getSrcMtxIndex()
                group_dict['matrixDst'] = stateHelper.getDestMtxIndex()
                tris_list = group_dict['triangles'] = []
                for face in tris:
                    tri_dict = dict()
                    tris_list.append(tri_dict)
                    point_list = tri_dict['points'] = []
                    for point in face.obj_indices:
                        point_dict = dict()
                        point_list.append(point_dict)
                        if point.position_coordinate:
                            point_dict['position'] = point.position_coordinate.ind
                        if point.texture_coordinate:
                            point_dict['texture'] = point.texture_coordinate.ind
                        if point.normal_coordinate:
                            point_dict['normal'] = point.normal_coordinate.ind

        # Write to Obj
        coord_group = OBJ.OBJGroup(
            positions=poss,
            textures=tex_coords,
            normals=norms,
            faces=[],
            comments=[]
            )

        draw_groups = [OBJ.OBJGroup(positions=[], textures=[], normals=[], faces=gg[0], mtl=f"mssbMtl.{gg[1]}" if gg[1] != None else None, name=f"group{obj_part}", comments=gg[2]) for obj_part, gg in enumerate(all_draws)]

        draw_groups = [coord_group] + draw_groups
        # assert False

        mtl_file = join(mtl_header, "mtl.mtl")
        obj_file = OBJ.OBJFile(
            groups=draw_groups, 
            mtl_file=mtl_file
            )

        # if not obj_file.assert_valid():
        #     debug = 0

        write_text(str(obj_file), join(output_directory, d.name + ".obj"))
        log_to_file(log_file, f"Exported {d.name}.obj to {output_directory}")

    json_file = join(output_directory, "model.json")
    if os.path.exists(json_file):
        os.remove(json_file)
    with open(json_file, 'w') as f:
        f.write(json.dumps(json_dict, indent=4))
    
    return json_dict

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

def parse_indices(b: bytes, components) -> list[OBJ.OBJFace]:
    vector_size = components["vector_size"]
    pos_size = components["pos_size"]
    pos_offset = components["pos_offset"]
    norm_size = components["norm_size"]
    norm_offset = components["norm_offset"]
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
                
                if uv_size > 0:
                    uv = int.from_bytes(v[uv_offset:][:uv_size], 'big')
                else:
                    uv = None

                new_tris.append(OBJ.OBJIndices(
                    position_coordinate=OBJ.OBJIndex(pos),
                    normal_coordinate=OBJ.OBJIndex(norm),
                    texture_coordinate=OBJ.OBJIndex(uv)
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
    
    return [OBJ.OBJFace(face) for face in faces_to_return]

if __name__ == "__main__":
    main()