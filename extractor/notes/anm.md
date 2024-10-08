### ANM
- ANM Header (ANIMBank)
    - 4 bytes: Version number
    - 4 bytes: Offset to sequence array
    - 2 bytes: Bank ID
    - 2 bytes: Number of sequences
    - 2 bytes: Number of tracks
    - 2 bytes: Number of keyframes
    - 4 bytes: User-defined data size
    - 4 bytes: Offset to user data (32-byte aligned)
- Sequence Array
    - Sequence (ANIMSequence)
    - 4 bytes: Offset to sequence name
    - 4 bytes: Offset to track array
    - 2 bytes: Number of tracks
    - 2 bytes: Pad
- Track Array
    - Track (ANIMTrack)
    - 4 bytes: Animation time
    - 4 bytes: Offset to keyframe array
    - 2 bytes: Number of keyframes
    - 2 bytes: Track ID
    - 1 byte: Parameter quantization info
    - 1 byte: Animation type 
        - Bits 7-5: None
        - Bit 4: Matrix
        - Bit 3: Quat rotation
        - Bit 2: Euler rotation
        - Bit 1: scale
        - Bit 0: trans
    - 1 byte: Interpolation type
        - Bit 7: None
        - Bits 6-4: Rotation interpolation type
        - Bits 3-2: Scale interpolation type
        - Bits 1-0: Translation interpolation type

        - Interpolation types:
            - 00: None (eu, sc, tr)
            - 01: Linear (eu, sc, tr)
            - 10: Bezier (eu, sc, tr)
            - 11: Hermite (eu, sc, tr)
            - 100: SQUAD (quat rot only)
            - 101: SQUADEE (quat rot only)
            - 110: SLERP (quat rot only)
    - 1 byte: Pad
- Key Frame Array
    - Keyframe (ANIMKeyFrame)
    - 4 bytes: Time
    - 4 bytes: Offset to setting bank
    - 4 bytes: Offset to interpolation info
        - Bezier
            - 12 bytes: In control
            - 12 bytes: Out control
        - Hermite
            - 12 bytes: In control
            - 12 bytes: Out control
            - 2 bytes: Ease-in
            - 2 bytes: Ease-out
        - SQUAD
            - 16 bytes: In quaternion
            - 16 bytes: Out quaternion
        - SQUADEE
            - 16 bytes: In quaternion
            - 16 bytes: Out quaternion
            - 2 bytes: Ease-in
            - 2 bytes: Ease-out
- Key Frame Setting Bank
- Interpolation Info Bank
- String Bank