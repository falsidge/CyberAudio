import io
import sys
import pathlib
import glob
import argparse

parser = argparse.ArgumentParser(description='Extracts opuspak files. Can also extract opus from the wems in opuspak')
parser.add_argument("path", metavar="file/folder", type=str, nargs="+", help="the file or folder to extract. supports globbing (*.opuspak)")
parser.add_argument("--out","-o", type=str, nargs="?", help="the folder to output to. will create path if does not exist")
parser.add_argument('--singlefolder',"-s", dest='single', action='store_true',
                    help='Puts all the files in a single out folder. (default: create folder in same folder as file) ')
parser.add_argument('--opus',"-op", dest='opus', action='store_true',
                    help='Extracts the opus file from the wem')
parser.add_argument('--verbose',"-v", dest='verbose', action='store_true',
                    help='Turn on verbose logging')
parser.add_argument('--pattern', "-p",
                    help='Pattern for filename ({file_name}_{total_index}_{index}.wem)')
args = parser.parse_args()

paths = []
for j in args.path:
    paths.extend(glob.glob(j))
new_paths = []
for path in paths:
    tp = pathlib.Path(path)
    if tp.is_dir():
        new_paths.extend(glob.glob(path+"/*.opuspak"))
    else:
        new_paths.append(path)

class WiseHeader:
    def __init__(self, f = None, offset = 0):
        if f:
            self.parse(f, offset)
    
    def parse(self, f : io.TextIOWrapper, file_offset = 0):
        f.seek(file_offset)
        assert f.read(4) == b"RIFF", "RIFF MAGIC header not found"
        f.read(4) # RIFF Size. Very far off 
        assert f.read(4) == b"WAVE", "WAVE header not found"

        offset = 0xc + file_offset
        
        while True:
            header_type = f.read(4)
            buf = f.read(4)
            header_size = int.from_bytes(buf, 'little')
            if len(buf) < 4:
                break

            offset += 0x08
            if header_type == b"fmt ":
                self.fmt_offset = offset
                self.fmt_size = header_size
            elif header_type == b"data":
                self.data_offset = offset
                self.data_size = header_size
                break # read only one fmt and data
            offset += header_size
            f.seek(offset)
        f.seek(self.fmt_offset)
        self.format = int.from_bytes(f.read(2), 'little')
        self.channels = int.from_bytes(f.read(2), 'little')
        self.sample_rate = int.from_bytes(f.read(4), 'little')
        self.average_bps = int.from_bytes(f.read(4), 'little')
        self.block_align = int.from_bytes(f.read(2), 'little')
        self.bits_per_sample = int.from_bytes(f.read(2), 'little')
        self.extra_size = int.from_bytes(f.read(2), 'little')
        f.read(2)
        self.channel_layout = int.from_bytes(f.read(4), 'little')
        if (self.channel_layout & 0xFF) == self.channels:
            self.channel_type = (self.channel_layout >> 8 & 0x0f)
            self.channel_layout >>= 12

        if self.format == 0xFFFF:
            self.codec = "VORBIS"
        else:
            self.codec = "OPUSCPR"

    def __str__(self):
        return f'''Codec: {self.codec} (Format: {hex(self.format)})
Channels: {self.channels}
Sample Rate: {self.sample_rate}
Average BPS: {self.average_bps}
Block Align: {self.block_align}
Bits per sample: {self.bits_per_sample}
Extra size: {self.extra_size}'''

class OggOpusHeader:
    def __init__(self, f = None, offset = 0):
        if f:
            self.parse(f, offset)
        
    def parse(self, f, offset = 0):
        f.seek(offset)
        assert f.read(4) == b"OggS", "OggS header not found"
        # f.read(1) # stream_structure_version
        # f.read(1) # header_type_flag
        # f.read(8) # absolute_granule position
        # f.read(4) # stream serial number
        # f.read(4) # page sequence no
        # f.read(4) # crc32
        f.seek(26 + offset)
        self.page_segments = ord(f.read(1)) # page segments
        self.segment_table = f.read(self.page_segments)
        self.header_size = 27 + self.page_segments
        self.page_size = sum(self.segment_table)

def decode_opus_cpr(f, verbose=False):
    ww = WiseHeader(f)
    if verbose: print(ww)
    offsets = []

    assert ww.codec == "OPUSCPR"
    if ww.codec == "OPUSCPR":
        file_offset = 0
        offset = ww.data_offset
        while True:
            offsets.append((file_offset, offset))
            if verbose: print("Found data at Offset: ", offset)
            try:
                while True:
                    oo = OggOpusHeader(f, offset)
                    offset += oo.page_size + oo.header_size
            except AssertionError:
                file_offset = offset
                try:
                    ww = WiseHeader(f, offset)
                    offset = ww.data_offset
                except AssertionError: #EOF or RIFF header not found
                    break
        return offsets
    else:
        ... # VORBIS

total_i = 0
out_folder = None
if args.out:
    out_folder = pathlib.Path(args.out)
    out_folder.mkdir(parents=True, exist_ok=True)

for file_name in new_paths:
    print(file_name)
    
    pathname = pathlib.Path(file_name)
    par = None
    if args.out:
        par = out_folder
    else:
        par = pathname.parent
    
    fold = None
    if args.single:
        if args.out:
            fold = out_folder
        else:
            fold = par / "out"
    else:
        fold = par / pathname.stem
    fold.mkdir(parents=True,exist_ok=True)

    with open(pathname, "rb") as in_file:
        try:
            offset_list = decode_opus_cpr(in_file, args.verbose)
        except AssertionError:
            print("ERROR not opuspak file")
        
        for i,offsets in enumerate(offset_list) :

            out_file_name = ""
            if args.pattern:
                out_file_name = args.pattern.format(index=i,total_index=total_i,file_name=pathname.stem)
            else:
                if args.single:
                    out_file_name = str(total_i)
                else:
                    out_file_name = str(i)
                if args.opus:
                    out_file_name += ".ogg"
                else:
                    out_file_name += ".wem"
            
            if args.opus:
                offset = offsets[1]
            else:
                offset = offsets[0]
            end_offset = offset_list[i+1][0] - offset if i+1 < len(offset_list) else None
            in_file.seek(offset)

            with open(fold / out_file_name,'wb' ) as f:
                f.write(in_file.read(end_offset))
            
            total_i += 1