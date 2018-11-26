#!/usr/bin/env python3.7

import argparse
import subprocess

# orenmn:
#   I used only printable characters in the communication over the serial port
#   in order to avoid using serial control characters (which would mess things up).

SYNC_BYTES = b'serial sync\n'

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        description='Write the sync bytes to the serial port. '
                    'Then, for each of the 2 received executables, write to the '
                    'serial port: the executable\'s size, checksum and contents.'
                    'For an empty executable, just write to the seiral port 0. '
                    '(I.e. it\'s size is zero.')
    parser.add_argument('executable1_path', type=str)
    parser.add_argument('executable2_path', type=str)
    parser.add_argument('serial_port_path', type=str)
    return parser.parse_args()

def get_16_bit_checksum(file_contents):
    return sum(file_contents) & 0xffff

def get_bytes_to_write_file_to_serial(file_path):
    with open(file_path, 'rb') as f:
        file_contents = f.read()

    file_size = len(file_contents)
    if file_size == 0:
        return b'0\n'

    checksum = get_16_bit_checksum(file_contents)

    file_contents_as_hex = file_contents.hex()
    assert(len(file_contents_as_hex) == file_size * 2)
    
    file_contents_as_hex_for_serial = ''
    for i in range(0, len(file_contents_as_hex), 2):
        file_contents_as_hex_for_serial += f'{file_contents_as_hex[i:i+2]}\n'
    
    return (f'{file_size}\n'
            f'{checksum}\n'
            f'{file_contents_as_hex_for_serial}'.encode('ascii'))

if __name__ == '__main__':
    args = parse_cmd_args()

    with open(args.serial_port_path, 'wb') as f:
        f.write(SYNC_BYTES)
        f.write(get_bytes_to_write_file_to_serial(args.executable1_path))
        f.write(get_bytes_to_write_file_to_serial(args.executable2_path))

