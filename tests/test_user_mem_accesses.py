import subprocess
import os
import os.path
import time
import argparse
import shutil
import pathlib
import unittest

WORKLOAD_RUNNER_REL_PATH = os.path.join('tests_bin',
                                        'simple_user_memory_intensive_workload')
ANALYSIS_TOOL_REL_PATH = os.path.join('tests_bin', 'simple_analysis')

def execute_cmd_in_dir(cmd, dir_path='.'):
    print(f'executing cmd (in {dir_path}): {cmd}\n')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Check whether qemu_mem_tracer produces trace records as '
                'expected.\n\n'
                'Run `qemu_mem_tracer -h` for help about the cmd arguments.')
parser.add_argument('qemu_mem_tracer_script_path', type=str)
parser.add_argument('qemu_with_GMBEOO_path', type=str)
parser.add_argument('guest_image_path', type=str)
parser.add_argument('snapshot_name', type=str)
parser.add_argument('host_password', type=str)
args = parser.parse_args()

this_script_path = os.path.realpath(__file__)
this_script_location = os.path.split(this_script_path)[0]

workload_runner_path = os.path.join(this_script_location,
                                    WORKLOAD_RUNNER_REL_PATH)
analysis_tool_path = os.path.join(this_script_location, ANALYSIS_TOOL_REL_PATH)

run_qemu_mem_tracer_cmd = (f'python3.7 {args.qemu_mem_tracer_script_path} '
                           f'"{args.guest_image_path}" '
                           f'"{args.snapshot_name}" '
                           f'"{workload_runner_path}" '
                           f'"{args.host_password}" '
                           f'"{args.qemu_with_GMBEOO_path}" '
                           f'--analysis_tool_path "{analysis_tool_path}" '
                           )
                           # f'--verbose ')
execute_cmd_in_dir(run_qemu_mem_tracer_cmd)


