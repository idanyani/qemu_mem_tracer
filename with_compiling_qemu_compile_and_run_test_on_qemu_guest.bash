#!/bin/bash
python3.7 /mnt/hgfs/qemu_automation/sync_repo_on_ubuntu.py && \
python3.7 /mnt/hgfs/qemu_automation/compile_and_run_test_on_qemu_guest.py oren_vm_disk2.qcow2 ready_for_test2 /mnt/hgfs/qemu_automation/test.c 123456 ~/qemu_mem_tracer --compile_qemu