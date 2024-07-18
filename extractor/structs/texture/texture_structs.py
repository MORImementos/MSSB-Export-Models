from dataclasses import dataclass
from PIL.Image import Image, new as new_Image
from helpers import ensure_dir, write_text, dirname
from os.path import join

@dataclass
class ExtractedTexture:
    img:Image
    img_format:str

class ExtractedTextureCollection:
    def __init__(self, images : list[ExtractedTexture]) -> None:
        self.images = images

    def generate_outputs(self, path:str=None) -> list[tuple[str, ExtractedTexture]]:
        outputs = []
        for index, tex in enumerate(self.images):
            file_name = f"{index}.png"
            if path != None:
                file_name = join(path, file_name)
            outputs.append((file_name, tex))
        return outputs

    def write_images_to_folder(self, path:str = None):
        for file_name, tex in self.generate_outputs(path):
            ensure_dir(dirname(file_name))
            tex.img.save(file_name)

    def write_mtl_file(self, output_path:str, img_file_path:str):
        mtl_contents = self.get_mtl_file(img_file_path)
        write_text(mtl_contents, output_path)

    def get_mtl_file(self, img_files_path:str = None):
        output = ""
        for i, (path, tex) in enumerate(self.generate_outputs(img_files_path)):
            path:str

            path = path.replace("\\", "\\\\")

            output += (f"newmtl mssbMtl.{i}\n")
            output += (f"map_Kd {path}\n")
            output += (f"# Height: {tex.img.height}, Width: {tex.img.width}, Format: {tex.img_format}\n")
            output += ("\n")
    
        return output

    
# @dataclass
# class RGBA8:
#     # each is uint8_t
#     r: int
#     g: int
#     b: int
#     a: int

# class DXT1Block:
#     color1: int # u16
#     color2: int # u16
#     lines: list # u8[4]


def dummyImage():
    return new_Image('1', (1, 1))

