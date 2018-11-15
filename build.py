import subprocess
import shutil
import os
import os.path
import argparse

BUILD_QEMU_SCRIPT_NAME = 'config_and_make_qemu_with_GMBEOO.py'
QEMU_MEM_TRACER_SCRIPT_NAME = 'memory_tracer.py'
TESTS_DIR_NAME = 'tests'
BUILD_AND_RUN_TESTS_SCRIPT_NAME = 'build_and_run_tests.py'
TO_RUN_ON_GUEST_DIR_NAME = 'to_run_on_guest'
RUN_SCRIPT_FROM_SERIAL_ELF_NAME = 'run_executables_from_serial'
RUN_SCRIPT_FROM_SERIAL_ELF_REL_PATH = os.path.join(
    TO_RUN_ON_GUEST_DIR_NAME, RUN_SCRIPT_FROM_SERIAL_ELF_NAME)
COMMUNICATIONS_DIR_NAME = 'host_guest_communications'
RUN_SCRIPT_FROM_SERIAL_SOURCE_NAME = f'{RUN_SCRIPT_FROM_SERIAL_ELF_NAME}.c'
RUN_SCRIPT_FROM_SERIAL_SOURCE_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_SCRIPT_FROM_SERIAL_SOURCE_NAME)

def execute_cmd_in_dir(cmd, dir_path='.'):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Build qemu_mem_tracer.\n\n'
                'Run `python3.7 memory_tracer.py -h` for help about arguments '
                'that both memory_tracer.py and this script receive.')
parser.add_argument('qemu_with_GMBEOO_path', type=str)
parser.add_argument('--enable-debug', dest='debug_flag',
                    action='store_const',
                    const='--enable-debug', default='--disable-debug',
                    help='If specified, --enable-debug is passed to the '
                         'configure script of qemu_with_GMBEOO, instead of '
                         '--disable-debug (the default).')
parser.add_argument('--dont_compile_qemu', action='store_true',
                    help='If specified, this script doesn\'t build '
                         'qemu_with_GMBEOO.')
parser.add_argument('--run_tests', action='store_true',
                    help='If specified, this script runs tests (that '
                         'check whether qemu_mem_tracer works as '
                         'expected).')
parser.add_argument('--guest_image_path', type=str)
parser.add_argument('--snapshot_name', type=str)
args = parser.parse_args()

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]
this_script_location_dir_name = os.path.split(this_script_location)[-1]
if this_script_location_dir_name != 'qemu_mem_tracer':
    print(f'Attention:\n'
          f'This script assumes that other scripts in qemu_mem_tracer '
          f'are in the same folder as this script (i.e. in the folder '
          f'"{this_script_location}").\n'
          f'However, "{this_script_location_dir_name}" != "qemu_mem_tracer".\n'
          f'Enter "y" if you wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break

run_script_from_serial_source_path = os.path.join(
  this_script_location, RUN_SCRIPT_FROM_SERIAL_SOURCE_REL_PATH)
run_script_from_serial_elf_path = os.path.join(
  this_script_location, RUN_SCRIPT_FROM_SERIAL_ELF_REL_PATH)
compile_cmd = (f'gcc -Werror -Wall -pedantic '
               f'{run_script_from_serial_source_path} '
               f'-o {run_script_from_serial_elf_path}')
execute_cmd_in_dir(compile_cmd, this_script_location)

if not args.dont_compile_qemu:
    build_qemu_script_path = os.path.join(this_script_location,
                                          BUILD_QEMU_SCRIPT_NAME)
    build_qemu_cmd = (f'python3.7 {BUILD_QEMU_SCRIPT_NAME} '
                      f'{args.qemu_with_GMBEOO_path} {args.debug_flag}')
    execute_cmd_in_dir(build_qemu_cmd, this_script_location)


if args.run_tests:
    for arg_name in ('guest_image_path', 'snapshot_name'):
        if getattr(args, arg_name) is None:
            raise RuntimeError(f'--run_tests was specified, but '
                               f'--{arg_name} was not specified.')
    tests_dir_path = os.path.join(this_script_location, TESTS_DIR_NAME)
    build_and_run_tests_script_path = os.path.join(
        tests_dir_path, BUILD_AND_RUN_TESTS_SCRIPT_NAME)
    qemu_mem_tracer_script_path = os.path.join(
        this_script_location, QEMU_MEM_TRACER_SCRIPT_NAME)
    
    execute_cmd_in_dir(f'python3.7 {build_and_run_tests_script_path} '
                       f'{qemu_mem_tracer_script_path} '
                       f'{args.qemu_with_GMBEOO_path} '
                       f'{args.guest_image_path} '
                       f'{args.snapshot_name} '
                       f'--verbose '
                       ,
                       tests_dir_path)

