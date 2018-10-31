import subprocess
import shutil
import os
import os.path
import time
import tempfile
import re
import sys
import fcntl
import signal

F_SETPIPE_SZ = 1031  # Linux 2.6.35+
F_GETPIPE_SZ = 1032  # Linux 2.6.35+

SIGKILL = 9

# constants from common_memory_intensive.h and long_memory_intensive.h
OUR_ARR_LEN = 10000
SMALL_NUM_OF_ITERS_OVER_OUR_ARR = 5
BIG_NUM_OF_ITERS_OVER_OUR_ARR = 500

NUM_OF_ACCESSES_FOR_INC = 2


def read_file_until_it_contains_str(file_path, expected_str):
    print(f'expecting to find "{expected_str}" in {file_path}')
    while True:
        file_contents = read_file(file_path)
        if expected_str in file_contents:
            return file_contents
        time.sleep(1)

def read_file(file_path):
    with open(file_path) as f:
        return f.read()

def execute_cmd_in_dir(cmd, dir_path='.', stdout_dest=subprocess.PIPE,
                       stderr_dest=sys.stderr):
    print(f'executing cmd (in {dir_path}): {cmd}')
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                          stdout=stdout_dest, stderr=stderr_dest)

def get_output_of_executed_cmd_in_dir(cmd, dir_path='.'):
    return execute_cmd_in_dir(cmd, dir_path).stdout.strip().decode()

def get_tests_bin_file_path(this_script_location, file_name):
    return os.path.join(this_script_location, 'tests_bin', file_name)

def get_mem_tracer_cmd(this_script_location, qemu_mem_tracer_script_path,
                       qemu_with_GMBEOO_path, guest_image_path,
                       snapshot_name, host_password, workload_runner_path,
                       extra_cmd_args=''):
    return (f'python3.7 {qemu_mem_tracer_script_path} '
            f'"{guest_image_path}" '
            f'"{snapshot_name}" '
            f'"{workload_runner_path}" '
            f'"{host_password}" '
            f'"{qemu_with_GMBEOO_path}" '
            f'{extra_cmd_args} '
            )
            # f'--verbose ')

def get_mem_tracer_error_and_output(*args, **kwargs):
    cmd_result = execute_cmd_in_dir(get_mem_tracer_cmd(*args, **kwargs),
                                    stderr_dest=subprocess.PIPE)
    return cmd_result.stderr.strip().decode() + cmd_result.stdout.strip().decode()

def get_mem_tracer_output(*args, **kwargs):
    return get_output_of_executed_cmd_in_dir(get_mem_tracer_cmd(*args, **kwargs))
    
def _test_workload_without_info(this_script_location, qemu_mem_tracer_script_path,
                               qemu_with_GMBEOO_path, guest_image_path,
                               snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 'dummy_workload_without_info'),
        f'--analysis_tool_path "{simple_analysis_path}"')
    
    # match succeeding means that the workload info isn't printed.
    assert(re.match(
        '^tracing_duration_in_seconds:.*analysis output:.*analysis cmd args:.*',
        mem_tracer_output, re.DOTALL) is not None)

def _test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'dummy_workload_with_funny_test_info'),
        f'--analysis_tool_path "{simple_analysis_path}"')
    analysis_cmd_args_as_str = re.match(
        r'^workload info:.*analysis output:.*analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')

