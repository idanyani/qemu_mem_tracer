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

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

def compile_c_files(dir_path):
    for root_dir_path, dir_names, file_names in os.walk(dir_path):
        if not root_dir_path.endswith(OUTPUT_DIR_NAME):
            output_dir_path = os.path.join(root_dir_path, OUTPUT_DIR_NAME)
            shutil.rmtree(output_dir_path, ignore_errors=True)
            os.mkdir(output_dir_path)

            for file_fullname in file_names:
                name, ext = os.path.splitext(file_fullname)
                if ext.lower() == '.c':
                    bin_rel_path = os.path.join(OUTPUT_DIR_NAME, name)
                    compile_cmd = (f'gcc -Werror -Wall -pedantic {file_fullname} '
                                   f'-o {bin_rel_path}')
                    execute_cmd_in_dir(compile_cmd, root_dir_path)
                    



this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]

compile_c_files(this_script_location)

tests = unittest.TestLoader().discover(this_script_location)
result = unittest.TextTestRunner(verbosity=2).run(tests)
if result.wasSuccessful():
    exit(0)
else:
    exit(1)


