import argparse
import struct

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        description='Write the received script\'s size (as a uint32_t), and '
                    'then its contents, to the received serial port.')
    parser.add_argument('script_path', type=str)
    parser.add_argument('serial_port_path', type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_cmd_args()

    with open(args.script_path, 'rb') as f:
        script_contents = f.read()

    script_size = len(script_contents)
    script_size_bytes = struct.pack('<i', script_size)

    with open(args.serial_port_path, 'wb') as f:
        f.write(script_size_bytes)
        f.write(script_contents)
