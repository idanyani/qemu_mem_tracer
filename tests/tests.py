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

NUM_OF_MILLISECONDS_IN_SECOND = 1000

# constants from common_memory_intensive.h and long_memory_intensive.h
OUR_ARR_LEN = 10000
SMALL_NUM_OF_ITERS_OVER_OUR_ARR = 5
BIG_NUM_OF_ITERS_OVER_OUR_ARR = 500

NUM_OF_ACCESSES_FOR_INC = 2

VERBOSE_LEVEL = 0

TOY_WORKLOAD_AND_ANALYSIS_TOOLS_DIR_REL_PATH = 'toy_workloads_and_analysis_tools'
TESTS_BIN_DIR_REL_PATH = os.path.join(TOY_WORKLOAD_AND_ANALYSIS_TOOLS_DIR_REL_PATH,
                                      'tests_bin')


def read_file_until_it_contains_str(file_path, expected_str):
    if VERBOSE_LEVEL:
        print(f'expecting to find "{expected_str}" in {file_path} ')
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
    if VERBOSE_LEVEL:
        print(f'executing cmd (in {dir_path}): {cmd} ')
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                          stdout=stdout_dest, stderr=stderr_dest)

def get_output_of_executed_cmd_in_dir(cmd, dir_path='.'):
    return execute_cmd_in_dir(cmd, dir_path).stdout.strip().decode()

def get_toy_elf_path(this_script_location, file_name):
    return os.path.join(this_script_location, TESTS_BIN_DIR_REL_PATH, file_name)

def get_toy_bash_path(this_script_location, file_name):
    return os.path.join(this_script_location,
                        TOY_WORKLOAD_AND_ANALYSIS_TOOLS_DIR_REL_PATH, file_name)

def get_mem_tracer_cmd(this_script_location, qemu_mem_tracer_script_path,
                       qemu_with_GMBEOO_path, guest_image_path,
                       snapshot_name, extra_cmd_args=''):
    if VERBOSE_LEVEL > 1:
        verbose_cmd_arg = '--verbose '
    else:
        verbose_cmd_arg = ' '
    return (f'python3.7 {qemu_mem_tracer_script_path} '
            f'"{guest_image_path}" '
            f'"{snapshot_name}" '
            f'"{qemu_with_GMBEOO_path}" '
            f'{extra_cmd_args} '
            f'{verbose_cmd_arg} '
            )

def get_mem_tracer_error_and_output(*args, **kwargs):
    cmd_result = execute_cmd_in_dir(get_mem_tracer_cmd(*args, **kwargs),
                                    stderr_dest=subprocess.PIPE)
    return cmd_result.stderr.strip().decode() + cmd_result.stdout.strip().decode()

def get_mem_tracer_output(*args, **kwargs):
    return get_output_of_executed_cmd_in_dir(get_mem_tracer_cmd(*args, **kwargs))
    
def check_mem_tracer_output_attention(mem_tracer_output):
    if 'ATTENTION' in mem_tracer_output:
        print(mem_tracer_output)
        print('\n\n---mem_tracer_output contains an ATTENTION message. '
              'You should probably take a look.---\n\n')

def _test_workload_without_info(this_script_location, qemu_mem_tracer_script_path,
                               qemu_with_GMBEOO_path, guest_image_path,
                               snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_bash_path(this_script_location, 'empty_workload.bash')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--workload_path_on_host {workload_path} ')
    
    # match succeeding means that the workload info isn't printed.
    assert(re.match(
        '^tracing_duration_in_milliseconds:.*analysis output:.*analysis cmd args:.*',
        mem_tracer_output, re.DOTALL) is not None)

def _test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(this_script_location, 
                                     'dummy_workload_with_funny_test_info')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--dont_add_communications_with_host_to_workload '
        f'--workload_path_on_host {workload_path} ')
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
        r'^workload info:(.*)tracing_duration_in_milliseconds:.*our_buf_addr:(.*)'
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
                            snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(
        this_script_location, 'simple_user_memory_intensive_workload')

    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--dont_add_communications_with_host_to_workload '
        f'--workload_path_on_host {workload_path} '
        )
    
    # print(mem_tracer_output)
    check_mem_accesses(mem_tracer_output,
                       OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)
    

