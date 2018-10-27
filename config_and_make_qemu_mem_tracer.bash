#!/bin/bash

# $1 - the path of qemu_mem_tracer
# $2 - debug_flag (i.e. --disable-debug or --enable-debug)

echo "running qemu's configure" && \
$1/configure --target-list=x86_64-softmmu --enable-trace-backends=simple $2 && \
echo "running qemu's make" && \
make -C $1