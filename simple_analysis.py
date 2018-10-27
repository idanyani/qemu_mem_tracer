import subprocess
import os
import os.path
import time
import argparse
import struct
import signal

TRACE_RECORD_SIZE = 0x20
VIRT_ADDR_OFFSET = 0x10
ADDR_SIZE = 8
INT_SIZE = 4
OUR_BUF_SIZE = 20000 * INT_SIZE

parser = argparse.ArgumentParser(description='simple analysis tool')
parser.add_argument('pipe_name', type=str,
                    help='The path of the FIFO that QEMU writes traces into')
parser.add_argument('our_buf_addr', type=lambda arg: int(arg, 0),
                    help='The address of our buffer (in the test code)')

args = parser.parse_args()
print(args.pipe_name, args.our_buf_addr)

our_buf_end_addr = args.our_buf_addr + OUR_BUF_SIZE




print('\n'
      '----------------------------------------------\n'
      'It seems that python is too slow for this job.\n'
      '----------------------------------------------\n')
exit()




def handle_end_analysis_signal(signum, frame):
    print(f'num_of_mem_accesses_by_user_code:              ?\n'
          f'num_of_mem_accesses_by_kernel_code:            ?\n'
          f'num_of_mem_accesses_by_CPL3_to_cpu_entry_area: ?\n'
          f'num_of_mem_accesses:                           {num_of_mem_accesses}\n'
          f'num_of_mem_accesses_to_our_buf:                {num_of_mem_accesses_to_our_buf}')
    

signal.signal(signal.SIGUSR1, handle_end_analysis_signal)

# uint64_t num_of_mem_accesses_by_user_code = 0; 
# uint64_t num_of_mem_accesses_by_kernel_code = 0; 
# uint64_t num_of_mem_accesses_by_CPL3_to_cpu_entry_area = 0; 
# uint64_t num_of_mem_accesses_to_our_buf = 0; 
num_of_mem_accesses_to_our_buf = 0
num_of_mem_accesses = 0
with open(args.pipe_name, 'rb') as pipe:
    while True:
        trace_record = pipe.read(TRACE_RECORD_SIZE)
        num_of_mem_accesses += 1
        virt_addr_bytes = trace_record[VIRT_ADDR_OFFSET:][:ADDR_SIZE]
        # comment the next line, and python might keep up with QEMU, but my
        # guess is that even without it, it causes QEMU to block on writing to
        # the FIFO...
        virt_addr = struct.unpack('<Q', virt_addr_bytes)[0] 
        # print(hex(virt_addr))
        # if args.our_buf_addr <= virt_addr < our_buf_end_addr:
        #     num_of_mem_accesses_to_our_buf += 1



