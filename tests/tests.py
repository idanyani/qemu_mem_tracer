import subprocess
import os
import os.path
import time
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
                          snapshot_name, host_password, workload_rel_path,
                          analysis_tool_rel_path):
    workload_runner_path = get_tests_bin_file_path(
        this_script_location, workload_rel_path)
    analysis_tool_path = get_tests_bin_file_path(
        this_script_location, analysis_tool_rel_path)
    run_mem_tracer_cmd = (f'python3.7 {qemu_mem_tracer_script_path} '
                               f'"{guest_image_path}" '
                               f'"{snapshot_name}" '
                               f'"{workload_runner_path}" '
                               f'"{host_password}" '
                               f'"{qemu_with_GMBEOO_path}" '
                               f'--analysis_tool_path "{analysis_tool_path}" '
                               )
                               # f'--verbose ')
    return get_output_of_executed_cmd_in_dir(run_mem_tracer_cmd)
    
def test_workload_without_info(this_script_location, qemu_mem_tracer_script_path,
                               qemu_with_GMBEOO_path, guest_image_path,
                               snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(this_script_location,
                                              qemu_mem_tracer_script_path,
                                              qemu_with_GMBEOO_path,
                                              guest_image_path,
                                              snapshot_name,
                                              host_password,
                                              'dummy_workload_without_info',
                                              'simple_analysis')
    
    # match succeeding means that the workload info isn't printed.
    assert(re.match(
        '^analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL) is not None)

def test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(this_script_location,
                                              qemu_mem_tracer_script_path,
                                              qemu_with_GMBEOO_path,
                                              guest_image_path,
                                              snapshot_name,
                                              host_password,
                                              'dummy_workload_with_funny_test_info',
                                              'simple_analysis')
    
    analysis_cmd_args_as_str = re.match(
        '^workload info:(.*)analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(3)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')

def test_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                            qemu_with_GMBEOO_path, guest_image_path,
                            snapshot_name, host_password):
    mem_tracer_output = get_mem_tracer_output(this_script_location,
                                              qemu_mem_tracer_script_path,
                                              qemu_with_GMBEOO_path,
                                              guest_image_path,
                                              snapshot_name,
                                              host_password,
                                              'simple_user_memory_intensive_workload',
                                              'simple_analysis')

    workload_info_as_str, our_buf_addr_as_str, counter_arr_as_str = re.match(
        '^workload info:(.*)analysis output:(.*)our_buf_addr:(.*)'
        'num_of_mem_accesses_by_user_code:(.*)counter_arr:(.*)'
        'analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1, 3, 5)
    # Use `list` so that counter_arr isn't an iterator (because then `sum`
    # would exhaust it).
    our_buf_addr_in_workload_info = int(workload_info_as_str.strip(), 16)
    our_buf_addr_in_analysis_output = int(our_buf_addr_as_str.strip())
    assert(our_buf_addr_in_workload_info == our_buf_addr_in_analysis_output)
    counter_arr = list(map(int, filter(None, counter_arr_as_str.strip().split(","))))
    counter_arr_sum = sum(counter_arr)
    assert(APPROX_NUM_OF_EXPECTED_ACCESSES <= counter_arr_sum <=
           APPROX_NUM_OF_EXPECTED_ACCESSES + 100)

    # make sure count_arr isn't empty.
    assert(len(counter_arr) == OUR_ARR_LEN)
    for counter in counter_arr:
        assert(APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM <= counter <=
               APPROX_NUM_OF_EXPECTED_ACCESSES_FOR_ELEM + 10)

def _test_kernel_mem_accesses():
    pass
def _test_sampling():
    pass
def _test_trace_only_user_code_GMBE():
    pass


