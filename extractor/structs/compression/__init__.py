from .compression_structs import CompressionData, DataEntry, FileCache, FingerPrintSearcher, MultipleRanges
from .archive import ArchiveCompressor, ArchiveDecompressor
from .rolling import RollingDecompressor

# Define shorter aliases
archive = type('archive', (), {
    'Compressor': ArchiveCompressor,
    'Decompressor': ArchiveDecompressor
})

rolling = type('rolling', (), {
    'Decompressor': RollingDecompressor
})
