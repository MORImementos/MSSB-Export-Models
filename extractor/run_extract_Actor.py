from os.path import dirname, join, exists
from helper_vector import *
from helper_obj_file import *
from helper_c3 import *
from helper_mssb_data import *

from helper_mssb_data import get_parts_of_file, float_from_fixedpoint

def main():
    # todo (duh)
    print("extracting actor on a per file basis is not yet implemented")

def export_actor(file_bytes:bytearray, output_directory:str, part_of_file):
    parts_of_file = get_parts_of_file(file_bytes)

    base_act_address = parts_of_file[part_of_file]
    act_header = ACTLayoutHeader(file_bytes, base_act_address)
    print(act_header)
    print(hex(base_act_address))
    act_header.add_offset(base_act_address)
    geo_name = get_c_str(file_bytes, act_header.GEOPaletteName)

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
        print(bone)

if __name__ == "__main__":
    main()