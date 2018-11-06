import shutil
import subprocess
import os
import os.path
import argparse
import tests


SIMPLE_ANALYSIS_SOURCE_NAME = 'simple_analysis.c'
SIMPLE_ANALYSIS_NAME = os.path.splitext(SIMPLE_ANALYSIS_SOURCE_NAME)[0]
# Note that this script removes this directory upon starting.
OUTPUT_DIR_NAME = 'tests_bin'
TEST_SCRIPT_PREFIX = 'test_'
TEST_SCRIPT_EXT = '.py'
LOADABLE_KERNEL_MODULE_SUFFIX = '_lkm'

def execute_cmd_in_dir(cmd, dir_path):
    if args.verbose:
        print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

def compile_c_files(dir_path):
    for root_dir_path, dir_names, file_fullnames in os.walk(dir_path):
        if (not root_dir_path.endswith(OUTPUT_DIR_NAME)) and (
                not root_dir_path.endswith(LOADABLE_KERNEL_MODULE_SUFFIX)) and (
                not '999.specrand' in root_dir_path):
            output_dir_path = os.path.join(root_dir_path, OUTPUT_DIR_NAME)
            shutil.rmtree(output_dir_path, ignore_errors=True)
            os.mkdir(output_dir_path)

            for fullname in file_fullnames:
                name, ext = os.path.splitext(fullname)
                if ext.lower() == '.c' and not name.endswith('_lkm'):
                    bin_rel_path = os.path.join(OUTPUT_DIR_NAME, name)
                    compile_cmd = (f'gcc -Werror -Wall -pedantic {fullname} '
                                   f'-o {bin_rel_path}')
                    execute_cmd_in_dir(compile_cmd, root_dir_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Build and run tests for qemu_mem_tracer.\n\n'
                'Run `memory_tracer.py -h` for help about cmd '
                'arguments that both build.py and this script receive.')
parser.add_argument('qemu_mem_tracer_script_path', type=str,
                    help='The path of memory_tracer.py.')
parser.add_argument('qemu_with_GMBEOO_path', type=str)
parser.add_argument('guest_image_path', type=str)
parser.add_argument('snapshot_name', type=str)
parser.add_argument('host_password', type=str)
parser.add_argument('--verbose', '-v', action='store_true')
args = parser.parse_args()

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]

compile_c_files(this_script_location)

print(f'\n\n--------start running tests--------')
if args.verbose:
    tests.VERBOSE_LEVEL = 1
for attr in dir(tests):
    if attr.startswith('test_'):
        test_func = getattr(tests, attr)
        print(f'---start running {attr}---')
        test_func(this_script_location, args.qemu_mem_tracer_script_path,
                  args.qemu_with_GMBEOO_path, args.guest_image_path,
                  args.snapshot_name, args.host_password)
        print(f'---{attr} completed successfully---\n')
print(f'--------done running tests--------\n')

