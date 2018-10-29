import subprocess
import os
import os.path
import time
import re

def get_output_of_executed_cmd_in_dir(cmd, dir_path='.'):
    print(f'executing cmd (in {dir_path}): {cmd}\n')
    return subprocess.run(cmd, shell=True, check=True, cwd=dir_path,
                   capture_output=True).stdout.strip().decode()

def get_tests_bin_file_path(this_script_location, file_name):
    return os.path.join(this_script_location, 'tests_bin', file_name)

def test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
                                qemu_with_GMBEOO_path, guest_image_path,
                                snapshot_name, host_password):
    workload_runner_path = get_tests_bin_file_path(
        this_script_location, 'dummy_workload_with_funny_test_info')
    analysis_tool_path = get_tests_bin_file_path(
        this_script_location, 'simple_analysis')
    
    run_memory_tracer_cmd = (f'python3.7 {qemu_mem_tracer_script_path} '
                               f'"{guest_image_path}" '
                               f'"{snapshot_name}" '
                               f'"{workload_runner_path}" '
                               f'"{host_password}" '
                               f'"{qemu_with_GMBEOO_path}" '
                               f'--analysis_tool_path "{analysis_tool_path}" '
                               )
                               # f'--verbose ')
    memory_tracer_output = get_output_of_executed_cmd_in_dir(run_memory_tracer_cmd)
    # memory_tracer_output = ('''asonetuhsnt analysis_cmd_args_tuple = (
    # '/mnt/hgfs/qemu_mem_tracer/tests/tests_bin/simple_analysis',
    # 'trace_fifo_1540807664',
    # 'arg2',
    # 'arg3',
    # 'arg4',
    # 'arg5',
    # 'arg6',
    # )
    # ''')
    print(memory_tracer_output)
    # print('aoeu')
    # print(re.search('analysis_cmd_args_tuple = .*', memory_tracer_output, re.DOTALL).group())
    analysis_cmd_args_as_str = re.search('analysis_cmd_args:(.*),',
                                         memory_tracer_output,
                                         re.DOTALL).group(1)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    print(analysis_cmd_args)
    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')
    # memory_tracer_output.find('')

def atest_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
                           qemu_with_GMBEOO_path, guest_image_path,
                           snapshot_name, host_password):
    workload_runner_path = get_tests_bin_file_path(
        this_script_location, 'simple_user_memory_intensive_workload')
    analysis_tool_path = get_tests_bin_file_path(
        this_script_location, 'simple_analysis')
    
    run_memory_tracer_cmd = (f'python3.7 {qemu_mem_tracer_script_path} '
                               f'"{guest_image_path}" '
                               f'"{snapshot_name}" '
                               f'"{workload_runner_path}" '
                               f'"{host_password}" '
                               f'"{qemu_with_GMBEOO_path}" '
                               f'--analysis_tool_path "{analysis_tool_path}" '
                               )
                               # f'--verbose ')
    print(get_output_of_executed_cmd_in_dir(run_memory_tracer_cmd))


# parser = argparse.ArgumentParser(
#     formatter_class=argparse.RawDescriptionHelpFormatter,
#     description='Check whether qemu_mem_tracer produces trace records as '
#                 'expected.\n\n'
#                 'Run `qemu_mem_tracer -h` for help about the cmd arguments.')
# parser.add_argument('qemu_mem_tracer_script_path', type=str)
# parser.add_argument('qemu_with_GMBEOO_path', type=str)
# parser.add_argument('guest_image_path', type=str)
# parser.add_argument('snapshot_name', type=str)
# parser.add_argument('host_password', type=str)
# args = parser.parse_args()

# this_script_path = os.path.realpath(__file__)
# this_script_location = os.path.split(this_script_path)[0]




