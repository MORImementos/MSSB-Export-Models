from __future__ import annotations
from typing import NamedTuple, Union
from struct import pack, unpack, calcsize
from os.path import dirname, exists
from os import makedirs
from structs import DBI

class CompressionData(NamedTuple):
    ORIGINAL_DATA = 1
    REPETITION_DATA = 0
    flag: int = None
    data: int = None
    look_back: int = None
    length: int = None
    
    def is_original_data(self):
        return self.flag == self.ORIGINAL_DATA
    
    def is_repeated_data(self):
        return self.flag == self.REPETITION_DATA

    def __str__(self):
        if self.flag == self.ORIGINAL_DATA:
            return f"OriginalData({self.data:02x})"
        elif self.flag == self.REPETITION_DATA:
            return f"RepetitionData(look_back={self.look_back}, length={self.length})"
        else:
            return ""
        
    def __repr__(self) -> str:
        return self.__str__()
   
class DataEntry(DBI):
    DATA_FORMAT = ">xxBBIII"

    @property
    def footer_size(self):
        base = 0x800
        size = self.disk_location + self.compressed_size
        size %= base
        if size == 0:
            footer = 0
        else:
            footer = base - size
        
        return footer

    def __init__(self, b: bytearray, offset:int, file="") -> None:

        self.file = file
        self.repetition_bit_size,\
        self.lookback_bit_size,\
        self.original_size,\
        self.disk_location,\
        self.compressed_size =\
        self.parse_bytes(b, offset)

        self.compression_flag = self.original_size >> 28

        self.original_size &= 0xf_ff_ff_ff

        self.output_name = f"{self.file} {self.lookback_bit_size:02x}{self.repetition_bit_size:02x} {self.disk_location:08x}.dat"
        
        self.reset_output_name()

    def reset_output_name(self):
        self.output_name = f"{self.file} {self.lookback_bit_size:02x}{self.repetition_bit_size:02x} {self.disk_location:08x}.dat"

    def __str__(self) -> str:
        s = ""
        s += f'File:            {self.file}\n'
        s += f'Output Name:     {self.output_name}\n'
        s += f'Lookback bits:   0x{self.lookback_bit_size:02x}\n'
        s += f'Repetition bits: 0x{self.repetition_bit_size:02x}\n'
        s += f'Original Size:   0x{self.original_size:x}\n'
        s += f'Disk Location:   0x{self.disk_location:08x}\n'
        s += f'Compressed Size: 0x{self.compressed_size:x}\n'
        s += f'Compressed Flag: {self.compression_flag}\n'
        s += f'Footer Size:     0x{self.footer_size:x}'

        return s
    
    def to_dict(self)->dict:
        return {
            "Input": self.file,
            "Output": self.output_name,
            "lookbackBitSize": self.lookback_bit_size,
            "repetitionBitSize": self.repetition_bit_size,
            "size": self.original_size,
            "offset": self.disk_location,
            "compressedSize": self.compressed_size,
            "compressionFlag": self.compression_flag,
            "footerSize": self.footer_size
        }
    
    def from_dict(d:dict) -> DataEntry:
        data = DataEntry(
            pack(
                DataEntry.DATA_FORMAT, 
                d["repetitionBitSize"], 
                d["lookbackBitSize"], 
                d["size"] | (d["compressionFlag"] << 28), 
                d["offset"], 
                d["compressedSize"]
            ),
            0,
            d["Input"]
        )

        if "Output" in d:
            data.output_name = d["Output"]
        return data
    
    def to_range(self):
        return range(self.disk_location, self.disk_location + self.compressed_size + self.footer_size)

    def __hash__(self) -> int:
        return hash((self.file, self.lookback_bit_size, self.repetition_bit_size, self.original_size, self.disk_location, self.compressed_size, self.compression_flag, self.footer_size))
    
    def equals_besides_filename(self, __o: object):
        if not isinstance(__o, DataEntry):
            return False
        
        return self.lookback_bit_size == __o.lookback_bit_size and self.repetition_bit_size == __o.repetition_bit_size and self.original_size == __o.original_size and self.disk_location == __o.disk_location and self.compressed_size == __o.compressed_size and self.compression_flag == __o.compression_flag and self.footer_size == __o.footer_size

    def __eq__(self, __o: object) -> bool:
        return self.equals_besides_filename(__o) and  self.file == __o.file
    
    def __lt__(self, __o: object):
        if not isinstance(__o, DataEntry):
            return False
        return self.disk_location < __o.disk_location
    
    def __repr__(self) -> str:
        return self.__str__()

class FileCache:
    def __init__(self) -> None:
        self.__byte_cache__ = {}
    
    def __load_file(self, file_name:str):
        assert(file_name not in self.__byte_cache__)

        with open(file_name, "rb") as f:
            self.__byte_cache__[file_name] = f.read()

    def get_file_bytes(self, file_name:str)->bytes:
        if file_name not in self.__byte_cache__:
            self.__load_file(file_name)

        return self.__byte_cache__[file_name]
    
