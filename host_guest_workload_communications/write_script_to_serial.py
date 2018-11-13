import argparse
import struct

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        description='Write the received script\'s size (as a uint32_t), and '
                    'then its contents, to the received serial port.')
    parser.add_argument('script_path', type=str)
    parser.add_argument('serial_port_path', type=str)
    parser.add_argument('dont_add_communications_with_host_to_workload', type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_cmd_args()

    with open(args.script_path, 'rb') as f:
        script_contents = f.read()

    script_size = len(script_contents)
    script_size_bytes = struct.pack('<i', script_size)
    assert(len(script_size_bytes) == 4)
    dont_add_communications = (
        1 if args.dont_add_communications_with_host_to_workload == 'True' else 0)
    dont_add_communications_bytes = struct.pack('B', dont_add_communications)
    assert(len(dont_add_communications_bytes) == 1)

    with open(args.serial_port_path, 'wb') as f:
        f.write(dont_add_communications_bytes)
        f.write(script_size_bytes)
        f.write(script_contents)
