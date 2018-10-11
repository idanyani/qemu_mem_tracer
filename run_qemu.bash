stat run_qemu
./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 \
    -hda oren_vm_disk2.qcow2 -monitor telnet:127.0.0.1:55555,server,nowait
{ echo "loadvm before_scp"; sleep 0.4; } | telnet 127.0.0.1 55555

