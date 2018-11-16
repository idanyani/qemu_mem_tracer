import sys
import subprocess
import os
import os.path
import time
import argparse
import shutil
import pathlib
import tempfile
import fcntl
import stat

F_SETPIPE_SZ = 1031  # Linux 2.6.35+
F_GETPIPE_SZ = 1032  # Linux 2.6.35+

EXECUTABLE1_FOR_SERIAL_NAME = 'executable1'
EXECUTABLE2_FOR_SERIAL_NAME = 'executable2'
EMPTY_FILE_NAME = 'empty'
EXECUTABLE1_PATH_ON_GUEST = os.path.join('/tmp', EXECUTABLE1_FOR_SERIAL_NAME)
EXECUTABLE2_PATH_ON_GUEST = os.path.join('/tmp', EXECUTABLE2_FOR_SERIAL_NAME)
COMMUNICATIONS_DIR_NAME = 'host_guest_communications'
RUN_QEMU_AND_WORKLOAD_EXPECT_SCRIPT_NAME = 'run_qemu_and_workload.sh'
RUN_QEMU_AND_WORKLOAD_EXPECT_SCRIPT_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_QEMU_AND_WORKLOAD_EXPECT_SCRIPT_NAME)
RUN_WORKLOAD_NATIVELY_EXPECT_SCRIPT_NAME = 'run_workload_natively.sh'
RUN_WORKLOAD_NATIVELY_EXPECT_SCRIPT_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, RUN_WORKLOAD_NATIVELY_EXPECT_SCRIPT_NAME)
WRITE_EXECUTABLES_TO_SERIAL_NAME = 'write_executables_to_serial.py'
WRITE_EXECUTABLES_TO_SERIAL_REL_PATH = os.path.join(
    COMMUNICATIONS_DIR_NAME, WRITE_EXECUTABLES_TO_SERIAL_NAME)
BASH_SCRIPT_FIRST_LINE = '#!/bin/bash'


def read_file_bytes(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def write_file(file_path, contents):
    with open(file_path, 'w') as f:
        return f.write(contents)

def execute_cmd_in_dir(cmd, dir_path='.', stdout_dest=subprocess.DEVNULL):
    debug_print(f'executing cmd (in {dir_path}): {cmd}')
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                          stdout=stdout_dest)

def verify_arg_is_file(arg, arg_name):
    if not os.path.isfile(arg):
        raise RuntimeError(f'{arg_name} must be a file path, but {arg} isn\'t.')

def verify_arg_is_fifo(arg, arg_name):
    if stat.S_ISFIFO(os.stat(arg).st_mode) == 0:
        raise RuntimeError(f'{arg_name} must be a fifo path, but {arg} isn\'t.')

def verify_arg_is_dir(arg, arg_name):
    if not os.path.isdir(arg):
        raise RuntimeError(f'{arg_name} must be a dir path, but {arg} isn\'t.')

def verify_arg_is_in_range(arg, arg_name, low, high):
    if not (low <= arg <= high):
        raise RuntimeError(f'{arg_name} must be in range [{low}, {high}], but '
                           f'{arg} isn\'t.')