class MultipleRanges:
    def __init__(self) -> None:
        self.__ranges:list[range] = []

    def __overlap(r1:range, r2:range):
        return (
            # if one of the start/stops exists in the other
            (r2.start in r1 or r2.stop in r1) or
            (r1.start in r2 or r1.stop in r2))
    
    def __overlap_or_touch(r1:range, r2:range):
        return (
            # if they overlap on an edge
            r1.start == r2.stop or 
            r2.start == r1.stop or
            MultipleRanges.__overlap(r1, r2))
    
    def __combine_range(r1:range, r2:range)->range:
        if MultipleRanges.__overlap_or_touch(r1, r2):
            all_points = [r1.start, r2.start, r1.stop, r2.stop]
            # if the overlap, just take the max and mins
            return range(min(all_points), max(all_points))
        return None

    def does_overlap(self, r:range):
        return any([MultipleRanges.__overlap(x, r) for x in self.__ranges])

    def add_range(self, r:range):

        overlapping_indices = [i for i, this_range in enumerate(self.__ranges) if MultipleRanges.__overlap_or_touch(r, this_range)]

        if len(overlapping_indices) == 0:
            self.__ranges.append(r)
        else:
            # indices should be next to eachother
            new_range = range(r.start, r.stop)
            for ind in overlapping_indices:
                new_range = MultipleRanges.__combine_range(new_range, self.__ranges[ind])
                assert(new_range != None)

            to_remove_ind = min(overlapping_indices)
            to_remove_count = len(overlapping_indices)
            for _ in range(to_remove_count):
                self.__ranges.pop(to_remove_ind)
            
            self.__ranges.append(new_range)

        self.__ranges.sort(key=lambda x: x.start)

    def __str__(self) -> str:
        return f"{self.__ranges}"
    
    def __repr__(self) -> str:
        return self.__str__()

    def remove_range(self, r:range):
        new_ranges = []

        for old_range in self.__ranges:
            if (old_range.start >= r.start and 
                old_range.stop <= r.stop): # complete overlap, remove
                pass
            elif (old_range.start <= r.start and
                   old_range.stop >= r.start and 
                   old_range.stop <= r.stop): # overlap top
                new_ranges.append(range(old_range.start, r.start))
            elif (old_range.stop >= r.stop and
                   old_range.start >= r.start and 
                   old_range.start <= r.stop): # overlap bottom
                new_ranges.append(range(r.stop, old_range.stop))
            elif (r.start >= old_range.start and 
                  r.stop <= old_range.stop): # overlap middle
                new_ranges.append(range(old_range.start, r.start))
                new_ranges.append(range(r.stop, old_range.stop))            

        self.__ranges = new_ranges

        self.__ranges.sort(key=lambda x: x.start)
    
    def __contains__(self, value):
        if len(self.__ranges) == 0:
            return False 
        # binary search
        max_ind = len(self.__ranges)
        min_ind = 0
        ind = max_ind // 2
        while True:
            this_range = self.__ranges[ind]
            
            if value in this_range:
                return True
            
            if ind == min_ind or ind == len(self.__ranges) - 1:
                return False
            
            if value < this_range.start:
                max_ind = ind
                ind = (ind + min_ind) // 2
            elif value > this_range.stop:
                min_ind = ind
                ind = (ind + max_ind) // 2
            elif value == this_range.stop:
                return False
            
class FingerPrintSearcher:
    def __init__(self, b:bytearray, file_name:str) -> None:
        self.data = b
        self.file_name = file_name

    def search_compression(self, lookback:int, repetitions:int) -> set[DataEntry]:
        to_find = ((repetitions << 8) | lookback).to_bytes(4, 'big')
        d = self.data
        
        found = set()

        ind = d.find(to_find)
        while ind > 0 and len(d) >= DataEntry.SIZE_OF_STRUCT:
            entry = DataEntry(d, ind, self.file_name)            
            # for now it has to be a mult of 2048 bytes, and not 0
            if entry.disk_location % 0x800 == 0 and entry.disk_location != 0:
                found.add(entry)
            
            d = d[ind + len(to_find):]
            ind = d.find(to_find)
        
        return found

    def search_uncompressed(self) -> set[DataEntry]:
        epsilon = 3
        to_find = (0).to_bytes(4, 'big')
        d = self.data
        found = set()

        ind = d.find(to_find)
        while ind >= 0 and len(d[ind:]) >= DataEntry.SIZE_OF_STRUCT:
            entry = DataEntry(d, ind, self.file_name)
            
            # for now it has to be a mult of 2048 bytes, and not 0
            if entry.disk_location % 0x800 == 0 and entry.disk_location != 0:
                # compressed size and entry size should be close to same size, but not 0
                if entry.compressed_size > 0 and entry.original_size > 0 and abs(entry.compressed_size - entry.original_size) <= epsilon:
                    found.add(entry)
            
            d = d[ind + 1:]
            ind = d.find(to_find)
        return found