def ______test_kernel_mem_accesses(this_script_location,
                             qemu_mem_tracer_script_path,
                             qemu_with_GMBEOO_path, guest_image_path,
                             snapshot_name):
    # TODO: implement and run this test.
    # orenmn: I didn't manage to run it, because it requires installing `make`
    # and `gcc` on the guest (in order to compile the LKM on it), and I had 
    # trouble connecting the guest machine to the internet.
    # 
    # The relevant files are in the directory
    # simple_kernel_memory_intensive_workload_lkm.
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    # check_mem_accesses(mem_tracer_output,
    #                    OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)
    raise NotImplementedError


def _test_trace_only_CPL3_code_GMBE(this_script_location,
                                   qemu_mem_tracer_script_path,
                                   qemu_with_GMBEOO_path, guest_image_path,
                                   snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--trace_only_CPL3_code_GMBE '
        f'--dont_add_communications_with_host_to_workload '
        f'--workload_path_on_host {workload_path} ')
    
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

def _test_invalid_log_of_cmd_args(this_script_location,
                                 qemu_mem_tracer_script_path,
                                 qemu_with_GMBEOO_path, guest_image_path,
                                 snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len "-1" --log_of_GMBE_tracing_ratio 4 '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len "65" --log_of_GMBE_tracing_ratio 4 '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio "-1" '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio 65 '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--log_of_GMBE_block_len 32 --log_of_GMBE_tracing_ratio 33 '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
    except subprocess.CalledProcessError as e:
        assert('log_of_GMBE_block_len + log_of_GMBE_tracing_ratio '
               'must be in range [0, 64], but 32 + 33 = 65 '
               'isn\'t' in e.stderr.decode())
    else:
        assert(False)

def _test_sampling(this_script_location,
                  qemu_mem_tracer_script_path,
                  qemu_with_GMBEOO_path, guest_image_path,
                  snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')
    mem_tracer_output = get_mem_tracer_error_and_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--log_of_GMBE_block_len 3 --log_of_GMBE_tracing_ratio 4 --verbose '
        f'--print_trace_info '
        f'--dont_add_communications_with_host_to_workload '
        f'--workload_path_on_host {workload_path} ')
    check_mem_tracer_output_attention(mem_tracer_output)

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
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio 3 --verbose '
        f'--print_trace_info '
        f'--dont_add_communications_with_host_to_workload '
        f'--workload_path_on_host {workload_path} ')
    check_mem_tracer_output_attention(mem_tracer_output)
    
    mask_of_GMBE_block_idx, actual_tracing_ratio = re.search(
        regex, mem_tracer_output, re.DOTALL).group(1, 2)
    assert(mask_of_GMBE_block_idx.strip() == '70'.zfill(16))
    assert(2 ** 3 - 1 <= float(actual_tracing_ratio.strip()) <= 2 ** 3 + 1)

