class SECTION_TYPES():
    ACT = 0
    GEO = 1
    texture = 2
    collision = 3
    type_count = 4

SECTION_TEMPLATES:dict[str, dict[int, int]] = {
    'Stadium': {
        'stadium': {
            SECTION_TYPES.ACT: 0,
            SECTION_TYPES.GEO: 3,
            SECTION_TYPES.texture: 5,
            SECTION_TYPES.collision: 2
        },
        'backdrop': {
            SECTION_TYPES.ACT: 1,
            SECTION_TYPES.GEO: 4
        }
    }
}
