from compression_structs import CompressionData
from __future__ import annotations
from typing import NamedTuple

class ArchiveDecompressor:
    def __init__(self, buffer:bytearray, lookback_bit_count:int, repetition_bit_count:int, original_size:int=None) -> None:
        self.bytes_to_decompress = bytearray(buffer)
        self.lookback_bit_count = lookback_bit_count
        self.repetition_bit_count = repetition_bit_count
        self.original_size = original_size
        self.__reset_buffer()
    
    @property
    def compressed_size(self):
        return self.__byte_index

    def __read_int(self)->int:
        if(self.__byte_index + 3 >= len(self.bytes_to_decompress)):
            raise ValueError("No more ints to read")

        value = int.from_bytes(self.bytes_to_decompress[self.__byte_index : self.__byte_index + 4], 'big')

        self.__byte_index += 4

        return value

    def __has_bits(self):
        if self.__byte_index >= len(self.bytes_to_decompress) - 1:
            return self.__bit_buffer != 0
        return True

    def __should_keep_decompressing(self, size:int):
        if self.original_size != None:
            return size < self.original_size
        return self.__has_bits()

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

    def is_valid_decompression(self) -> bool:
        if self.lookback_bit_count == 0 and self.repetition_bit_count == 0:
            return True
        
        self.__reset_buffer()

        written_bit_count = 0

        while self.__should_keep_decompressing(written_bit_count):
            # returns 0 or 1
            head_bit = self.__read_bits(1)
            if head_bit == 0:                
                far_back = self.__read_bits(self.lookback_bit_count)
                repetitions = self.__read_bits(self.repetition_bit_count) + 2
                if far_back >= written_bit_count:
                    # if there is a sequence requested to be read that is before the start of the array, then stop
                    return False
                written_bit_count += repetitions
            else:
                self.__read_bits(8)
                written_bit_count += 1
        return True
    
    def get_compression_instructions(self) -> list[CompressionData]:
        if self.lookback_bit_count == 0 and self.repetition_bit_count == 0:
            return []
        
        self.__reset_buffer()

        written_bit_count = 0
        instructions = []
        while self.__should_keep_decompressing(written_bit_count):
            # returns 0 or 1
            head_bit = self.__read_bits(1)
            if head_bit == 0:                
                far_back = self.__read_bits(self.lookback_bit_count)
                length = self.__read_bits(self.repetition_bit_count) + 2
                if far_back > written_bit_count:
                    # if there is a sequence requested to be read that is before the start of the array, then stop
                    raise ValueError("Invalid data, received too far lookback")

                instructions.append(CompressionData(flag=head_bit, look_back=far_back, length=length))
            else:
                instructions.append(CompressionData(flag=head_bit, data=self.__read_bits(8)))
                length = 1

            written_bit_count += length
        return instructions

    def decompress(self):
        if self.lookback_bit_count == 0 and self.repetition_bit_count == 0:
            if self.original_size != None:
                return self.bytes_to_decompress[:self.original_size]
            else:
                return bytearray()
        
        self.__reset_buffer()

        final_data = bytearray()

        while self.__should_keep_decompressing(len(final_data)):
            # returns 0 or 1
            head_bit = self.__read_bits(1)
            if head_bit == CompressionData.REPETITION_DATA:

                far_back = self.__read_bits(self.lookback_bit_count)
                
                repetitions = self.__read_bits(self.repetition_bit_count) + 2

                if far_back > len(final_data):
                    # if there is a sequence requested to be read that is before the start of the array, then stop
                    raise ValueError("Invalid data, received too far lookback")
                while repetitions != 0:
                    final_data.append(final_data[-1 - far_back])
                    repetitions -= 1
            else:
                final_data.append(self.__read_bits(8))

        return final_data

