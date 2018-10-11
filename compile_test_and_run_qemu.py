import subprocess


TEST_SOURCE_PATH = '/mnt/hgfs/CSL_QEMU_memory_tracer/qemu_automation/test.c'
RUN_QEMU_SCRIPT_PATH = '/mnt/hgfs/CSL_QEMU_memory_tracer/qemu_automation/run_qemu.bash'
TEST_ELF_NAME = 'test_elf'



subprocess.run('cd ~', shell=True, check=True)

compile_cmd = (f'gcc -Werror -Wall -pedantic '
               f'{TEST_SOURCE_PATH} -o {TEST_ELF_NAME}')
# subprocess.run(compile_cmd, shell=True, check=True, stdout=out2_file)
subprocess.run(compile_cmd, shell=True, check=True)

subprocess.run(RUN_QEMU_SCRIPT_PATH, shell=True, check=True)

