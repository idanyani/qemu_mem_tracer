import subprocess
import os
import os.path
import time
import argparse


parser = argparse.ArgumentParser(description='Run a test on the qemu guest.\n'
                                             '(GMBE = guest_mem_before_exec)')
parser.add_argument('guest_image_path', type=str,
                    help='The path of the qcow2 file which is the image of the'
                         ' guest.')
parser.add_argument('snapshot_name', type=str,
                    help='The name of the snapshot saved by the monitor '
                         'command `savevm`, which was specially constructed '
                         'for running a test.')
parser.add_argument('test_source_path', type=str,
                    help='The path of the test\'s C source file.')
parser.add_argument('host_password', type=str)
parser.add_argument('qemu_mem_tracer_path', type=str,
                    help='The path of qemu_mem_tracer.')
parser.add_argument('--trace_only_user_code_GMBE',
                    action='store_const',
                    const='on', default='off',
                    help='If specified, qemu would only trace memory accesses '
                         'by user code. Otherwise, qemu would trace all '
                         'accesses.')
parser.add_argument('--log_of_GMBE_block_len', type=int, default=0,
                    help='Log of the length of a GMBE_block, i.e. the number '
                         'of GMBE events in a GMBE_block. (It is used when '
                         'determining whether to trace a GMBE event.)')
parser.add_argument('--log_of_GMBE_tracing_ratio', type=int, default=0,
                    help='Log of the ratio between the number of blocks '
                         'of GMBE events we trace to the '
                         'total number of blocks. E.g. if GMBE_tracing_ratio '
                         'is 16, we trace 1 block, then skip 15 blocks, then '
                         'trace 1, then skip 15, and so on...')
parser.add_argument('--compile_qemu', action='store_const',
                    const=True, default=False,
                    help='If specified, this script also configures and '
                         'compiles qemu.')
parser.add_argument('--disable_debug_in_qemu', dest='debug_flag',
                    action='store_const',
                    const='--disable-debug', default='--enable-debug',
                    help='If specified (in case --compile_qemu was specified),'
                         ' --disable-debug is passed to the configure script '
                         'of qemu instead of --enable-debug (the default).')
args = parser.parse_args()

guest_image_path = os.path.realpath(args.guest_image_path)
test_source_path = os.path.realpath(args.test_source_path)
qemu_mem_tracer_path = os.path.realpath(args.qemu_mem_tracer_path)
qemu_mem_tracer_location = os.path.split(qemu_mem_tracer_path)[0]

def read_txt_file_when_it_exists(file_path):
    while not os.path.isfile(file_path):
        time.sleep(1)
    return read_txt_file(file_path)

def read_txt_file(file_path):
    with open(file_path) as f:
        return f.read()

def try_to_remove(file_path):
    try:
        os.remove(file_path)
    except OSError:
        pass


if args.compile_qemu:
    configure_cmd = (f'./configure --target-list=x86_64-softmmu '
                     f'--enable-trace-backends=simple {args.debug_flag}')
    print("running qemu's configure")
    subprocess.run(configure_cmd, shell=True, check=True, cwd=qemu_mem_tracer_path)
    print("running qemu's make")
    subprocess.run('make', shell=True, check=True, cwd=qemu_mem_tracer_path)


this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]
this_script_location_dir_name = os.path.split(this_script_location)[-1]
if this_script_location_dir_name != 'qemu_mem_tracer_runner':
    print(f'This script assumes that other scripts in qemu_mem_tracer_runner '
          f'are in the same folder as this script (i.e. in the folder '
          f'"{this_script_location}").\n'
          f'However, "{this_script_location_dir_name}" != "qemu_mem_tracer_runner".\n'
          f'Enter "y" if wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break
# I am assuming here that this script and run_qemu_and_test.sh are in the same
# folder.
run_qemu_and_test_expect_script_path = os.path.join(this_script_location,
                                                    'run_qemu_and_test.sh')

test_elf_path = os.path.join(qemu_mem_tracer_location, 'test_elf')
test_output_path = os.path.join(qemu_mem_tracer_location, 'test_output.txt')

try_to_remove(test_elf_path)
try_to_remove(test_output_path)

compile_test_cmd = (f'gcc -Werror -Wall -pedantic '
                    f'{test_source_path} -o {test_elf_path}')
subprocess.run(compile_test_cmd, shell=True, check=True,
               cwd=qemu_mem_tracer_location)

print('running run_qemu_and_test.sh')
subprocess.run(f'{run_qemu_and_test_expect_script_path} '
               f'"{args.host_password}" "{guest_image_path}" '
               f'"{args.snapshot_name}" {args.trace_only_user_code_GMBE} '
               f'{args.log_of_GMBE_block_len} {args.log_of_GMBE_tracing_ratio} '
               f'{this_script_location}',
               shell=True, check=True, cwd=qemu_mem_tracer_location)



# output = read_txt_file_when_it_exists(test_output_path)

