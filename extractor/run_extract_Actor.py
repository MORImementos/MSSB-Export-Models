from os.path import dirname, join, exists
from helper_vector import *
from helper_obj_file import *
from helper_c3 import *
from helper_mssb_data import *

from helper_mssb_data import get_parts_of_file, float_from_fixedpoint
import os

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

def export_actor(file_bytes:bytearray, output_directory:str, part_of_file):

    log_file = join(output_directory, "actor_export_log.txt")
    if os.path.exists(log_file):
        os.remove(log_file)

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

if __name__ == "__main__":
    main()