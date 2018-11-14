import argparse
# import struct
# import serial
import subprocess

SYNC_BYTES = b'serial sync '

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        description='Write the received script\'s size (as a uint32_t), and '
                    'then its contents, to the received serial port.')
    parser.add_argument('script_path', type=str)
    parser.add_argument('serial_port_path', type=str)
    parser.add_argument('dont_add_communications_with_host_to_workload', type=str)
    return parser.parse_args()

def execute_cmd(cmd):
    print(f'executing cmd: {cmd}')
    subprocess.run(cmd, shell=True, check=True)

def byte_to_backslash_x_str(byte_to_convert):
    return '\\x' + hex(byte_to_convert)[2:].zfill(2)

def bytes_to_backslash_x_str(bytes_to_convert):
    result = ''
    for b in bytes_to_convert:
        result += byte_to_backslash_x_str(b)
    return result

if __name__ == '__main__':
    args = parse_cmd_args()

    with open(args.script_path, 'rb') as f:
        script_contents = f.read()

    script_size = len(script_contents)
    script_size_bytes = str(script_size).encode('ascii')

    dont_add_communications_bytes = (
        b'1' if args.dont_add_communications_with_host_to_workload == 'True' else b'0')

    # echo -e "\012"
    # execute_cmd(f'echo -en "\x41"'
    #             f' > {args.serial_port_path}')
    # execute_cmd(f'echo -en "{byte_to_backslash_x_str(dont_add_communications)}"'
    #             f' > {args.serial_port_path}')

    # execute_cmd(f'echo -en "{bytes_to_backslash_x_str(script_size_bytes)}"'
    #             f' > {args.serial_port_path}')

    # execute_cmd(f'cat {args.script_path} > {args.serial_port_path}')

    with open(args.serial_port_path, 'wb') as f:
        f.write(SYNC_BYTES)
        f.write(dont_add_communications_bytes)
        f.write(script_size_bytes)
        f.write(script_contents.hex())

    # print('aoeu')

    # ser = serial.Serial(args.serial_port_path, baudrate=115200)
    # if not ser.isOpen():
    #     raise RuntimeError(f'Failed to open serial {args.serial_port_path}')
    
    # ser.write(dont_add_communications_bytes)
    # print(dont_add_communications_bytes)
    # ser.write(script_size_bytes)
    # print(script_size_bytes)
    # # ser.write(script_contents)

