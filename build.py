#!/usr/bin/env python3

import subprocess
import os
import os.path
import argparse
import stat

BUILD_QEMU_SCRIPT_NAME = 'config_and_make_qemu_with_GMBEOO.py'
QEMU_MEM_TRACER_SCRIPT_NAME = 'memory_tracer.py'
TESTS_DIR_NAME = 'tests'
BUILD_AND_RUN_TESTS_SCRIPT_NAME = 'build_and_run_tests.py'
RUN_QEMU_AND_WORKLOAD_SCRIPT_NAME = 'run_qemu_and_workload.sh'
RUN_WORKLOAD_NATIVELY_SCRIPT_NAME = 'run_workload_natively.sh'
TO_RUN_ON_GUEST_DIR_NAME = 'to_run_on_guest'
COMMUNICATIONS_DIR_NAME = 'communications'
RUN_SCRIPT_FROM_SERIAL_ELF_NAME = 'run_executables_from_serial'
RUN_SCRIPT_FROM_SERIAL_ELF_REL_PATH = os.path.join(
    TO_RUN_ON_GUEST_DIR_NAME, RUN_SCRIPT_FROM_SERIAL_ELF_NAME)
RUN_SCRIPT_FROM_SERIAL_SOURCE_NAME = f'{RUN_SCRIPT_FROM_SERIAL_ELF_NAME}.c'
RUN_SCRIPT_FROM_SERIAL_SOURCE_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_SCRIPT_FROM_SERIAL_SOURCE_NAME)
WRITE_EXECUTABLES_TO_SERIAL_SCRIPT_NAME = 'write_executables_to_serial.py'
WRITE_EXECUTABLES_TO_SERIAL_SCRIPT_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, WRITE_EXECUTABLES_TO_SERIAL_SCRIPT_NAME)
RUN_QEMU_AND_WORKLOAD_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_QEMU_AND_WORKLOAD_SCRIPT_NAME)
RUN_WORKLOAD_NATIVELY_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_WORKLOAD_NATIVELY_SCRIPT_NAME)

def execute_cmd_in_dir(cmd, dir_path='.'):
    if args.verbosity_level > 0:
        print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, check=True, cwd=dir_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Build memory_tracer.\n\n'
                'Run `memory_tracer.py -h` for help about arguments '
                'that both memory_tracer.py and this script receive.')
parser.add_argument('qemu_with_GMBEOO_path', type=str)
parser.add_argument('--enable_debug',
                    action='store_const',
                    const='--enable_debug', default='',
                    help='If specified, `--enable-debug` is passed to the '
                         'configure script of qemu_with_GMBEOO, instead of: '
                         '`--disable-debug-mutex --disable-qom-cast-debug '
                         '--disable-debug-info`.')
parser.add_argument('--dont_compile_qemu', action='store_true',
                    help='If specified, this script doesn\'t build '
                         'qemu_with_GMBEOO.')
parser.add_argument('--run_tests', action='store_true',
                    help='If specified, this script runs tests (that '
                         'check whether memory_tracer works as expected).')
parser.add_argument('--verbosity_level', '-v', type=int, default=0)
parser.add_argument('--guest_image_path', type=str)
parser.add_argument('--snapshot_name', type=str)
args = parser.parse_args()

args.qemu_with_GMBEOO_path = os.path.realpath(args.qemu_with_GMBEOO_path)

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]
this_script_location_dir_name = os.path.split(this_script_location)[-1]
if this_script_location_dir_name != 'qemu_mem_tracer':
    print(f'Attention:\n'
          f'This script assumes that other scripts in memory_tracer '
          f'are in the same folder as this script (i.e. in the folder '
          f'"{this_script_location}").\n'
          f'However, "{this_script_location_dir_name}" != "memory_tracer".\n'
          f'Enter "y" if you wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break

to_run_on_guest_dir_path = os.path.join(this_script_location,
                                        TO_RUN_ON_GUEST_DIR_NAME)
if not os.path.isdir(to_run_on_guest_dir_path):
    os.mkdir(to_run_on_guest_dir_path)

run_qemu_and_workload_path = os.path.join(
    this_script_location, RUN_QEMU_AND_WORKLOAD_REL_PATH)
os.chmod(run_qemu_and_workload_path,
         os.stat(run_qemu_and_workload_path).st_mode | stat.S_IXUSR | stat.S_IRUSR)
run_workload_natively_path = os.path.join(
    this_script_location, RUN_WORKLOAD_NATIVELY_REL_PATH)
os.chmod(run_workload_natively_path,
         os.stat(run_workload_natively_path).st_mode | stat.S_IXUSR | stat.S_IRUSR)

run_script_from_serial_source_path = os.path.join(
    this_script_location, RUN_SCRIPT_FROM_SERIAL_SOURCE_REL_PATH)
run_script_from_serial_elf_path = os.path.join(
    this_script_location, RUN_SCRIPT_FROM_SERIAL_ELF_REL_PATH)
compile_cmd = ['gcc', '-Werror', '-Wall', '-pedantic',
               run_script_from_serial_source_path,
               '-o', run_script_from_serial_elf_path]
execute_cmd_in_dir(compile_cmd, this_script_location)

run_executables_to_serial_script_path = os.path.join(
    this_script_location, WRITE_EXECUTABLES_TO_SERIAL_SCRIPT_REL_PATH)
os.chmod(run_executables_to_serial_script_path,
         os.stat(run_executables_to_serial_script_path).st_mode |
         stat.S_IXUSR | stat.S_IRUSR)

if not args.dont_compile_qemu:
    build_qemu_script_path = os.path.join(this_script_location,
                                          BUILD_QEMU_SCRIPT_NAME)
    os.chmod(build_qemu_script_path,
             os.stat(build_qemu_script_path).st_mode | stat.S_IXUSR | stat.S_IRUSR)
    build_qemu_cmd = (build_qemu_script_path,
                      args.qemu_with_GMBEOO_path,
                      args.enable_debug)
    execute_cmd_in_dir(build_qemu_cmd, this_script_location)


if args.run_tests:
    for arg_name in ('guest_image_path', 'snapshot_name'):
        if getattr(args, arg_name) is None:
            raise RuntimeError(f'--run_tests was specified, but '
                               f'--{arg_name} was not specified.')
    tests_dir_path = os.path.join(this_script_location, TESTS_DIR_NAME)
    memory_tracer_script_path = os.path.join(
        this_script_location, QEMU_MEM_TRACER_SCRIPT_NAME)
    os.chmod(memory_tracer_script_path,
             os.stat(memory_tracer_script_path).st_mode | stat.S_IXUSR | stat.S_IRUSR)
    build_and_run_tests_script_path = os.path.join(
        tests_dir_path, BUILD_AND_RUN_TESTS_SCRIPT_NAME)
    os.chmod(build_and_run_tests_script_path,
             os.stat(build_and_run_tests_script_path).st_mode | stat.S_IXUSR | stat.S_IRUSR)
    execute_cmd_in_dir([build_and_run_tests_script_path,
                       memory_tracer_script_path,
                       args.qemu_with_GMBEOO_path,
                       args.guest_image_path,
                       args.snapshot_name,
                       '--verbosity_level',
                       str(args.verbosity_level)])

