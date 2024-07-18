from os.path import dirname, exists
from os import makedirs
from typing import Union
import json

def get_parts_of_file(file_bytes:bytearray):
    found_inds = []

    i = 0
    while True:
        new_ind = int.from_bytes(file_bytes[i:i+4], 'big')
        i += 4
        
        if new_ind == 0:
            break

        if len(found_inds) != 0 and new_ind <= found_inds[-1]:
            break

        found_inds.append(new_ind)

    return found_inds

def float_from_fixedpoint(a:int, shift:int):
    return a / (1 << shift)

def ensure_dir(path:str):
    if not (path == '' or path in "\\/" or exists(path)):
        makedirs(path)

def write_text(s:str, file_path:str):
    write_bytes(s.encode(), file_path)

def write_bytes(b:bytes, file_path:str):
    ensure_dir(dirname(file_path))
    with open(file_path, "wb") as f:
        f.write(b)

def get_c_str(b: bytes, offset: int, max_length: Union[int, None] = 100):
    s = ""
    n_offset = offset
    while b[n_offset] != 0:
        s += chr(b[n_offset])

        if max_length != None and len(s) >= max_length:
            break

        n_offset += 1

    return s

def save_to_json(data, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def copyAttributesToDict(obj, dict, attrs):
    for attr in attrs:
        dict[attr] = getattr(obj, attr)

def warn(s:str) -> None:
    print (f'\033[93m' + s + f'\033[0m')