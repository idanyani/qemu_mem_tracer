#!/bin/bash

HOST_USERNAME="orenmn"
QEMU_MEM_TRACER_LOCATION="~"

scp ${HOST_USERNAME}@10.0.2.2:${QEMU_MEM_TRACER_LOCATION}/test_elf test_elf_from_ubuntu
chmod 777 test_elf_from_ubuntu
./test_elf_from_ubuntu
