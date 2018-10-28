import shutil
import subprocess
import os
import os.path
import unittest
import argparse

BUILD_QEMU_SCRIPT_NAME = 'config_and_make_qemu_mem_tracer.py'
SIMPLE_ANALYSIS_SOURCE_NAME = 'simple_analysis.c'
SIMPLE_ANALYSIS_NAME = os.path.splitext(SIMPLE_ANALYSIS_SOURCE_NAME)[0]
# Note that this script removes this directory upon starting.
OUTPUT_DIR_NAME = 'tests_bin'
TEST_SCRIPT_PREFIX = 'test_'
TEST_SCRIPT_EXT = '.py'

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

def compile_c_files(dir_path):
    for root_dir_path, dir_names, file_fullnames in os.walk(dir_path):
        if not root_dir_path.endswith(OUTPUT_DIR_NAME):
            output_dir_path = os.path.join(root_dir_path, OUTPUT_DIR_NAME)
            shutil.rmtree(output_dir_path, ignore_errors=True)
            os.mkdir(output_dir_path)

            for fullname in file_fullnames:
                name, ext = os.path.splitext(fullname)
                if ext.lower() == '.c':
                    bin_rel_path = os.path.join(OUTPUT_DIR_NAME, name)
                    compile_cmd = (f'gcc -Werror -Wall -pedantic {fullname} '
                                   f'-o {bin_rel_path}')
                    execute_cmd_in_dir(compile_cmd, root_dir_path)

def run_test_scripts(dir_path, qemu_mem_tracer_path, guest_image_path,
                     snapshot_name, host_password):
    for root_dir_path, dir_names, file_fullnames in os.walk(dir_path):
        for fullname in file_fullnames:
            name, ext = os.path.splitext(fullname)
            if name.startswith(TEST_SCRIPT_PREFIX) and ext.lower() == TEST_SCRIPT_EXT:
                run_test_cmd = (f'python3.7 {fullname} '
                                f'{qemu_mem_tracer_path} '
                                f'{guest_image_path} '
                                f'{snapshot_name} '
                                f'{host_password}')
                execute_cmd_in_dir(run_test_cmd, root_dir_path)
                    
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Build and run tests for qemu_mem_tracer_runner.\n\n'
                'Run `qemu_mem_tracer_runner -h` for help about the cmd '
                'arguments.')
parser.add_argument('qemu_mem_tracer_path', type=str)
parser.add_argument('guest_image_path', type=str)
parser.add_argument('snapshot_name', type=str)
parser.add_argument('host_password', type=str)
args = parser.parse_args()


this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]

compile_c_files(this_script_location)

run_test_scripts(this_script_location, args.qemu_mem_tracer_path,
                 args.guest_image_path, args.snapshot_name, args.host_password)



