import subprocess
import shutil
import os
import os.path
import time
import tempfile
import re

# simple_user_memory_intensive_workload constants
OUR_ARR_LEN = 10000
NUM_OF_ITERS_OVER_OUR_ARR = 5
NUM_OF_ACCESSES_FOR_INC = 2
APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM = (
    NUM_OF_ITERS_OVER_OUR_ARR * NUM_OF_ACCESSES_FOR_INC)
APPROX_NUM_OF_EXPECTED_ACCESSES = (
    OUR_ARR_LEN * APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM)


def get_output_of_executed_cmd_in_dir(cmd, dir_path='.'):
    print(f'executing cmd (in {dir_path}): {cmd}')
    # return subprocess.run(cmd, shell=True, check=True, cwd=dir_path).stdout.strip().decode()
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                          stdout=subprocess.PIPE).stdout.strip().decode()

def get_tests_bin_file_path(this_script_location, file_name):
    return os.path.join(this_script_location, 'tests_bin', file_name)

def get_mem_tracer_output(this_script_location, qemu_mem_tracer_script_path,
                          qemu_with_GMBEOO_path, guest_image_path,
                          snapshot_name, host_password, workload_runner_path,
                          analysis_tool_path, extra_cmd_args=''):
    run_mem_tracer_cmd = (f'python3.7 {qemu_mem_tracer_script_path} '
                               f'"{guest_image_path}" '
                               f'"{snapshot_name}" '
                               f'"{workload_runner_path}" '
                               f'"{host_password}" '
                               f'"{qemu_with_GMBEOO_path}" '
                               f'--analysis_tool_path "{analysis_tool_path}" '
                               f'{extra_cmd_args} '
                               )
                               # f'--verbose ')
    return get_output_of_executed_cmd_in_dir(run_mem_tracer_cmd)
    
def test_workload_without_info(this_script_location, qemu_mem_tracer_script_path,
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

def test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
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
        '^workload info:(.*)analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(3)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')

def check_mem_accesses(mem_tracer_output):
    workload_info_as_str, our_buf_addr_as_str, counter_arr_as_str = re.match(
        '^workload info:(.*)analysis output:(.*)our_buf_addr:(.*)'
        'num_of_mem_accesses_by_CPL3_code:(.*)counter_arr:(.*)'
        'analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1, 3, 5)
    
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

def test_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
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
    

def _test_kernel_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
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

def test_trace_only_CPL3_code_GMBE(this_script_location,
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
        '^workload info:(.*)analysis output:(.*)'
        'num_of_mem_accesses_by_non_CPL3_code:(.*)'
        'num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area:(.*)',
        mem_tracer_output, re.DOTALL).group(3)
    
    num_of_mem_accesses_by_non_CPL3_code = int(
        num_of_mem_accesses_by_non_CPL3_code_as_str.strip())
    assert(num_of_mem_accesses_by_non_CPL3_code == 0)

def _test_sampling():
    pass


