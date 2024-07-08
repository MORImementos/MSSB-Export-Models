from os.path import dirname, join, exists
from helper_vector import *
from helper_obj_file import *
from helper_c3 import *
from helper_mssb_data import *

from helper_mssb_data import get_parts_of_file, float_from_fixedpoint
import os, json

def main():
    # added a basic impl like I used for the model extract
    file_name = r"E:\MSSB\MSSB-Export-Models\extractor\data\test\06CFD000.dat"
    part_of_file = int(input("Input part of file: "))
    with open(file_name, 'rb') as f:
        file_bytes = f.read()
    export_actor(file_bytes, dirname(file_name), part_of_file)

# log 
def log_to_file(log_file, message):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def export_actor(file_bytes:bytearray, output_directory:str, part_of_file) -> dict:

    log_file = join(output_directory, "actor_export_log.txt")
    if os.path.exists(log_file):
        os.remove(log_file)
    f = open(log_file, 'w')
    f.close()

    json_dict = dict()

    parts_of_file = get_parts_of_file(file_bytes)

    base_act_address = parts_of_file[part_of_file]
    act_header = ACTLayoutHeader(file_bytes, base_act_address)
    log_to_file(log_file, f"{act_header}")
    log_to_file(log_file, f"Base ACT Address: {hex(base_act_address)}")
    act_header.add_offset(base_act_address)
    geo_name = get_c_str(file_bytes, act_header.GEOPaletteName)
    log_to_file(log_file, f"GeoPaletteName: {geo_name}")

    rootBone = ACTBoneLayoutHeader(file_bytes, act_header.boneTree.offsetToRoot)
    rootBone.add_offset(base_act_address)
    ACTBoneLayoutHeaders:list[ACTBoneLayoutHeader] = [rootBone]
    boneStack:list[ACTBoneLayoutHeader] = [rootBone]
    # Haven't tested this on a bone structure with any depth
    while len(boneStack):
        top = boneStack[-1]
        if top.branch.offsetToFirstChildBranch and top.firstChildBone is None:
            childBone = ACTBoneLayoutHeader(file_bytes, top.branch.offsetToFirstChildBranch)
            ACTBoneLayoutHeaders.append(childBone)
            childBone.add_offset(base_act_address)
            childBone.parentBone = top
            top.firstChildBone = childBone
            boneStack.append(childBone)
        else:
            boneStack.pop()
            if top.branch.offsetToNextBranch:
                siblingBone = ACTBoneLayoutHeader(file_bytes, top.branch.offsetToNextBranch)
                ACTBoneLayoutHeaders.append(siblingBone)
                siblingBone.add_offset(base_act_address)
                siblingBone.previousBone = top
                top.nextBone = siblingBone
                siblingBone.parentBone = top.parentBone
                boneStack.append(siblingBone)
    for bone in ACTBoneLayoutHeaders:
        if bone.offsetToCTRLControl:
            bone.CTRL = CTRLControl(file_bytes, bone.offsetToCTRLControl)
        else:
            # Feed in dummy data that gives this bone an SRT correlating to the identity
            bone.CTRL = CTRLControl(b'\0\0\0\0', 0)
        log_to_file(log_file, f"{bone}")

    actor_file = join(output_directory, f"{geo_name}.actor")
    with open(actor_file, 'w', encoding='utf-8') as f:
        f.write(f"ACTLayoutHeader: {act_header}\n")
        f.write(f"GeoPaletteName: {geo_name}\n")
        for bone in ACTBoneLayoutHeaders:
            f.write(f"{bone}\n")

    copyAttributesToDict(act_header, json_dict, [
        'actorID',
        'numberOfBones',
        'skinFileID'
    ])
    json_dict['GEOPaletteName'] = geo_name
    bone_list = json_dict['bones'] = []
    for bone in ACTBoneLayoutHeaders:
        bone_dict = dict()
        bone_list.append(bone_dict)
        copyAttributesToDict(bone, bone_dict, [
            'GEOFileID',
            'boneID',
            'inheritanceFlag',
            'drawingPriority',
        ])
        bone_dict['previousSibling'] = bone.previousBone.boneID if bone.previousBone else -1
        bone_dict['nextSibling'] = bone.nextBone.boneID if bone.nextBone else -1
        bone_dict['parent'] = bone.parentBone.boneID if bone.parentBone else -1
        bone_dict['firstChild'] = bone.firstChildBone.boneID if bone.firstChildBone else -1
        orientation_dict = bone_dict['orientation'] = dict()
        # I'm assuming every CTRL is a CTRLSRTControl type, if CTRLMTXControl
        # ever needs to be implemented this will need to be updated
        orientation_dict['scale'] = bone.CTRL.SRT.getScale()
        orientation_dict['quaternion'] = bone.CTRL.SRT.getQuaternionRotation()
        orientation_dict['translation'] = bone.CTRL.SRT.getTranslation()

    json_file = join(output_directory, "actor.json")
    if os.path.exists(json_file):
        os.remove(json_file)
    with open(json_file, 'w') as f:
        f.write(json.dumps(json_dict, indent=4))
    
    return json_dict

if __name__ == "__main__":
    main()