def _test_trace_fifo_path_cmd_arg(this_script_location,
                                 qemu_mem_tracer_script_path,
                                 qemu_with_GMBEOO_path, guest_image_path,
                                 snapshot_name):
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')

    with tempfile.TemporaryDirectory() as temp_dir_path:
        trace_fifo_path = os.path.join(temp_dir_path, 'trace_fifo')
        os.mkfifo(trace_fifo_path)
        print_fifo_max_size_cmd = 'cat /proc/sys/fs/pipe-max-size '
        fifo_max_size_as_str = get_output_of_executed_cmd_in_dir(
            print_fifo_max_size_cmd)
        fifo_max_size = int(fifo_max_size_as_str)
        
        fifo_fd = os.open(trace_fifo_path, os.O_NONBLOCK)
        fcntl.fcntl(fifo_fd, F_SETPIPE_SZ, fifo_max_size)
        assert(fcntl.fcntl(fifo_fd, F_GETPIPE_SZ) == fifo_max_size)
        os.close(fifo_fd)

        simple_analysis_path = get_toy_elf_path(this_script_location,
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
                f'--trace_fifo_path {trace_fifo_path} --print_trace_info '
                f'--dont_add_communications_with_host_to_workload '
                f'--workload_path_on_host {workload_path} ')
            check_mem_tracer_output_attention(mem_tracer_output)

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
        qemu_with_GMBEOO_path, guest_image_path, snapshot_name):
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host /bin/date ')
    except subprocess.CalledProcessError as e:
        pass
    else:
        assert(False)


    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            guest_image_path,
            snapshot_name,
            f'--analysis_tool_path a --trace_fifo_path b'
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host /bin/date ')
    except subprocess.CalledProcessError as e:
        pass
    else:
        assert(False)

def _test_invalid_file_or_dir_cmd_arg(
        this_script_location, qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path, guest_image_path, snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')
    must_be_a_file_expected_err_message = ('must be a file path, but')
    must_be_a_fifo_expected_err_message = ('must be a fifo path, but')
    must_be_a_dir_expected_err_message = ('must be a dir path, but')
    try:
        get_mem_tracer_error_and_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            qemu_with_GMBEOO_path,
            'definitely/not/a/file/path',
            snapshot_name,
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')

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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host definitely/not/a/file/path')
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
            '--analysis_tool_path definitely/not/a/file/path '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            '--trace_fifo_path /home '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
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
            f'--analysis_tool_path "{simple_analysis_path}" '
            f'--dont_add_communications_with_host_to_workload '
            f'--workload_path_on_host {workload_path} ')
    except subprocess.CalledProcessError as e:
        assert(must_be_a_dir_expected_err_message in e.stderr.decode())
    else:
        assert(False)
    