def parse_cmd_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Run a workload on the QEMU guest while writing optimized GMBE '
                    'trace records to a FIFO.\n\n'
                    '(memory_tracer.py assumes you have already run build.py '
                    'successfully.)\n\n'
                    'GMBE is short for guest_mem_before_exec. This is an event in '
                    'upstream QEMU 3.0.0 that occurs on every attempt of the QEMU '
                    'guest to access a virtual memory address. (For more about '
                    'tracing in upstream QEMU, see '
                    'qemu/docs/devel/tracing.txt.)\n\n'
                    'We optimized QEMU\'s tracing code for the case in which only '
                    'trace records of GMBE are gathered. (We call it GMBE only '
                    'optimization - GMBEOO, and so we gave our fork of QEMU the '
                    'name qemu_with_GMBEOO. Note that in our documentation and '
                    'comments, we often refer to qemu_with_GMBEOO as `qemu`.)\n'
                    'When GMBEOO is enabled (in qemu_with_GMBEOO), a trace record '
                    'is structured as follows:\n\n'
                    'struct GMBEOO_TraceRecord {\n'
                    '    uint8_t size_shift : 3; /* interpreted as "1 << size_shift" bytes */\n'
                    '    bool    sign_extend: 1; /* whether it is a sign-extended operation */\n'
                    '    uint8_t endianness : 1; /* 0: little, 1: big */\n'
                    '    bool    store      : 1; /* whether it is a store operation */\n'
                    '    uint8_t cpl        : 2;\n'
                    '    uint64_t unused2   : 56;\n'
                    '    uint64_t virt_addr : 64;\n'
                    '};\n'
                    '\n'
                    'memory_tracer.py also prints the workload info (in case it '
                    'isn\'t the empty string), and the tracing duration in '
                    'miliseconds.\n'
                    'In case --analysis_tool_path is specified, memory_tracer.py '
                    'also prints the output of the analysis tool.\n\n'
                    'Note that the given workload can be any executable (e.g. '
                    'ELF, bash script).\n\n'
                    'If --analysis_tool_path is specified, the provided analysis '
                    'tool must do the following:\n'
                    '1. Receive in argv[1] the path of the trace FIFO, but not '
                    'open it for reading yet.'
                    '2. Register a handler for the signal SIGUSR1 (e.g. '
                    'by calling the `signal` syscall). The handler must:\n'
                    '    a. Print "-----begin analysis output-----".\n'
                    '    b. Print the output of the analysis tool.\n'
                    '    c. Print "-----end analysis output-----".\n'
                    '3. Print "Ready to analyze" when you wish the '
                    'tracing to start.\n'
                    '4. Open the trace FIFO for read, and start reading trace '
                    'records from it. Note that the reading from the FIFO should be '
                    'as fast as possible. Otherwise, the FIFO\'s buffer would get '
                    'full, and qemu_with_GMBEOO would start blocking when it '
                    'tries to write to the FIFO. Soon, trace_buf would get full, '
                    'and trace records of new GMBE events would be dropped.\n'
                    '(If any of the messages isn\'t printed, it will '
                    'probably seem like memory_tracer.py is stuck.)\n'
                    '\n'
                    'Note that some of the command line arguments might be '
                    'irrelevant to you as a user of memory_tracer, but they '
                    'exist because they are useful while developing '
                    'memory_tracer.'
                    )
    parser.add_argument('guest_image_path', type=str,
                        help='The path of the qcow2 file which is the image of the'
                             ' guest.')
    parser.add_argument('snapshot_name', type=str,
                        help='The name of the snapshot saved by the monitor '
                             'command `savevm`, which was specially constructed '
                             'for running a workload with GMBE tracing.')
    parser.add_argument('qemu_with_GMBEOO_path', type=str,
                        help='The path of qemu_with_GMBEOO.')
    workload_path = parser.add_mutually_exclusive_group(required=True)
    workload_path.add_argument('--workload_path_on_guest', type=str,
                               help='The path of the workload on the guest.')
    workload_path.add_argument('--workload_path_on_host', type=str,
                               help='The path of the workload on the host. The '
                                    'file in that path would be sent to the '
                                    'guest to run as the workload.')
    analysis_or_fifo = parser.add_mutually_exclusive_group(required=True)
    analysis_or_fifo.add_argument(
        '--analysis_tool_path', type=str, default='/dev/null',
        help='Path of an analysis tool that would start executing '
             'before the tracing starts.\n')
    analysis_or_fifo.add_argument(
        '--trace_fifo_path', type=str,
        help='Path of the FIFO into which trace records will be '
             'written. Note that as mentioned above, a scenario '
             'in which the FIFO\'s buffer getting full is bad, and '
             'so it is recommended to use a FIFO whose buffer is '
             'of size `cat /proc/sys/fs/pipe-max-size`.')
    analysis_or_fifo.add_argument(
        '--dont_trace', action='store_true',
        help='If specified, memory_tracer.py will run without '
             'enabling the tracing feature of qemu_with_GMBEOO. '
             'Therefore, it will not print the trace info (even '
             'if --print_trace_info is specified). '
             'This is useful for comparing the speed of '
             'qemu_with_GMBEOO with and without tracing.')
    analysis_or_fifo.add_argument(
        '--dont_use_qemu', action='store_true',
        help='If specified, memory_tracer.py will run the '
             'workload on the host (i.e. natively). '
             'Please pass dummy non-empty '
             'strings as the arguments guest_image_path, '
             'snapshot_name, and qemu_with_GMBEOO_path. '
             'As expected, no trace info will be printed (even if '
             '--print_trace_info is specified).'
             'This is useful for comparing the speed of '
             'qemu_with_GMBEOO to running the code natively. ')
    parser.add_argument('--trace_only_CPL3_code_GMBE',
                        action='store_const',
                        const='on', default='off',
                        help='If specified, qemu would only trace memory accesses '
                             'by CPL3 code. Otherwise, qemu would trace all '
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
    dont_add_communications_or_timeout = parser.add_mutually_exclusive_group()
    dont_add_communications_or_timeout.add_argument(
        '--timeout', type=float,
        help='If specified, the workload would be stopped '
             'when the specified timeout elapses. '
             'Note that if you use '
             '--dont_add_communications_with_host_to_workload, '
             'then the timeout includes the communications '
             'with the host. Otherwise, the timeout doesn\'t '
             'include the communications.')
    dont_add_communications_or_timeout.add_argument(
        '--dont_add_communications_with_host_to_workload', action='store_true',
        help='If specified, the workload would not be wrapped with code '
             'that handles the required communications between the guest and '
             'the host, i.e. the workload (given in workload_path_on_host or '
             'workload_path_on_guest) must do the following:\n'
             '(1) Print "-----begin workload info-----".\n'
             '(2) Print runtime info of the workload. This info '
             'will be written to stdout, as well as passed as cmd '
             'arguments to the analysis tool in case of '
             '--analysis_tool_path was specified. (Print nothing '
             'if you don\'t need any runtime info.)\n'
             '(3) Print "-----end workload info-----".\n'
             '(4) Print "Ready to trace. Press enter to continue" '
             'when you wish the tracing to start.\n'
             '(5) Wait until enter is pressed, and only then '
             'start executing the code you wish to run while '
             'tracing.\n'
             '(6) Print "Stop tracing" when you wish the tracing '
             'to stop.\n'
             '(If any of the messages isn\'t printed, it will '
             'probably seem like memory_tracer.py is stuck.)\n\n')
    parser.add_argument('--print_trace_info', action='store_true',
                        help='If specified, memory_tracer.py would also print some '
                             'additional trace info: '
                             'num_of_events_waiting_in_trace_buf (only if it isn\'t '
                             '0, which probably shouldn\'t happen); '
                             'num_of_GMBE_events_since_enabling_GMBEOO (excluding '
                             'non-CPL3 GMBE events, in case '
                             '--trace_only_CPL3_code_GMBE was specified); '
                             'num_of_events_written_to_trace_buf; '
                             'num_of_missing_events (i.e. '
                             '`num_of_events_written_to_trace_buf - '
                             'num_of_events_written_to_trace_file - '
                             'num_of_events_waiting_in_trace_buf`, but only if it '
                             'isn\'t 0, which is probably a bug in '
                             'qemu_with_GMBEOO); '
                             'actual_tracing_ratio (i.e. '
                             'num_of_GMBE_events_since_enabling_GMBEOO / '
                             'num_of_events_written_to_trace_buf); '
                             'num_of_dropped_events (i.e. events such that when '
                             'qemu_with_GMBEOO tried to write them to the '
                             'trace_buf, it was full, so they were discarded. '
                             'This shouldn\'t happen normally.')
    parser.add_argument('--dont_use_nographic', action='store_true',
                        help='If specified, qemu_with_GMBEOO will be started '
                             'with the cmd argument `-monitor stdio` instead '
                             'of `-nographic`. This degrades performance, but '
                             'is probably more convenient while developing '
                             'memory_tracer on your machine. See the official '
                             'documentation '
                             '(https://qemu.weilnetz.de/doc/qemu-doc.html) for '
                             'more about `-nographic` and `-monitor stdio`.')
    parser.add_argument('--dont_exit_qemu_when_done', action='store_true',
                        help='If specified, qemu won\'t be terminated after running '
                             'the workload, and you would be able to use the '
                             'terminal to send monitor commands, as well as use '
                             'the qemu guest directly, in case you have a graphic '
                             'interface (which isn\'t the case if you are running '
                             'memory_tracer.py on a remote server using ssh). '
                             'Still, you would be able to use the qemu guest, e.g. '
                             'by connecting to it using ssh.\n\n'
                             'Remember that the guest would probably be in the '
                             'state it was before running the workload, which is '
                             'probably a quite uncommon state, e.g. /dev/tty is '
                             'overwritten by /dev/ttyS0.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='If specified, debug messages are printed.')
    args = parser.parse_args()

    if args.workload_path_on_host:
        verify_arg_is_file(args.workload_path_on_host, 'workload_path_on_host')
    if not args.dont_use_qemu:
        verify_arg_is_file(args.guest_image_path, 'guest_image_path')
        verify_arg_is_dir(args.qemu_with_GMBEOO_path, 'qemu_with_GMBEOO_path')
        if args.analysis_tool_path != '/dev/null':
            verify_arg_is_file(args.analysis_tool_path, 'analysis_tool_path')
        if args.trace_fifo_path:
            verify_arg_is_fifo(args.trace_fifo_path, 'trace_fifo_path')

        verify_arg_is_in_range(args.log_of_GMBE_block_len,
                               'log_of_GMBE_block_len', 0, 64)
        verify_arg_is_in_range(args.log_of_GMBE_tracing_ratio,
                               'log_of_GMBE_tracing_ratio', 0, 64)
        if args.log_of_GMBE_block_len + args.log_of_GMBE_tracing_ratio > 64:
            raise RuntimeError(f'log_of_GMBE_block_len + log_of_GMBE_tracing_ratio '
                               f'must be in range [0, 64], but '
                               f'{args.log_of_GMBE_block_len} + '
                               f'{args.log_of_GMBE_tracing_ratio} = '
                               f'{args.log_of_GMBE_block_len + args.log_of_GMBE_tracing_ratio}'
                               f' isn\'t.')
    return args

def verify_this_script_location(this_script_location):
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

def create_empty_file(file_path):
    with open(file_path, 'w'):
        pass

def get_executables_paths(workload_path_on_guest, workload_path_on_host,
                          timeout, dont_use_qemu, dont_add_communications,
                          temp_dir_path):

    if timeout:
        timeout_cmd_prefix = f'timeout {timeout} '
    else:
        timeout_cmd_prefix = ''

    if dont_use_qemu:
        executable2_path_when_running_executable1 = workload_path_on_host
    elif workload_path_on_guest:
        executable2_path_when_running_executable1 = workload_path_on_guest
    else:
        assert(workload_path_on_host and not dont_use_qemu)
        executable2_path_when_running_executable1 = EXECUTABLE2_PATH_ON_GUEST
        executable2_path = workload_path_on_host

    run_executable_2_cmd = (f'{timeout_cmd_prefix}'
                            f'{executable2_path_when_running_executable1}')

    if dont_use_qemu or workload_path_on_guest:
        empty_file_path = os.path.join(temp_dir_path, EMPTY_FILE_NAME)
        create_empty_file(empty_file_path)
        executable2_path = empty_file_path

        executable2_dir_path_when_running_executable1 = os.path.split(
            executable2_path_when_running_executable1)[0]
        run_executable_2_cmd = (
            f'(cd {executable2_dir_path_when_running_executable1} && '
            f'{run_executable_2_cmd})')

    if dont_add_communications:
        executable1_source = (f'{BASH_SCRIPT_FIRST_LINE}\n'
                              f'{run_executable_2_cmd}\n')
    else: 
        executable1_source = (
            f'{BASH_SCRIPT_FIRST_LINE}\n'
            f'echo "-----begin workload info-----"\n'
            f'echo "-----end workload info-----"\n'
            f'echo "Ready to trace. Press enter to continue"\n'
            f'read -n1\n'
            f'{run_executable_2_cmd}\n'
            f'echo "Stop tracing"\n'
            )
    executable1_path = os.path.join(temp_dir_path, EXECUTABLE1_FOR_SERIAL_NAME)
    write_file(executable1_path, executable1_source)
    os.chmod(executable1_path, 0o777)
    # os.chmod(executable1_path, stat.S_IEXEC)

    return executable1_path, executable2_path    


def get_trace_fifo_path(trace_fifo_path_cmd_arg):
    if trace_fifo_path_cmd_arg:
        return trace_fifo_path_cmd_arg

    trace_fifo_path = os.path.join(temp_dir_path, 'trace_fifo')
    os.mkfifo(trace_fifo_path)
    print_fifo_max_size_cmd = 'cat /proc/sys/fs/pipe-max-size'
    fifo_max_size_as_str = execute_cmd_in_dir(
        print_fifo_max_size_cmd,
        stdout_dest=subprocess.PIPE).stdout.strip().decode()
    fifo_max_size = int(fifo_max_size_as_str)
    
    debug_print(f'change {trace_fifo_path} to size {fifo_max_size} '
                f'(/proc/sys/fs/pipe-max-size)')
    fifo_fd = os.open(trace_fifo_path, os.O_NONBLOCK)
    fcntl.fcntl(fifo_fd, F_SETPIPE_SZ, fifo_max_size)
    assert(fcntl.fcntl(fifo_fd, F_GETPIPE_SZ) == fifo_max_size)
    os.close(fifo_fd)

    return trace_fifo_path

if __name__ == '__main__':
    args = parse_cmd_args()

    if args.verbose:
        def debug_print(*args, **kwargs):
            print(*args, file=sys.stderr, **kwargs)
            sys.stderr.flush()
        # debug_print = print
    else:
        def debug_print(*args, **kwargs):
            return

    guest_image_path = os.path.realpath(args.guest_image_path)

    this_script_path = os.path.realpath(__file__)
    this_script_location = os.path.split(this_script_path)[0]

    verify_this_script_location(this_script_location)

    with tempfile.TemporaryDirectory() as temp_dir_path:
        executable1_path, executable2_path = get_executables_paths(
            args.workload_path_on_guest, args.workload_path_on_host,
            args.timeout, args.dont_use_qemu,
            args.dont_add_communications_with_host_to_workload,
            temp_dir_path)
        if not args.dont_use_qemu:
            trace_fifo_path = get_trace_fifo_path(args.trace_fifo_path)

            write_executables_to_serial_path = os.path.join(
                this_script_location, WRITE_EXECUTABLES_TO_SERIAL_REL_PATH)
            qemu_with_GMBEOO_path = os.path.realpath(args.qemu_with_GMBEOO_path)
            run_qemu_and_workload_expect_script_path = os.path.join(
                this_script_location, RUN_QEMU_AND_WORKLOAD_EXPECT_SCRIPT_REL_PATH)

            run_qemu_and_workload_cmd = (f'{run_qemu_and_workload_expect_script_path} '
                                         f'"{guest_image_path}" '
                                         f'"{args.snapshot_name}" '
                                         f'"{executable1_path}" '
                                         f'"{executable2_path}" '
                                         f'"{write_executables_to_serial_path}" '
                                         f'{args.trace_only_CPL3_code_GMBE} '
                                         f'{args.log_of_GMBE_block_len} '
                                         f'{args.log_of_GMBE_tracing_ratio} '
                                         f'"{args.analysis_tool_path}" '
                                         f'"{trace_fifo_path}" '
                                         f'"{qemu_with_GMBEOO_path}" '
                                         f'{args.verbose} '
                                         f'{args.dont_exit_qemu_when_done} '
                                         f'{args.print_trace_info} '
                                         f'{args.dont_trace} '
                                         f'{args.dont_add_communications_with_host_to_workload} '
                                         f'{args.dont_use_nographic} '
                                         )

            execute_cmd_in_dir(run_qemu_and_workload_cmd, temp_dir_path, sys.stdout)

        else:
            assert(args.dont_use_qemu)
            run_workload_natively_expect_script_path = os.path.join(
                this_script_location, RUN_WORKLOAD_NATIVELY_EXPECT_SCRIPT_REL_PATH)
            run_workload_cmd = (f'{run_workload_natively_expect_script_path} '
                                f'"{executable1_path}" '
                                f'{args.verbose} '
                                )

            execute_cmd_in_dir(run_workload_cmd, temp_dir_path, sys.stdout)

