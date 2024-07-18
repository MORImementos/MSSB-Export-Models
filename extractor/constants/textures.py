VALID_IMAGE_FORMATS = {
    0: "I4",
    1: "I8",
    2: "IA4",
    3: "IA8",
    4: "RGB565",
    5: "RGB5A3",
    6: "RGBA32",
    8: "C4",
    9: "C8",
    0xa: "C14X2",
    0xe: "CMPR"
}

REV_VALID_IMAGE_FORMATS = {v: k for k, v in VALID_IMAGE_FORMATS.items()}

CMPR_BLOCK_SIZE = 8
