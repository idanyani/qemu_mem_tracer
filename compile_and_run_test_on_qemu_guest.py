import subprocess
import os
import os.path
import time

# External constants
TEST_SOURCE_PATH = '/mnt/hgfs/qemu_automation/test.c'
RUN_QEMU_AND_TEST_EXPECT_SCRIPT_PATH = (
    '/mnt/hgfs/qemu_automation/run_qemu_and_test.sh')
HOST_PASSWORD = "123456"
GUEST_IMAGE_PATH = "oren_vm_disk2.qcow2"

# Internal constants
TEST_ELF_NAME = 'test_elf'
TEST_OUTPUT_PATH = 'test_output.txt'
PIPE_FOR_SERIAL_NAME = 'pipe_for_serial'


def read_txt_file_when_it_exists(file_path):
    while not os.path.isfile(file_path):
        time.sleep(1)
    return read_txt_file(file_path)

def read_txt_file(file_path):
    with open(file_path) as f:
        return f.read()

def try_to_remove(file_path):
    try:
        os.remove(file_path)
    except OSError:
        pass

try_to_remove(TEST_ELF_NAME)
try_to_remove(TEST_OUTPUT_PATH)

subprocess.run('cd ~', shell=True, check=True)

compile_cmd = (f'gcc -Werror -Wall -pedantic '
               f'{TEST_SOURCE_PATH} -o {TEST_ELF_NAME}')
subprocess.run(compile_cmd, shell=True, check=True)

try_to_remove(PIPE_FOR_SERIAL_NAME)
subprocess.run(f'mkfifo {PIPE_FOR_SERIAL_NAME}', shell=True, check=True)
subprocess.run(f'cat < {PIPE_FOR_SERIAL_NAME} &', shell=True, check=True)
# Conveniently, the process that redirects the pipe to stdout dies when this
# Python script ends. Use this line instead (and then later `kill -0 <pid>`)
# if you wish to verify that.
# subprocess.run(f'cat < {PIPE_FOR_SERIAL_NAME} &\n echo $!', shell=True, check=True)

host_password_chars = " ".join(list(HOST_PASSWORD))
subprocess.run(f'{RUN_QEMU_AND_TEST_EXPECT_SCRIPT_PATH} '
               f'"{host_password_chars}" "{GUEST_IMAGE_PATH}" '
               f'{PIPE_FOR_SERIAL_NAME} ',
               shell=True, check=True)


output = read_txt_file_when_it_exists(TEST_OUTPUT_PATH)