def check_mem_accesses(mem_tracer_output, our_arr_len, num_of_iters_over_our_arr):
    min_num_of_expected_accesses_for_elem = (
        num_of_iters_over_our_arr * NUM_OF_ACCESSES_FOR_INC)
    min_num_of_expected_accesses = (
        our_arr_len * min_num_of_expected_accesses_for_elem)

    workload_info_as_str, our_buf_addr_as_str, counter_arr_as_str = re.match(
        r'^workload info:(.*)tracing_duration_in_seconds:.*our_buf_addr:(.*)'
        r'num_of_mem_accesses_by_CPL3_code:.*counter_arr:(.*)'
        r'analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1, 2, 3)
    
    our_buf_addr_in_workload_info = int(workload_info_as_str.strip(), 16)
    our_buf_addr_in_analysis_output = int(our_buf_addr_as_str.strip())
    assert(our_buf_addr_in_workload_info == our_buf_addr_in_analysis_output)
    
    # Use `list` so that counter_arr isn't an iterator (because then `sum`
    # would exhaust it).
    counter_arr = list(map(int, filter(None, counter_arr_as_str.strip().split(","))))
    assert(len(counter_arr) == OUR_ARR_LEN)

    counter_arr_sum = sum(counter_arr)
    assert(min_num_of_expected_accesses <= counter_arr_sum <=
           min_num_of_expected_accesses + 100)

    for counter in counter_arr:
        assert(min_num_of_expected_accesses_for_elem <= counter <=
               min_num_of_expected_accesses_for_elem + 10)


    # This seems to me like proof that the extra memory accesses happen because
    # of page faults. I don't know why we get 2 extra memory accesses, but I
    # guess that for some reason both the load and the store operations (that
    # TCG emitted to simulate `++arr[i];`) cause a page fault. I guess that
    # because when I replaced the `++arr[i];` with `i += arr[i];` (arr[i] is 0,
    # so don't worry about messing the loop), I saw only 1 extra memory access.
    # print(hex(our_buf_addr_in_workload_info))
    # for i, counter in enumerate(counter_arr):
    #     if counter > min_num_of_expected_accesses_for_elem:
    #         print(hex(i), hex(our_buf_addr_in_workload_info + i * 4), counter)

def _test_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                            qemu_with_GMBEOO_path, guest_image_path,
                            snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        f'--analysis_tool_path "{simple_analysis_path}"')
    
    check_mem_accesses(mem_tracer_output,
                       OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)
    

# TODO: actually run this test. orenmn: I didn't manage to run it, because it
# requires installing `make` and `gcc` on the guest (in order to compile the
# LKM on it), and I had trouble connecting the guest machine to the internet.
def ____test_kernel_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                              qemu_with_GMBEOO_path, guest_image_path,
                              snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    workload_path = os.path.join(this_script_location,
                                 'simple_kernel_memory_intensive_workload_lkm')

    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        os.path.join(this_script_location,
                     'simple_kernel_memory_intensive_workload_runner.bash'),
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--workload_path {workload_path}')

    check_mem_accesses(mem_tracer_output,
                       OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)

