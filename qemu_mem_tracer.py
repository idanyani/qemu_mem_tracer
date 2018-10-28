import subprocess
import os
import os.path
import time
import argparse
import shutil
import pathlib

TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_NAME = (
    'qemu_mem_tracer_temp_dir_for_guest_to_download_from')
TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_PATH = os.path.join(
    pathlib.Path.home(), TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_NAME)
WORKLOAD_RUNNER_DOWNLOAD_PATH = os.path.join(
    f'{TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_PATH}', 'workload_runner.bash')
WORKLOAD_DIR_DOWNLOAD_PATH = os.path.join(
    f'{TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_PATH}', 'workload')
MAKE_BIG_FIFO_REL_PATH = os.path.join('tracer_bin', 'make_big_fifo')

shutil.rmtree(TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_PATH, ignore_errors=True)
os.mkdir(TEMP_DIR_FOR_THE_GUEST_TO_DOWNLOAD_FROM_PATH)

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Run a workload on the QEMU guest while writing optimized GMBE '
                'trace records to a FIFO.\n\n'
                'GMBE is short for guest_mem_before_exec. This is an event in '
                'upstream QEMU 3.0.0 that occurs on every attempt of the QEMU '
                'guest to access a virtual memory address.\n\n'
                'We optimized QEMU\'s tracing code for the case in which only '
                'trace records of GMBE are gathered (we call it GMBE only '
                'optimization - GMBEOO).\n'
                'When GMBEOO is enabled, a trace record is structured as '
                'follows:\n\n'
                'struct GMBEOO_TraceRecord {\n'
                '    uint8_t size_shift : 3; /* interpreted as "1 << size_shift" bytes */\n'
                '    bool    sign_extend: 1; /* whether it is a sign-extended operation */\n'
                '    uint8_t endianness : 1; /* 0: little, 1: big */\n'
                '    bool    store      : 1; /* whether it is a store operation */\n'
                '    uint8_t cpl        : 2;\n'
                '    uint64_t unused2   : 56;\n'
                '    uint64_t virt_addr : 64;\n'
                '};')
parser.add_argument('guest_image_path', type=str,
                    help='The path of the qcow2 file which is the image of the'
                         ' guest.')
parser.add_argument('snapshot_name', type=str,
                    help='The name of the snapshot saved by the monitor '
                         'command `savevm`, which was specially constructed '
                         'for running a workload with GMBE tracing.')
parser.add_argument('workload_runner_path', type=str,
                    help='The path of the workload_runner script.\n'
                         'workload_runner would be downloaded and executed by '
                         'the qemu guest.\n\n'
                         'Either workload_runner or the workload itself must '
                         'do the following:\n'
                         '1. Print "-----begin test info-----".\n'
                         '2. Print runtime info of the test. This info '
                         'would be written to stdout, as well as passed as cmd '
                         'arguments to the analysis tool in case of '
                         '--analysis_tool_path was specified. (Print nothing '
                         'if you don\'t need any runtime info.)\n'
                         '3. Print "-----end test info-----".\n'
                         '4. Print "Ready to trace. Press enter to continue." '
                         'when you wish the tracing to start.\n'
                         '5. Wait until enter is pressed, and only then '
                         'start executing the code you wish to run while '
                         'tracing.\n'
                         '6. Print "Stop tracing." when you wish the tracing '
                         'to stop.\n\n'
                         'Note that workload_runner can also be an ELF that '
                         'includes the workload and the aforementioned prints.')
parser.add_argument('host_password', type=str,
                    help='If you don’t like the idea of your password in plain '
                         'text, feel free to patch our code so that scp would '
                         'use keys instead.')
parser.add_argument('qemu_with_GMBEOO_path', type=str,
                    help='The path of qemu_with_GMBEOO.')
parser.add_argument('--workload_dir_path', type=str,
                    help='The path of a directory that would be downloaded by '
                         'the qemu guest into its home directory, and named '
                         'qemu_mem_tracer_workload. (This is meant for '
                         'convenience, e.g. in case your workload includes '
                         'multiple small files that workload_runner executes '
                         'sequentially.\n'
                         'If your workload is heavy and unchanging, it would '
                         'probably be faster to download it to the QEMU guest, '
                         'use `savevm`, and later pass that snapshot\'s name '
                         'as the snapshot_name argument.\n')
parser.add_argument('--analysis_tool_path', type=str, default='',
                    help='Path of an analysis tool that would start executing '
                         'before the tracing starts.\n'
                         'The tracing would start after it prints '
                         '"Ready to analyze." (If this is never printed, it '
                         'will seem like qemu_mem_tracer.py is stuck.)')
parser.add_argument('--trace_only_user_code_GMBE',
                    action='store_const',
                    const='on', default='off',
                    help='If specified, qemu would only trace memory accesses '
                         'by user code. Otherwise, qemu would trace all '
                         'accesses.')
parser.add_argument('--log_of_GMBE_block_len', type=int, default=0,
                    help='Log of the length of a GMBE_block, i.e. the number '
                         'of GMBE events in a GMBE_block. (It is used when '
                         'determining whether to trace a GMBE event.)')
parser.add_argument('--log_of_GMBE_tracing_ratio', type=int, default=0,
                    help='Log of the ratio between the number of blocks '
                         'of GMBE events we trace to the '
                         'total number of blocks. E.g. if GMBE_tracing_ratio '
                         'is 16, we trace 1 block, then skip 15 blocks, then '
                         'trace 1, then skip 15, and so on...')
parser.add_argument('--dont_exit_qemu_when_done', action='store_const',
                    const=True, default=False,
                    help='If specified, qemu won\'t be terminated after running '
                         'the workload.\n\n'
                         'Remember that the guest would probably be in the '
                         'state it was before running the workload, which is '
                         'probably a quite uncommon state, e.g. /dev/tty is '
                         'overwritten by /dev/ttyS0.')
args = parser.parse_args()

guest_image_path = os.path.realpath(args.guest_image_path)
workload_runner_path = os.path.realpath(args.workload_runner_path)
qemu_with_GMBEOO_path = os.path.realpath(args.qemu_with_GMBEOO_path)
qemu_mem_tracer_location = os.path.split(qemu_with_GMBEOO_path)[0]


if args.workload_dir_path is None:
    pathlib.Path(WORKLOAD_DIR_DOWNLOAD_PATH).touch()
else:
    workload_dir_path = os.path.realpath(args.workload_dir_path)
    os.symlink(workload_dir_path, WORKLOAD_DIR_DOWNLOAD_PATH)

os.symlink(workload_runner_path, WORKLOAD_RUNNER_DOWNLOAD_PATH)

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

run_qemu_and_workload_expect_script_path = os.path.join(this_script_location,
                                                        'run_qemu_and_workload.sh')
make_big_fifo_path = os.path.join(this_script_location, MAKE_BIG_FIFO_REL_PATH)

run_qemu_and_workload_cmd = (f'{run_qemu_and_workload_expect_script_path} '
                             f'"{guest_image_path}" '
                             f'"{args.snapshot_name}" '
                             f'"{args.host_password}" '
                             f'{args.trace_only_user_code_GMBE} '
                             f'{args.log_of_GMBE_block_len} '
                             f'{args.log_of_GMBE_tracing_ratio} '
                             f'{this_script_location} '
                             f'{args.analysis_tool_path}')
print(f'executing cmd: {run_qemu_and_workload_cmd}')
subprocess.run(run_qemu_and_workload_cmd,
               shell=True, check=True, cwd=qemu_mem_tracer_location)

