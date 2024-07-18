from os.path import dirname, join, exists
from structs import COL
from helpers import get_parts_of_file, save_to_json
import os
from pathlib import Path

def main():
    file_name = r"E:\MSSB\MSSB-Export-Models\extractor\data\test\06CFD000.dat"
    # file_name = "extractor/outputs/US/Referenced Files/Mario Stadium/Mario Stadium.dat"
    with open(file_name, 'rb') as f:
        file_bytes = f.read()

    parts = get_parts_of_file(file_bytes)
    output_directory = dirname(file_name)
    
    for part_index in range(len(parts)):
        start_offset = parts[part_index]
        try:
            export_collision(file_bytes, output_directory, start_offset)
        except Exception as e:
            print(f"Error processing part {part_index}: {e}")
            continue

    # export_collision(file_bytes, output_directory, start_offset=parts[2], end_offset=parts[3] - 1)
def log_to_file(log_file, message):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

def export_collision(file_bytes: bytearray, output_directory: str, start_offset: int):
    log_file = join(output_directory, f"collision_export_log_{hex(start_offset)}.txt")
    if os.path.exists(log_file):
        os.remove(log_file)
    
    try:
        collision = COL.Collision(file_bytes, start_offset)
        save_to_json(collision.to_dict(), Path(output_directory) / f"{hex(start_offset)}.json")
        print(f"    Successfully processed collision data at offset {hex(start_offset)}")    
    except Exception as e:
        log_to_file(log_file, f"Error: {str(e)}")
        print(f"    Error processing collision data at offset {hex(start_offset)}")

if __name__ == "__main__":
    main()
