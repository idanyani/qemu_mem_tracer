import subprocess
import shutil
import os
import os.path
import time
import tempfile
import re
import sys

# simple_user_memory_intensive_workload constants
OUR_ARR_LEN = 10000
NUM_OF_ITERS_OVER_OUR_ARR = 5
NUM_OF_ACCESSES_FOR_INC = 2
APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM = (
    NUM_OF_ITERS_OVER_OUR_ARR * NUM_OF_ACCESSES_FOR_INC)
APPROX_NUM_OF_EXPECTED_ACCESSES = (
    OUR_ARR_LEN * APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM)

def execute_cmd_in_dir(cmd, dir_path='.', stdout_dest=subprocess.PIPE,
                       stderr_dest=sys.stderr):
    print(f'executing cmd (in {dir_path}): {cmd}')
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                          stdout=stdout_dest, stderr=stderr_dest)

def get_output_of_executed_cmd_in_dir(cmd, dir_path='.'):
    # return subprocess.run(cmd, shell=True, check=True, cwd=dir_path).stdout.strip().decode()
    return execute_cmd_in_dir(cmd, dir_path).stdout.strip().decode()

def get_tests_bin_file_path(this_script_location, file_name):
    return os.path.join(this_script_location, 'tests_bin', file_name)

def get_mem_tracer_cmd(this_script_location, qemu_mem_tracer_script_path,
                       qemu_with_GMBEOO_path, guest_image_path,
                       snapshot_name, host_password, workload_runner_path,
                       analysis_tool_path, extra_cmd_args=''):
    return (f'python3.7 {qemu_mem_tracer_script_path} '
            f'"{guest_image_path}" '
            f'"{snapshot_name}" '
            f'"{workload_runner_path}" '
            f'"{host_password}" '
            f'"{qemu_with_GMBEOO_path}" '
            f'--analysis_tool_path "{analysis_tool_path}" '
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
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 'dummy_workload_without_info'),
        get_tests_bin_file_path(this_script_location, 'simple_analysis'))
    
    # match succeeding means that the workload info isn't printed.
    assert(re.match(
        '^analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL) is not None)

def _test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'dummy_workload_with_funny_test_info'),
        get_tests_bin_file_path(this_script_location, 'simple_analysis'))
    analysis_cmd_args_as_str = re.match(
        r'^workload info:.*analysis output:.*analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')

def check_mem_accesses(mem_tracer_output):
    workload_info_as_str, our_buf_addr_as_str, counter_arr_as_str = re.match(
        r'^workload info:(.*)analysis output:.*our_buf_addr:(.*)'
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
    assert(APPROX_NUM_OF_EXPECTED_ACCESSES <= counter_arr_sum <=
           APPROX_NUM_OF_EXPECTED_ACCESSES + 100)

    for counter in counter_arr:
        assert(APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM <= counter <=
               APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM + 10)

def _test_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                            qemu_with_GMBEOO_path, guest_image_path,
                            snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        get_tests_bin_file_path(this_script_location, 'simple_analysis'))
    
    check_mem_accesses(mem_tracer_output)
    

def ____test_kernel_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                              qemu_with_GMBEOO_path, guest_image_path,
                              snapshot_name, host_password):
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
        get_tests_bin_file_path(this_script_location, 'simple_analysis'),
        f'--workload_path {workload_path}')

    check_mem_accesses(mem_tracer_output)

def _test_trace_only_CPL3_code_GMBE(this_script_location,
                                   qemu_mem_tracer_script_path,
                                   qemu_with_GMBEOO_path, guest_image_path,
                                   snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        get_tests_bin_file_path(this_script_location, 'simple_analysis'),
        '--trace_only_CPL3_code_GMBE')
    
    check_mem_accesses(mem_tracer_output)

    num_of_mem_accesses_by_non_CPL3_code_as_str = re.match(
        r'^workload info:.*analysis output:.*'
        r'num_of_mem_accesses_by_non_CPL3_code:(.*)'
        r'num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area:.*',
        mem_tracer_output, re.DOTALL).group(1)
    
    num_of_mem_accesses_by_non_CPL3_code = int(
        num_of_mem_accesses_by_non_CPL3_code_as_str.strip())
    assert(num_of_mem_accesses_by_non_CPL3_code == 0)

def test_sampling(this_script_location,
                  qemu_mem_tracer_script_path,
                  qemu_with_GMBEOO_path, guest_image_path,
                  snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_error_and_output(
        this_script_location,
        qemu_mem_tracer_script_path,
        qemu_with_GMBEOO_path,
        guest_image_path,
        snapshot_name,
        host_password,
        get_tests_bin_file_path(this_script_location, 
                                'simple_user_memory_intensive_workload'),
        get_tests_bin_file_path(this_script_location, 'simple_analysis'),
        '--log_of_GMBE_block_len 3 --log_of_GMBE_tracing_ratio 4 --verbose '
        '--print_trace_info')
    
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
        get_tests_bin_file_path(this_script_location, 'simple_analysis'),
        '--log_of_GMBE_block_len 4 --log_of_GMBE_tracing_ratio 3 --verbose '
        '--print_trace_info')
    
    mask_of_GMBE_block_idx, actual_tracing_ratio = re.search(
        regex, mem_tracer_output, re.DOTALL).group(1, 2)
    assert(mask_of_GMBE_block_idx.strip() == '70'.zfill(16))
    assert(2 ** 3 - 1 <= float(actual_tracing_ratio.strip()) <= 2 ** 3 + 1)

def _test_trace_fifo_path_cmd_arg():
    pass


