#!/bin/bash

HOST_USERNAME="orenmn"

scp ${HOST_USERNAME}@10.0.2.2:test_elf test_elf_from_ubuntu
chmod 777 test_elf_from_ubuntu
./test_elf_from_ubuntu