def _test_trace_only_CPL3_code_GMBE(this_script_location,
                                   qemu_mem_tracer_script_path,
                                   qemu_with_GMBEOO_path, guest_image_path,
                                   snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--trace_only_CPL3_code_GMBE')
    
    check_mem_accesses(mem_tracer_output,
                       OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)

    num_of_mem_accesses_by_non_CPL3_code_as_str = re.match(
        r'^workload info:.*analysis output:.*'
        r'num_of_mem_accesses_by_non_CPL3_code:(.*)'
        r'num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area:.*',
        mem_tracer_output, re.DOTALL).group(1)
    
    num_of_mem_accesses_by_non_CPL3_code = int(
        num_of_mem_accesses_by_non_CPL3_code_as_str.strip())
    assert(num_of_mem_accesses_by_non_CPL3_code == 0)

def test_invalid_log_of_cmd_args(this_script_location,
                                 qemu_mem_tracer_script_path,
                                 qemu_with_GMBEOO_path, guest_image_path,
                                 snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len "-1" --log_of_GMBE_tracing_ratio 4')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_block_len must be in range [0, 64], but -1 '
               'isn\'t.' in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len "65" --log_of_GMBE_tracing_ratio 4')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_block_len must be in range [0, 64], but 65 '
               'isn\'t.' in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio "-1"')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_tracing_ratio must be in range [0, 64], but -1 '
               'isn\'t.' in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio 65')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_tracing_ratio must be in range [0, 64], but 65 '
               'isn\'t.' in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 32 --log_of_GMBE_tracing_ratio 33')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_block_len + log_of_GMBE_tracing_ratio '
               'must be in range [0, 64], but 32 + 33 = 65 '
               'isn\'t' in e.stderr.decode())
    else:
        assert(False)

def _test_sampling(this_script_location,
                  qemu_mem_tracer_script_path,
                  qemu_with_GMBEOO_path, guest_image_path,
                  snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    mem_tracer_output = get_mem_tracer_error_and_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--log_of_GMBE_block_len 3 --log_of_GMBE_tracing_ratio 4 --verbose '
        f'--print_trace_info')
    
    regex = (
        r'GMBEOO_mask_of_GMBE_block_idx: (\w+)\s*'
        r'---storing start timestamp and starting to trace---.*'
        r'actual_tracing_ratio \(i\.e\. num_of_GMBE_events_since_enabling_GMBEOO / '
        r'num_of_events_written_to_trace_buf\): (\d+\.\d+)')
    mask_of_GMBE_block_idx, actual_tracing_ratio = re.search(
        regex, mem_tracer_output, re.DOTALL).group(1, 2)
    assert(mask_of_GMBE_block_idx.strip() == '78'.zfill(16))
    assert(2 ** 4 - 1 <= float(actual_tracing_ratio.strip()) <= 2 ** 4 + 1)

    mem_tracer_output = get_mem_tracer_error_and_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio 3 --verbose '
        f'--print_trace_info')
    
    mask_of_GMBE_block_idx, actual_tracing_ratio = re.search(
        regex, mem_tracer_output, re.DOTALL).group(1, 2)
    assert(mask_of_GMBE_block_idx.strip() == '70'.zfill(16))
    assert(2 ** 3 - 1 <= float(actual_tracing_ratio.strip()) <= 2 ** 3 + 1)

def _test_trace_fifo_path_cmd_arg(this_script_location,
                                 qemu_mem_tracer_script_path,
                                 qemu_with_GMBEOO_path, guest_image_path,
                                 snapshot_name, host_password):
    with tempfile.TemporaryDirectory() as temp_dir_path:
        trace_fifo_path = os.path.join(temp_dir_path, 'trace_fifo')
        os.mkfifo(trace_fifo_path)
        print_fifo_max_size_cmd = 'cat /proc/sys/fs/pipe-max-size'
        fifo_max_size_as_str = get_output_of_executed_cmd_in_dir(
            print_fifo_max_size_cmd)
        fifo_max_size = int(fifo_max_size_as_str)
        
        fifo_fd = os.open(trace_fifo_path, os.O_NONBLOCK)
        fcntl.fcntl(fifo_fd, F_SETPIPE_SZ, fifo_max_size)
        assert(fcntl.fcntl(fifo_fd, F_GETPIPE_SZ) == fifo_max_size)
        os.close(fifo_fd)

        simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                       'simple_analysis')
        simple_analysis_output_path = os.path.join(temp_dir_path,
                                                   'analysis_output')
        start_simple_analylsis_cmd = (
            f'{simple_analysis_path} {trace_fifo_path} > '
            f'{simple_analysis_output_path} & echo $!')
        simple_analysis_pid = int(
            get_output_of_executed_cmd_in_dir(start_simple_analylsis_cmd))
        try:
            read_file_until_it_contains_str(simple_analysis_output_path,
                                            'Ready to analyze')
            mem_tracer_output = get_mem_tracer_error_and_output(
                this_script_location,
                qemu_mem_tracer_script_path,
                qemu_with_GMBEOO_path,
                guest_image_path,
                snapshot_name,
                host_password,
                get_tests_bin_file_path(this_script_location, 
                                        'simple_user_memory_intensive_workload'),
                f'--trace_fifo_path {trace_fifo_path} --print_trace_info')

            os.kill(simple_analysis_pid, signal.SIGUSR1)
            analysis_output = read_file_until_it_contains_str(
                simple_analysis_output_path, '-----end analysis output-----')
            
            num_of_events_written_to_trace_buf = int(re.search(
                r'num_of_events_written_to_trace_buf: (\d+)',
                mem_tracer_output).group(1))
            num_of_mem_accesses_in_analysis = int(re.search(
                r'num_of_mem_accesses:\s+(\d+)', analysis_output).group(1))
            assert(num_of_events_written_to_trace_buf ==
                   num_of_mem_accesses_in_analysis)
        except:
            raise
        finally:
            # print(read_file(simple_analysis_output_path))
            try:
                os.kill(simple_analysis_pid, SIGKILL)
            except ProcessLookupError:
                pass