class ArchiveCompressor:
    class CompressedBufferHelper:
        ORIGINAL_DATA = 1
        REPETITION = 0

        def __init__(self) -> None:
            self.out_values = []
            self.buffer = 0
            self.buffer_bit_count = 0

        def write_original_data(self, data:int):
            assert(data >= 0)
            assert(data < 2**8)
            
            self.add_bits(self.ORIGINAL_DATA, 1)
            self.add_bits(data, 8)
        
        def write_repetition(self, lookback:int, lookback_size:int, repetitions:int, repetitions_size:int):
            assert(lookback >= 0)
            assert(lookback < 2**lookback_size)
            
            assert(repetitions >= 0)
            assert(repetitions < 2**repetitions_size)

            self.add_bits(self.REPETITION, 1)
            self.add_bits(lookback, lookback_size)
            self.add_bits(repetitions, repetitions_size)

        def add_bits(self, value:int, bit_count:int):
            assert(value & (2**bit_count -1) == value) # make sure the bit count convers all bits with value

            if self.buffer_bit_count + bit_count <= 32:
                self.buffer |= value << self.buffer_bit_count
                self.buffer_bit_count += bit_count
                if self.buffer_bit_count == 32:
                    self.out_values.append(self.buffer)

                    self.buffer = 0
                    self.buffer_bit_count = 0
            else:
                remaining_bits = 32 - self.buffer_bit_count
                # the remaining bits will get the high bits of the value
                upper_value = value >> (bit_count - remaining_bits)
                lower_value = value & (2**(bit_count - remaining_bits) - 1)

                self.buffer |= upper_value << self.buffer_bit_count

                self.out_values.append(self.buffer)

                self.buffer = lower_value
                self.buffer_bit_count = (bit_count - remaining_bits)


        def flush(self):
                if self.buffer_bit_count > 0:
                    self.out_values.append(self.buffer)
                    self.buffer = 0
                    self.buffer_bit_count = 0
        
        def to_byte_array(self) -> bytearray:
            b = bytearray()
            for i in self.out_values:
                b.extend(i.to_bytes(4, 'big', signed=False))
            return b
        
    class SublistDefinition(NamedTuple):
        offset:int
        length:int

    def __init__(self, data:bytearray, lookback_bit_size:int, repetition_bit_size:int) -> None:
        self.data = bytearray(data)
        self.lookback_bit_size = lookback_bit_size
        self.repetition_bit_size = repetition_bit_size

        self.cached_data = {}

    # function to help get the count of the matching characters
    def __length_of_match(data:bytearray, sublist:bytearray):
        count = 0
        while count < len(sublist) and (sublist[count] == data[count]):
            count += 1
        return count

    def __largest_sublist_cachedsearch(self, sub_start: int, sub_stop: int, sliding_window_start_index: int, sliding_window_stop_index: int, look_ahead_size: int, min_sublist_size:int):
        sliding_window_size = sliding_window_stop_index - sliding_window_start_index

        sublist = self.data[sub_start:sub_stop]
        
        first_char = sublist[0]

        cached_ind_set:list = self.cached_data.get(first_char, None)
        if cached_ind_set != None:
            to_remove = []
            match_length = -1
            match_index = -1

            for cached_ind in cached_ind_set:
                if cached_ind < (sub_start - sliding_window_size):
                    to_remove.append(cached_ind)
                    continue

                len_of_match = ArchiveCompressor.__length_of_match(self.data[cached_ind:cached_ind+sub_stop-sub_start], sublist)

                if len_of_match > match_length:
                    match_length = len_of_match
                    match_index = cached_ind
                
            cached_ind_set.append(sub_start)
            for rem in to_remove:
                cached_ind_set.remove(rem)

            for sublist_index in range(1, match_length):
                char = sublist[sublist_index]
                char_ind = sub_start + sublist_index
                
                cached_ind_set = self.cached_data.get(char, None)
                if cached_ind_set == None:
                    cached_ind_set = set()
                    self.cached_data[char] = cached_ind_set

                cached_ind_set.append(char_ind)
            
            if match_length >= min_sublist_size:
                return self.SublistDefinition(match_index, match_length)
        else:
            self.cached_data[first_char] = [sub_start]

        return None
    
    def __largest_sublist_bytesearch(self, sub_start: int, sub_stop: int, sliding_window_start_index: int, sliding_window_stop_index: int, look_ahead_size: int, min_sublist_size:int) -> SublistDefinition:

        sub_start                   = max(0, sub_start)
        sliding_window_start_index  = max(0, sliding_window_start_index)

        dat_len                     = len(self.data)

        sub_stop                    = min(dat_len, sub_stop)
        sliding_window_stop_index   = min(dat_len, sliding_window_stop_index)

        sublist = self.data[sub_start:sub_stop]

        
        # -------- bytearray built-in find ----------- 2.5 seconds

        # size of sliding window | first offset that is unacceptable
        unusable_lookahead_ind = sliding_window_stop_index - sliding_window_start_index
        # cut sliding window and lookahead to search in
        sliding_window_and_lookahead = self.data[sliding_window_start_index : sliding_window_stop_index + look_ahead_size]
        # only look for sublists for sizes above min_sublist_size
        while len(sublist) >= min_sublist_size:
            # finds first instance, returns >= 0 if found, else -1
            ind = sliding_window_and_lookahead.find(sublist)
            # checks to see if any found and first instance is not in the lookahead
            if 0 <= ind < unusable_lookahead_ind:
                # return offset into large array
                return self.SublistDefinition(sliding_window_start_index + ind, len(sublist))
            # cut down list to look for smaller sublist
            sublist = sublist[:-1]
        # nothing found
        return None
        
        # -----------------------------------

    def __largest_sublist_search(self, sub_start: int, sub_stop: int, sliding_window_start_index: int, sliding_window_stop_index: int, look_ahead_size: int, min_sublist_size:int) -> SublistDefinition:

        sub_start                   = max(0, sub_start)
        sliding_window_start_index  = max(0, sliding_window_start_index)

        dat_len                     = len(self.data)

        sub_stop                    = min(dat_len, sub_stop)
        sliding_window_stop_index   = min(dat_len, sliding_window_stop_index)

        sublist = self.data[sub_start:sub_stop]
        
        # ----------------- Iterate ------------------ 30 seconds
        # max_length = len(sublist)
        # best_index = -1
        # best_length = -1

        # # walk through every index in the sliding window
        # for compare_index in range(sliding_window_start_index, sliding_window_stop_index):

        #     # check to see how many values in the sublist match at this index
        #     sub_count = 0
        #     while sub_count < max_length and self.data[compare_index + sub_count] == sublist[sub_count]:
        #         sub_count += 1
            
        #     # record it if it was better than the previous best found
        #     if sub_count > best_length:
        #         best_index = compare_index
        #         best_length = sub_count

        # # only return sublist if it meets the min sublist requirement
        # if best_length >= min_sublist_size:
        #     return self.SublistDefinition(offset=best_index, length=best_length)
        # return None
        # -----------------------------------

        # ----------------- look for first char ------ 13 seconds
        sliding_window = self.data[sliding_window_start_index:sliding_window_stop_index]

        first_char = sublist[0]
        # retrive the indices of all times the first character of the sublist exists in the sliding window
        all_first_char_inds = [ind for (ind, v) in enumerate(sliding_window) if v == first_char]


        # loop over the indices, and figure out how many characters match the sublist
        all_lengths = [(ArchiveCompressor.__length_of_match(self.data[sliding_window_start_index + ind : sliding_window_start_index + ind + len(sublist)], sublist), ind) for ind in all_first_char_inds]
        
        # if no matches are found, return None
        if len(all_lengths) == 0:
            return None

        # have to choose 1 of the found, choose the first instance of longest length
        best_length = max([x[0] for x in all_lengths])

        # if best length isn't long enough, return none
        if best_length < min_sublist_size:
            return None

        best_index = min([x[1] for x in all_lengths if x[0] == best_length])
        return self.SublistDefinition(sliding_window_start_index + best_index, best_length)
        # -----------------------------------

    def compress(self) -> bytearray:
        self.cached_data    = {}
        data_index          = 0
        look_back_size      = 2**self.lookback_bit_size
        repetitions_size    = 2**self.repetition_bit_size + 1

        buffer = self.CompressedBufferHelper()
        while data_index < len(self.data):
                        
            longest_match = self.__largest_sublist_bytesearch(
                    sub_start                   = data_index,
                    sub_stop                    = data_index + repetitions_size,
                    min_sublist_size            = 2,

                    sliding_window_start_index  = data_index - look_back_size,
                    sliding_window_stop_index   = data_index,
                    look_ahead_size             = repetitions_size,
                )

            if longest_match != None:
                #longest_match.offset is just an index into the array, we actually want to have it become a lookback from the data_index
                buffer.write_repetition(
                    lookback            = data_index - longest_match.offset - 1, 
                    repetitions         = longest_match.length - 2, 
                    lookback_size       = self.lookback_bit_size, 
                    repetitions_size    = self.repetition_bit_size,
                )
                data_index += longest_match.length
            else:
                buffer.write_original_data(self.data[data_index])
                data_index += 1
        
        buffer.flush()
        return buffer.to_byte_array()

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
    