def print_workload_durations(this_script_location,
                             qemu_mem_tracer_script_path,
                             qemu_with_GMBEOO_path, guest_image_path,
                             snapshot_name, num_of_iterations,
                             workload_path_on_host=None,
                             workload_path_on_guest=None,
                             log_of_GMBE_block_len=16,
                             log_of_GMBE_tracing_ratio=10,
                             run_native_only=False,
                             dont_add_communications=False,
                             timeout=None):
    assert(num_of_iterations > 0)
    def get_avg(durations):
        return sum(durations) / num_of_iterations

    def get_standard_deviation(nums, avg):
        squares = [(num - avg) ** 2 for num in nums]
        return get_avg(squares) ** 0.5

    if workload_path_on_guest:
        workload_path_cmd_arg_str_for_non_native = (
            f'--workload_path_on_guest {workload_path_on_guest} ')
    else:
        assert(workload_path_on_host)
        workload_path_cmd_arg_str_for_non_native = (
            f'--workload_path_on_host {workload_path_on_host} ')

    if timeout:
        timeout_cmd_arg_str = '--timeout {timeout}'
    else:
        timeout_cmd_arg_str = ''

    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    native_durations = []
    no_trace_durations = []
    with_trace_durations = []
    mem_accesses_by_non_CPL3_code_ratios = []
    for i in range(num_of_iterations):
        print(f'iteration number {i + 1}...')
        native_mem_tracer_output = get_mem_tracer_output(
            this_script_location,
            qemu_mem_tracer_script_path,
            'dummy_qemu_with_GMBEOO_path',
            'dummy_guest_image_path',
            'dummy_snapshot_name',
            f'--dont_use_qemu '
            f'--workload_path_on_host {workload_path_on_host} '
            f'{timeout_cmd_arg_str} ')
        native_duration = (int(re.search(r'tracing_duration_in_milliseconds: (\d+)',
                               native_mem_tracer_output).group(1)) / 
                           NUM_OF_MILLISECONDS_IN_SECOND)
        print(f'native_duration: {native_duration}')
        native_durations.append(native_duration)                
        # if native_duration < 1:
        #     raise RuntimeError('The machine running this test is too fast. '
        #                        'The test should be edited to run longer.')

        if not run_native_only:
            if dont_add_communications:
                dont_add_communications_cmd_arg_str = (
                    '--dont_add_communications_with_host_to_workload')
            else:
                dont_add_communications_cmd_arg_str = ''

            no_trace_mem_tracer_output = get_mem_tracer_output(
                this_script_location,
                qemu_mem_tracer_script_path,
                qemu_with_GMBEOO_path,
                guest_image_path,
                snapshot_name,
                f'--dont_trace {workload_path_cmd_arg_str_for_non_native} '
                f'{dont_add_communications_cmd_arg_str} {timeout_cmd_arg_str} '
                )
            no_trace_duration = (int(re.search(r'tracing_duration_in_milliseconds: (\d+)',
                                     no_trace_mem_tracer_output).group(1)) /
                                 NUM_OF_MILLISECONDS_IN_SECOND)
            print(f'no_trace_duration: {no_trace_duration}')
            no_trace_durations.append(no_trace_duration)


            with_trace_mem_tracer_output = get_mem_tracer_output(
                this_script_location,
                qemu_mem_tracer_script_path,
                qemu_with_GMBEOO_path,
                guest_image_path,
                snapshot_name,
                f'--analysis_tool_path "{simple_analysis_path}" '
                f'--log_of_GMBE_block_len {log_of_GMBE_block_len} '
                f'--log_of_GMBE_tracing_ratio {log_of_GMBE_tracing_ratio} '
                f'--print_trace_info '
                f'{workload_path_cmd_arg_str_for_non_native} '
                f'{dont_add_communications_cmd_arg_str} {timeout_cmd_arg_str} ')
            check_mem_tracer_output_attention(with_trace_mem_tracer_output)

            with_trace_duration = (int(re.search(r'tracing_duration_in_milliseconds: (\d+)',
                                       with_trace_mem_tracer_output).group(1)) /
                                   NUM_OF_MILLISECONDS_IN_SECOND)
            print(f'with_trace_duration: {with_trace_duration}')
            with_trace_durations.append(with_trace_duration)



            # print(with_trace_mem_tracer_output)
            num_of_mem_accesses_by_non_CPL3_code_as_str, num_of_mem_accesses_as_str = (
                re.search(r'num_of_mem_accesses_by_non_CPL3_code:\s+(\d+).*'
                          r'num_of_mem_accesses:\s+(\d+)',
                          with_trace_mem_tracer_output, re.DOTALL).group(1, 2))
            num_of_mem_accesses_by_non_CPL3_code = int(
                num_of_mem_accesses_by_non_CPL3_code_as_str)
            num_of_mem_accesses = int(num_of_mem_accesses_as_str)

            # print(f'num_of_mem_accesses: {num_of_mem_accesses} ')
            assert(num_of_mem_accesses > 0)
            mem_accesses_by_non_CPL3_code_ratios.append(
                num_of_mem_accesses_by_non_CPL3_code / num_of_mem_accesses)


            # print(with_trace_mem_tracer_output)


    avg_native_duration = get_avg(native_durations)
    avg_no_trace_duration = get_avg(no_trace_durations)
    avg_with_trace_duration = get_avg(with_trace_durations)
    avg_mem_accesses_by_non_CPL3_code_ratio = get_avg(
        mem_accesses_by_non_CPL3_code_ratios)
    native_duration_SD = get_standard_deviation(native_durations,
                                                avg_native_duration)
    no_trace_duration_SD = get_standard_deviation(no_trace_durations,
                                                  avg_no_trace_duration)
    with_trace_duration_SD = get_standard_deviation(with_trace_durations,
                                                    avg_with_trace_duration)
    mem_accesses_by_non_CPL3_code_ratio_SD = get_standard_deviation(
        mem_accesses_by_non_CPL3_code_ratios,
        avg_mem_accesses_by_non_CPL3_code_ratio)

    print(f'avg_native_duration: {avg_native_duration}, SD: {native_duration_SD} '
          f'({native_durations})')
    if not run_native_only:
        print(f'avg_no_trace_duration: {avg_no_trace_duration}, '
              f'SD: {no_trace_duration_SD} ({no_trace_durations})')
        print(f'avg_with_trace_duration: {avg_with_trace_duration}, '
              f'SD: {with_trace_duration_SD} ({with_trace_durations})')
        print(f'avg_mem_accesses_by_non_CPL3_code_ratio: '
              f'{avg_mem_accesses_by_non_CPL3_code_ratio}, '
              f'SD: {mem_accesses_by_non_CPL3_code_ratio_SD} '
              f'({mem_accesses_by_non_CPL3_code_ratios})')

        print(f'avg_with_trace_duration / avg_native_duration: '
              f'{avg_with_trace_duration / avg_native_duration} ')
        print(f'avg_with_trace_duration / avg_no_trace_duration: '
              f'{avg_with_trace_duration / avg_no_trace_duration} ')

