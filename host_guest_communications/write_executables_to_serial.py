import argparse
import time
import subprocess

# orenmn:
#   I used only printable characters in the communication over the serial port
#   in order to avoid using serial control characters.

SYNC_BYTES = b'serial sync\n'

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        description='Write the received script\'s size (as a uint32_t), and '
                    'then its contents, to the received serial port.')
    parser.add_argument('executable1_path', type=str)
    parser.add_argument('executable2_path', type=str)
    parser.add_argument('serial_port_path', type=str)
    parser.add_argument('dont_add_communications_with_host_to_workload', type=str)
    return parser.parse_args()

def execute_cmd(cmd):
    print(f'executing cmd: {cmd}')
    subprocess.run(cmd, shell=True, check=True)

def get_16_bit_checksum(file_contents):
    return sum(file_contents) & 0xffff

def get_bytes_to_write_file_to_serial(file_path):
    with open(args.file_path, 'rb') as f:
        file_contents = f.read()

    checksum = get_16_bit_checksum(file_contents)
    file_size = len(file_contents)

    file_contents_as_hex = file_contents.hex()
    assert(len(file_contents_as_hex) == file_size * 2)
    
    file_contents_as_hex_for_serial = ''
    for i in range(0, len(file_contents_as_hex), 2):
        file_contents_as_hex_for_serial += f'{file_contents_as_hex[i:i+2]}\n'
    
    return (f'{checksum}\n'
            f'{file_size}\n'
            f'{file_contents_as_hex_for_serial}'.encode('ascii'))

if __name__ == '__main__':
    args = parse_cmd_args()

    # print(args.serial_port_path)
    with open(args.serial_port_path, 'wb') as f:
        f.write(SYNC_BYTES)
        f.write(get_bytes_to_write_file_to_serial(args.executable1_path))
        f.write(get_bytes_to_write_file_to_serial(args.executable2_path))

