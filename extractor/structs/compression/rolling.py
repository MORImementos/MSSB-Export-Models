from __future__ import annotations
from structs.compression import CompressionData
from typing import NamedTuple

class RollingDecompressor():
    MAX_SIZE = 4_000_000 # 4 mb max size

    def __init__(self, buffer:bytearray, lookback_bit_count:int, repetition_bit_count:int) -> None:
        self.bytes_to_decompress = bytearray(buffer)
        self.lookback_bit_count = lookback_bit_count
        self.repetition_bit_count = repetition_bit_count
        self.__reset_buffer()
        self.outputdata = bytearray()
    
    def __read_int(self)->int:
        if(self.__byte_index + 3 >= len(self.bytes_to_decompress)):
            raise ValueError("No more ints to read")

        value = int.from_bytes(self.bytes_to_decompress[self.__byte_index : self.__byte_index + 4], 'big')

        self.__byte_index += 4

        return value

    def __len__(self):
        return 2**32-1

    def __read_bits(self, bit_count:int):
        # if enough bits in buffer
        if bit_count <= self.__bits_in_buffer:
            # read the bits from the low end
            value = self.__bit_buffer & (2**bit_count - 1)
            # rotate out the bits
            self.__bit_buffer >>= bit_count
            # remove the count of those bits
            self.__bits_in_buffer -= bit_count
        else:
            # else not enough bits,
            # we need a new int
            new_buffer = self.__read_int()
            
            new_bits_needed = bit_count - self.__bits_in_buffer
            # the bits remaining in the buffer will be the high bits for the output data
            value = self.__bit_buffer << new_bits_needed

            self.__bits_in_buffer = 32 - new_bits_needed
            # the bits we're using from the new data will become the low bits of the output data
            value |= (new_buffer & (0xffffffff >> self.__bits_in_buffer))
            # rotate out the data
            self.__bit_buffer = new_buffer >> new_bits_needed

        return value
    
    def __reset_buffer(self):
        self.__byte_index = 0
        self.__bit_buffer = 0
        self.__bits_in_buffer = 0

    def decompress(self, size:int):
        while len(self.outputdata) < size and len(self.outputdata) < RollingDecompressor.MAX_SIZE:
            # returns 0 or 1
            head_bit = self.__read_bits(1)
            if head_bit == CompressionData.REPETITION_DATA:

                far_back = self.__read_bits(self.lookback_bit_count)
                
                repetitions = self.__read_bits(self.repetition_bit_count) + 2

                if far_back > len(self.outputdata):
                    # if there is a sequence requested to be read that is before the start of the array, then stop
                    raise ValueError("Invalid data, received too far lookback")
                while repetitions != 0:
                    self.outputdata.append(self.outputdata[-1 - far_back])
                    repetitions -= 1
            else:
                self.outputdata.append(self.__read_bits(8))

        return self.outputdata
    
    class RollingDecompressorSlice:
        def __init__(self, d: RollingDecompressor, s:slice) -> None:
            # we should only get to this point if stop is not defined
            self.__rolling_decompressor = d
            self.__slice = s
        
        def __getitem__(self, key):
            if isinstance(key, int):
                assert(key >= 0)
                
                self.__rolling_decompressor.decompress(max(self.__slice.start, self.__slice.stop))
                return self.__rolling_decompressor.outputdata[self.__slice.start:self.__slice.stop:self.__slice.step][key]
            
            elif isinstance(key, slice):
                assert(key.step == None or key.step > 0)
                assert(key.start == None or key.start >= 0)
                assert(key.stop == None or key.stop >= 0)

                my_start   = self.__slice.start if self.__slice.start != None else 0
                my_step    = self.__slice.step  if self.__slice.step  != None else 1

                this_start = key.start if key.start != None else 0
                this_step  = key.step  if key.step  != None else 1

                if key.stop != None: # stop defined

                    total_start = this_start + my_start
                    total_end = total_start + max((key.stop - this_start) * my_step, 0)
                    self.__rolling_decompressor.decompress(max(total_start, total_end))

                    return self.__rolling_decompressor.outputdata[total_start : total_end : this_step * my_step]
            
                elif key.stop == None: # no stop defined
                    
                    return RollingDecompressor.RollingDecompressorSlice(self.__rolling_decompressor, slice(my_start + (this_start * this_step), None, this_step*my_step))
                
            raise ValueError(f"Unexpected key: {type(key)}: {key}")

        def __len__(self):
            return len(self.__rolling_decompressor)
                    
    def __getitem__(self, key):
        if isinstance(key, int):
            assert(key >= 0)
            
            self.decompress(key+1)
            return self.outputdata[key]

        elif isinstance(key, slice):
            assert(key.step == None or key.step > 0)
            assert(key.start == None or key.start >= 0)
            assert(key.stop == None or key.stop >= 0)

            if key.stop != None: # stop defined
                assert(key.stop >= 0)
                
                this_start = key.start if key.start != None else 0
                
                self.decompress(max(this_start, key.stop))
                return self.outputdata[this_start:key.stop:key.step] # return data between start and stop
                        
            return RollingDecompressor.RollingDecompressorSlice(self, key) # if no stop defined
        raise ValueError(f"Unexpected key: {type(key)}: {key}")
    