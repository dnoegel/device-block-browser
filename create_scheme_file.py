#!/usr/bin/env python
# coding:utf-8

import re
import subprocess

import struct
import os
import sys

cmd = """LANG="C" dumpe2fs {device}"""

class BlockDevice(object):
    def __init__(self, device):
        self.device = device

        ## will raise an IOError, if we do not have root privelegs
        with open(self.device, "r"):
                pass

        self._collect_data()
        
    def _collect_data(self):
        self.blocks = []
        
        p = subprocess.Popen(cmd.format(device=self.device), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in p.stdout:
            line = line.decode("utf-8")
            if line.startswith("Block count"):
                self.total_blocks = int(line.split(":")[1].strip())
            elif line.startswith("Free blocks"):
                self.free_blocks = int(line.split(":")[1].strip())
            elif line.startswith("Block size"):
                self.block_size = int(line.split(":")[1].strip())
            elif line.startswith("  Free blocks"):
                self.blocks.append(line.split(":")[1].strip())
            

        self.used_blocks = self.total_blocks - self.free_blocks
    
    def _iter_blocks(self, input_blocks):
        """ Takes a string of comma seperated block ranges and iterates
        over the corresponding blocks
        
        iter_blocks("1-3, 5-6") -> 1 2 3 5 6
        """
        for b in input_blocks.strip().split(", "):
            if "-" in b:
                start, end = b.split("-")
                for i in range(int(start), int(end)+1):
                    yield i
            elif b != "":
                yield int(b)
   
    
    def iter_free_blocks(self):
        """Iterate over the free blocks of a given device"""

        for blocks in self.blocks:
            for b in self._iter_blocks(blocks):
                yield b
    
    def zero_one_block_scheme(self):
        free_blocks = dev.iter_free_blocks()
        next_free = next(free_blocks)
        i = 0
        for b in range(0, self.total_blocks):
            if b == next_free:
                i+=1
                yield 0
                try: 
                    next_free = next(free_blocks)
                except StopIteration:
                    next_free = -1
            else:
                yield 1
                

try:
    dev = BlockDevice(sys.argv[1])
except IndexError:
    print("Device-file as first argument is required")
    sys.exit(1)

   
filename_scheme = "{0}{1}{2}.01"

filename = filename_scheme.format(os.path.basename(sys.argv[1]), "", "")
i = 1
while os.path.exists(filename):
    filename = filename_scheme.format(os.path.basename(sys.argv[1]), "_", i)
    i+= 1

info = struct.pack("16piii", sys.argv[1], dev.block_size, dev.total_blocks, dev.free_blocks)

print("\nWill write to '{0}'.\nHit ENTER to continue".format(filename))
raw_input()

with open(filename, "w") as fh:
    fh.write(info)
    for b in dev.zero_one_block_scheme():
        fh.write(str(b))
        #~ pass
