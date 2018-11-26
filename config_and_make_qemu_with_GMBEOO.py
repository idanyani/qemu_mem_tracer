#!/usr/bin/env python3.7

import subprocess
import os
import os.path
import argparse

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, check=True, cwd=dir_path)

def get_current_branch_name(repo_path):
    return subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                          check=True, cwd=repo_path,
                          capture_output=True).stdout.strip().decode()

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Call qemu_with_GMBEOO\'s configure and make scripts.\n\n'
                'Run `build.py -h` for help about the cmd arguments.')
parser.add_argument('qemu_with_GMBEOO_path', type=str)
parser.add_argument('--enable_debug', dest='debug_flag',
                    action='store_const',
                    const=['--enable-debug'],
                    default=['--disable-debug-mutex',
                             '--disable-qom-cast-debug',
                             '--disable-debug-info'])
args = parser.parse_args()

qemu_with_GMBEOO_path = os.path.realpath(args.qemu_with_GMBEOO_path)

qemu_with_GMBEOO_branch_name = get_current_branch_name(qemu_with_GMBEOO_path)
if qemu_with_GMBEOO_branch_name != 'mem_tracer':
    print(f'Attention:\n'
          f'The expected current branch name of qemu_with_GMBEOO is '
          f'"mem_tracer", but it is "{qemu_with_GMBEOO_branch_name}".\n'
          f'Enter "y" if you wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break

configure_cmd = ['./configure',
                 '--target-list=x86_64-softmmu',
                 '--enable-trace-backends=simple'] + args.debug_flag
execute_cmd_in_dir(configure_cmd, qemu_with_GMBEOO_path)
execute_cmd_in_dir('make', qemu_with_GMBEOO_path)