def _test_invalid_combination_of_trace_fifo_and_analysis_tool_cmd_args(
        this_script_location, qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path, guest_image_path, snapshot_name, host_password):
    expected_err_message = ('Exactly one of --analysis_tool_path and '
                            '--trace_fifo_path must be specified.')
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'))
    except subprocess.CalledProcessError as e:
        assert(expected_err_message in e.stderr.decode())
    else:
        assert(False)


    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            '--analysis_tool_path a --trace_fifo_path b')
    except subprocess.CalledProcessError as e:
        assert(expected_err_message in e.stderr.decode())
    else:
        assert(False)

def _test_invalid_file_or_dir_cmd_arg(
        this_script_location, qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path, guest_image_path, snapshot_name, host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    must_be_a_file_expected_err_message = ('must be a file path, but')
    must_be_a_fifo_expected_err_message = ('must be a fifo path, but')
    must_be_a_dir_expected_err_message = ('must be a dir path, but')
    must_be_a_file_or_dir_expected_err_message = ('must be a file/dir path, but')
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            'definitely/not/a/file/path',
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" ')

    except subprocess.CalledProcessError as e:
        assert(must_be_a_file_expected_err_message in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            'definitely/not/a/file/path',
            f'--analysis_tool_path "{simple_analysis_path}" ')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_file_expected_err_message in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            '--analysis_tool_path definitely/not/a/file/path')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_file_expected_err_message in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            '--trace_fifo_path /home')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_fifo_expected_err_message in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            'definitely/not/a/dir/path',
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" ')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_dir_expected_err_message in e.stderr.decode())
    else:
        assert(False)

    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--workload_path definitely/not/a/dir/path')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_file_or_dir_expected_err_message in e.stderr.decode())
    else:
        assert(False)

def ___test_durations(this_script_location, qemu_mem_tracer_script_path,
                   qemu_with_GMBEOO_path, guest_image_path, snapshot_name,
                   host_password):
    simple_analysis_path = get_tests_bin_file_path(this_script_location,
                                                   'simple_analysis')
    no_trace_durations = []
    for _ in range(1):
        mem_tracer_output = get_mem_tracer_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_long_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" --dont_trace')
        duration = int(re.search(r'tracing_duration_in_seconds: (\d+)',
                                 mem_tracer_output).group(1))
        if duration == 0:
            raise RuntimeError('The machine running this test is too fast. '
                               'The test should be edited to run longer.')
        no_trace_durations.append(duration)

    print(no_trace_durations)

    with_trace_durations = []
    for _ in range(1):
        mem_tracer_output = get_mem_tracer_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            host_password,
            get_tests_bin_file_path(this_script_location, 
                                    'simple_long_user_memory_intensive_workload'),
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 3 --log_of_GMBE_tracing_ratio 44')
        duration = int(re.search(r'tracing_duration_in_seconds: (\d+)',
                                 mem_tracer_output).group(1))
        if duration == 0:
            raise RuntimeError('The machine running this test is too fast. '
                               'The test should be edited to run longer.')
        with_trace_durations.append(duration)

    print(with_trace_durations)



    # check_mem_accesses(mem_tracer_output,
    #                    OUR_ARR_LEN, BIG_NUM_OF_ITERS_OVER_OUR_ARR)
