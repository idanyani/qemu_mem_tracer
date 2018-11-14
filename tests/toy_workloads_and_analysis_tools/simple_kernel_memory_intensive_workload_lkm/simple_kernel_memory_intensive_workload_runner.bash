#!/bin/bash

cd ~/workload && \
make && \
insmod ./simple_kernel_memory_intensive_workload_lkm.ko
