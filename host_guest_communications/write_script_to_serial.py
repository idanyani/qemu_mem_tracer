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

    with open(args.serial_port_path, 'wb') as f:
        f.write(SYNC_BYTES)
        f.write(dont_add_communications_bytes)
        f.write(script_size_bytes)
        for i in range(0, len(script_contents_as_hex), 2):
            # time.sleep(0.00001)
            hex_repr_and_line_feed_bytes = (
                f'{script_contents_as_hex[i:i+2]}\n'.encode('ascii'))
            f.write(hex_repr_and_line_feed_bytes)

