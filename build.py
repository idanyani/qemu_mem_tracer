import subprocess
import shutil
import os
import os.path
import argparse

BUILD_QEMU_SCRIPT_NAME = 'config_and_make_qemu_mem_tracer.py'
MAKE_BIG_FIFO_SOURCE_NAME = 'make_big_fifo.c'
MAKE_BIG_FIFO_NAME = os.path.splitext(MAKE_BIG_FIFO_SOURCE_NAME)[0]
# Note that this script removes this directory upon starting.
OUTPUT_DIR_NAME = 'runner_bin'

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

# def get_current_branch_name(repo_path):
#     return subprocess.run('git rev-parse --abbrev-ref HEAD', shell=True,
#                           check=True, cwd=repo_path,
#                           capture_output=True).stdout.strip().decode()

parser = argparse.ArgumentParser(
    description='Build qemu_mem_tracer_runner.')
parser.add_argument('qemu_mem_tracer_path', type=str,
                    help='The path of qemu_mem_tracer.')
parser.add_argument('--enable-debug', dest='debug_flag',
                    action='store_const',
                    const='--enable-debug', default='--disable-debug',
                    help='If specified, --enable-debug is passed to the '
                         'configure script of qemu_mem_tracer, instead of '
                         '--disable-debug (the default).')
parser.add_argument('--dont_compile_qemu', action='store_const',
                    const=False, default=True,
                    help='If specified, this script doesn\'t build '
                         'qemu_mem_tracer.')
args = parser.parse_args()

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]
this_script_location_dir_name = os.path.split(this_script_location)[-1]
if this_script_location_dir_name != 'qemu_mem_tracer_runner':
    print(f'Attention:\n'
          f'This script assumes that other scripts in qemu_mem_tracer_runner '
          f'are in the same folder as this script (i.e. in the folder '
          f'"{this_script_location}").\n'
          f'However, "{this_script_location_dir_name}" != "qemu_mem_tracer_runner".\n'
          f'Enter "y" if you wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break

output_dir_path = os.path.join(this_script_location, OUTPUT_DIR_NAME)
shutil.rmtree(output_dir_path, ignore_errors=True)
os.mkdir(output_dir_path)

make_big_fifo_bin_path = os.path.join(output_dir_path, MAKE_BIG_FIFO_NAME)
compile_make_big_fifo_cmd = (f'gcc -Werror -Wall -pedantic '
                             f'{MAKE_BIG_FIFO_SOURCE_NAME} '
                             f'-o {make_big_fifo_bin_path}')
execute_cmd_in_dir(compile_make_big_fifo_cmd, this_script_location)

if not args.dont_compile_qemu:
    build_qemu_script_path = os.path.join(this_script_location,
                                          BUILD_QEMU_SCRIPT_NAME)
    build_qemu_cmd = (f'python3.7 {BUILD_QEMU_SCRIPT_NAME} '
                      f'{args.qemu_mem_tracer_path} {args.debug_flag}')
    execute_cmd_in_dir(build_qemu_cmd, this_script_location)

