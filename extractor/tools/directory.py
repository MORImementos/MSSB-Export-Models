import json
import os
from dataclasses import dataclass

DATA = "extractor\\data"
OUTPUTS = "extractor\\outputs"
TOOLS = "extractor\\tools"
US = "US"
JP = "JP"
EU = "EU"
BETA = "beta"
FAMILY = "Family"
FILE_NAMES = "FileNames.json"
REFERENCED_FILES = "Referenced Files"
UNREFERENCED_FILES = "Unreferenced Files"
RAW_FILES = "Raw Files"
ADGC_FORMS = "AdGCForms"

games = [US, JP, EU, BETA, FAMILY]


def _build_data_file_path(game=US):
    return "\\".join([DATA, game, FILE_NAMES])


def _build_outputs_file_path(game, file_type=REFERENCED_FILES):
     return "\\".join([OUTPUTS, game, file_type])


def open_filenames_json(game=US):
    if game not in games:
        raise ValueError("Invalid directory provided.")
    with open(_build_data_file_path(game), "r") as f:
            data = f.read()

    return json.loads(data)


def generate_path_summary(p):
    # want to do something like generate a text file for Referenced Files, and maybe print the offsets/parts that were extracted or somethign along those lines
    pass


def subdirs(path):
    for entry in os.scandir(path):
        if entry.is_dir():
            yield entry


def address_lookup_dict(json_data):
    lookup = {entry["Location"]: entry for entry in json_data}
    return lookup


def check_filenames(game, file_type=REFERENCED_FILES):
    json_data = open_filenames_json(game)
    lookup_dict = address_lookup_dict(json_data)
    updated = False

    for sub_dir in subdirs(_build_outputs_file_path(game, file_type)):
        normalized_dir_name = sub_dir.name.lstrip('0')

        # if it is default and/or in json, it should be the same
        default_file_name = f"{_build_outputs_file_path(game, file_type)}\{sub_dir.name}\{sub_dir.name}.dat"

        # if the file doesn't exist, it's been renamed
        if not os.path.exists(default_file_name):
            dat_file_exists = False
            location = None

            for entry in os.scandir(sub_dir.path):
                if entry.is_file() and entry.name.endswith('.dat'):
                    dat_file_exists = True

                    location = entry.name.split('.')[0].lstrip('0')
        
                    if location in lookup_dict:
                        # THIS ASSUMES THAT THE DAT FILE IN THE FOLDERS WILL ALWAYS STAY AS THE ADDRESS (which I need to change in the file to format it accordingly)
                        lookup_dict[location]["Name"] = sub_dir.name
                        updated = True
                        break
            if not dat_file_exists:
                print(f"No .dat file found in directory: {sub_dir.name}")
    if updated:
        save_json_file(_build_data_file_path(game), json_data)
        print("JSON file has been updated.")
    else:
        print("No updates were necessary.")

def save_json_file(json_path, data):
    with open(json_path, 'w') as file:
        json.dump(data, file, indent=4)

if __name__ == "__main__":
    check_filenames(US)


# todo: add file type (referenced / unreferenced etc to allow for naming any/all)
# @dataclass
# class FileNameEntry:
#     Location: str
#     Name: str
#     Format: str | None
