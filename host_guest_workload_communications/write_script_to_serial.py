import argparse
import time
# import struct
import serial
import subprocess

SYNC_BYTES = b'serial sync\n'

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

if __name__ == '__main__':
    args = parse_cmd_args()

    print(args.serial_port_path)

    with open(args.script_path, 'rb') as f:
        script_contents = f.read()

    script_size = len(script_contents)
    script_size_bytes = str(script_size).encode('ascii') + b'\n'

    dont_add_communications_bytes = (
        b'1' if args.dont_add_communications_with_host_to_workload == 'True' else b'0')

    script_contents_as_hex = script_contents.hex()
    assert(len(script_contents_as_hex) == script_size * 2)
    print(script_contents_as_hex)

    # echo -e "\012"
    # execute_cmd(f'echo -en "\x41"'
    #             f' > {args.serial_port_path}')
    # execute_cmd(f'echo -en "{get_byte_repr_for_serial(dont_add_communications)}"'
    #             f' > {args.serial_port_path}')

    # execute_cmd(f'echo -en "{get_bytes_repr_for_serial(script_size_bytes)}"'
    #             f' > {args.serial_port_path}')

    # execute_cmd(f'cat {args.script_path} > {args.serial_port_path}')

    with open(args.serial_port_path, 'wb') as f:
        f.write(SYNC_BYTES)
        f.write(dont_add_communications_bytes)
        f.write(script_size_bytes)
        time.sleep(1)
        # print(script_size * 3)
        for i in range(0, len(script_contents_as_hex), 2):
            hex_repr_and_line_feed_bytes = (
                f'{script_contents_as_hex[i:i+2]}\n'.encode('ascii'))
            time.sleep(0.0003)
            # print(i)
            f.write(hex_repr_and_line_feed_bytes)

    # print('aoeu')


    # ser = serial.Serial(args.serial_port_path, baudrate=115200)
    # if not ser.isOpen():
    #     raise RuntimeError(f'Failed to open serial {args.serial_port_path}')
    
    # ser.write(SYNC_BYTES)
    # print(SYNC_BYTES)
    # ser.write(dont_add_communications_bytes)
    # print(dont_add_communications_bytes)
    # ser.write(script_size_bytes)
    # print(script_size_bytes)
    # ser.write(script_contents.hex().encode('ascii'))

