import subprocess
import os
import os.path
import time


TEST_SOURCE_PATH = '/mnt/hgfs/qemu_automation/test.c'
RUN_QEMU_AND_TEST_EXPECT_SCRIPT_PATH = (
    '/mnt/hgfs/qemu_automation/run_qemu_and_test.sh')
TEST_ELF_NAME = 'test_elf'
TEST_OUTPUT_PATH = 'test_output.txt'


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

try_to_remove(TEST_OUTPUT_PATH)

subprocess.run('cd ~', shell=True, check=True)

compile_cmd = (f'gcc -Werror -Wall -pedantic '
               f'{TEST_SOURCE_PATH} -o {TEST_ELF_NAME}')
# subprocess.run(compile_cmd, shell=True, check=True, stdout=out2_file)
subprocess.run(compile_cmd, shell=True, check=True)

subprocess.run(RUN_QEMU_AND_TEST_EXPECT_SCRIPT_PATH, shell=True, check=True)


output = read_txt_file_when_it_exists(TEST_OUTPUT_PATH)



