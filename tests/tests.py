import subprocess
import os
import os.path
import time
import re

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
    
def _test_workload_without_info(this_script_location, qemu_mem_tracer_script_path,
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
    
    # print(mem_tracer_output)
    # match succeeding means that the workload info isn't printed.
    assert(re.match(
        '^analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL) is not None)

def _test_analysis_tool_cmd_args(this_script_location, qemu_mem_tracer_script_path,
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
    
    # print(mem_tracer_output)
    analysis_cmd_args_as_str = re.match(
        '^workload info:(.*)analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(3)
    analysis_cmd_args = analysis_cmd_args_as_str.split(',')

    # print(analysis_cmd_args)
    assert(analysis_cmd_args[2] == 'arg2')
    assert(analysis_cmd_args[3] == 'arg3')
    assert(analysis_cmd_args[4] == 'arg4')
    assert(analysis_cmd_args[5] == 'arg5')
    assert(analysis_cmd_args[6] == 'arg6')

def _test_user_mem_accesses(this_script_location, qemu_mem_tracer_script_path,
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
    
    # print(mem_tracer_output)
    workload_info_as_str, analysis_output_as_str = re.match(
        '^workload info:(.*)analysis output:(.*)analysis cmd args:(.*)',
        mem_tracer_output, re.DOTALL).group(1, 2)
    print(analysis_output_as_str)

    # print(analysis_cmd_args)
    # assert(analysis_cmd_args[2] == 'arg2')
    # assert(analysis_cmd_args[3] == 'arg3')
    # assert(analysis_cmd_args[4] == 'arg4')
    # assert(analysis_cmd_args[5] == 'arg5')

def _test_kernel_mem_accesses():
    pass
def _test_sampling():
    pass
def _test_trace_only_user_code_GMBE():
    pass


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




