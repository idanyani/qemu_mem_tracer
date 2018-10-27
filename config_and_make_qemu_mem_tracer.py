import subprocess
import os
import os.path
import argparse

def execute_cmd_in_dir(cmd, dir_path):
    print(f'executing cmd (in {dir_path}): {cmd}')
    subprocess.run(cmd, shell=True, check=True, cwd=dir_path)

def get_current_branch_name(repo_path):
    return subprocess.run('git rev-parse --abbrev-ref HEAD', shell=True,
                          check=True, cwd=repo_path,
                          capture_output=True).stdout.strip().decode()

parser = argparse.ArgumentParser(
    description='Call qemu_mem_tracer\'s configure and make scripts.')
parser.add_argument('qemu_mem_tracer_path', type=str,
                    help='The path of qemu_mem_tracer.')
parser.add_argument('--enable-debug', dest='debug_flag',
                    action='store_const',
                    const='--enable-debug', default='--disable-debug',
                    help='If specified, --enable-debug is passed to the '
                         'configure script of qemu_mem_tracer, instead of '
                         '--disable-debug (the default).')
args = parser.parse_args()

qemu_mem_tracer_path = os.path.realpath(args.qemu_mem_tracer_path)

qemu_mem_tracer_branch_name = get_current_branch_name(qemu_mem_tracer_path)
if qemu_mem_tracer_branch_name != 'mem_tracer':
    print(f'Attention:\n'
          f'The expected current branch name of qemu_mem_tracer is '
          f'"mem_tracer", but it is "{qemu_mem_tracer_branch_name}".\n'
          f'Enter "y" if you wish to proceed anyway.')
    while True:
        user_input = input()
        if user_input == 'y':
            break

configure_cmd = (f'./configure --target-list=x86_64-softmmu '
                 f'--enable-trace-backends=simple {args.debug_flag}')
execute_cmd_in_dir(configure_cmd, qemu_mem_tracer_path)
execute_cmd_in_dir('make', qemu_mem_tracer_path)

