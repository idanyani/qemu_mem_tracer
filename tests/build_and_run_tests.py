import shutil
import subprocess
import os
import os.path
import argparse

BUILD_QEMU_SCRIPT_NAME = 'config_and_make_qemu_mem_tracer.py'
SIMPLE_ANALYSIS_SOURCE_NAME = 'simple_analysis.c'
SIMPLE_ANALYSIS_NAME = os.path.splitext(SIMPLE_ANALYSIS_SOURCE_NAME)[0]
# Note that this script removes this directory upon starting.
OUTPUT_DIR_NAME = 'tests_bin'

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]

output_dir_path = os.path.join(this_script_location, OUTPUT_DIR_NAME)
shutil.rmtree(output_dir_path, ignore_errors=True)
os.mkdir(output_dir_path)
simple_analysis_bin_path = os.path.join(output_dir_path, SIMPLE_ANALYSIS_NAME)

compile_simple_analysis_cmd = (f'gcc -Werror -Wall -pedantic '
                               f'{SIMPLE_ANALYSIS_SOURCE_NAME} '
                               f'-o {simple_analysis_bin_path}')
execute_cmd_in_dir(compile_simple_analysis_cmd, this_script_location)

