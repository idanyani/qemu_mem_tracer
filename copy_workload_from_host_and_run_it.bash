#!/bin/bash

host_username="orenmn"
download_dir_on_host_path="~/qemu_mem_tracer_temp_dir_for_guest_to_download_from"
runner_script_filename="workload_runner.bash"
workload_dir_name="workload"

scp -r ${host_username}@10.0.2.2:${download_dir_on_host_path}/\{$runner_script_filename,$workload_dir_name\} . && \
chmod 777 $runner_script_filename && \
./$runner_script_filename