def _test_timeout(this_script_location,
                 qemu_mem_tracer_script_path,
                 qemu_with_GMBEOO_path, guest_image_path,
                 snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = get_toy_bash_path(this_script_location,
                                      'sleep_forever_workload.bash')
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--workload_path_on_host {workload_path} --timeout 7')
    
    duration = (int(re.search(r'tracing_duration_in_milliseconds: (\d+)',
                              mem_tracer_output).group(1)) /
                NUM_OF_MILLISECONDS_IN_SECOND)
    # print(duration)
    assert(6.7 <= duration <= 25)

def _test_workload_path_on_guest(this_script_location,
                                qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name):
    simple_analysis_path = get_toy_elf_path(this_script_location,
                                            'simple_analysis')
    workload_path = '\~/toy_workloads/simple_user_memory_intensive_workload'
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--workload_path_on_guest {workload_path} '
        f'--dont_add_communications_with_host_to_workload '
        f'--print_trace_info ')
    # print(mem_tracer_output)
    check_mem_accesses(mem_tracer_output,
                       OUR_ARR_LEN, SMALL_NUM_OF_ITERS_OVER_OUR_ARR)



def test_toy_workload_durations(this_script_location,
                                qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name):
    workload_path = get_toy_elf_path(this_script_location, 
                                     'simple_user_memory_intensive_workload')
                                     # 'simple_long_user_memory_intensive_workload')
    print_workload_durations(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path, guest_image_path,
        snapshot_name,
        2,
        workload_path_on_guest='\~/toy_workloads/simple_user_memory_intensive_workload',
        workload_path_on_host=workload_path,
        log_of_GMBE_tracing_ratio=10,
        dont_add_communications=True)

def _test_mcf_workload(this_script_location,
                      qemu_mem_tracer_script_path,
                      qemu_with_GMBEOO_path, guest_image_path,
                      snapshot_name):
    # print_workload_durations(
    #     this_script_location,
    #     qemu_mem_tracer_script_path,
    #     qemu_with_GMBEOO_path, guest_image_path,
    #     snapshot_name,
    #     '429.mcf/run.sh',
    #     1, workload_path='429.mcf/workload',
    #     # log_of_GMBE_tracing_ratio=0,
    #     )
    #     # run_native_only=True)
    # simple_analysis_path = get_toy_elf_path(this_script_location,
    #                                         'simple_analysis')
    workload_path = '\~/429.mcf/run.sh'
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        f'--analysis_tool_path "{simple_analysis_path}" '
        f'--workload_path_on_guest {workload_path} --timeout 10 '
        f'--print_trace_info ')
    num_of_mem_accesses_as_str = (
        re.search(r'num_of_mem_accesses:\s+(\d+)',
                  mem_tracer_output, re.DOTALL).group(1))
    num_of_mem_accesses = int(num_of_mem_accesses_as_str)
    assert(num_of_mem_accesses > 0)
    print(mem_tracer_output)



