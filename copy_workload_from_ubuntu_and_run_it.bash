#!/bin/bash

host_username="orenmn"
qemu_mem_tracer_location="~"
runner_script_filename="qemu_mem_tracer_workload_runner.bash"

scp ${host_username}@10.0.2.2:${qemu_mem_tracer_location}/\{$runner_script_filename,qemu_mem_tracer_workload\} . && \
chmod 777 $runner_script_filename && \
./$runner_script_filename
