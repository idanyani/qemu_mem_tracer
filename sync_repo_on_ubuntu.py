import subprocess


WINDOWS_REPO_PATH = '/mnt/hgfs/qemu_mem_tracer'
UBUNTU_REPO_PATH = '/home/orenmn/qemu_mem_tracer'
BRANCH_NAME = 'mem_tracer'
GET_CHANGED_FILE_NAMES_CMD = 'git diff --name-only --ignore-submodules'

def get_current_commit_hash(repo_path):
    return subprocess.run('git rev-parse HEAD', shell=True, check=True,
                          cwd=repo_path,
                          capture_output=True).stdout.strip().decode()

def get_current_branch_name(repo_path):
    return subprocess.run('git rev-parse --abbrev-ref HEAD', shell=True,
                          check=True, cwd=repo_path,
                          capture_output=True).stdout.strip().decode()

def get_changed_file_rel_paths(repo_path):
    print(f'running cmd: {GET_CHANGED_FILE_NAMES_CMD} with cwd={repo_path}')
    cmd_output = subprocess.run(GET_CHANGED_FILE_NAMES_CMD, shell=True,
                 check=True, cwd=repo_path, capture_output=True).stdout
    return set(cmd_output.strip().decode().split())

print('starting sync_repo_on_ubuntu')

ubuntu_branch_name = get_current_branch_name(UBUNTU_REPO_PATH)
windows_branch_name = get_current_branch_name(WINDOWS_REPO_PATH)
if ubuntu_branch_name != BRANCH_NAME:

    raise RuntimeError(f'ubuntu_branch_name should be {BRANCH_NAME} but it is '
                       f'{ubuntu_branch_name}')
if windows_branch_name != BRANCH_NAME:
    raise RuntimeError(f'windows_branch_name should be {BRANCH_NAME} but it is '
                       f'{windows_branch_name}')

windows_commit_hash = get_current_commit_hash(WINDOWS_REPO_PATH)
ubuntu_commit_hash = get_current_commit_hash(UBUNTU_REPO_PATH)

ubuntu_changed_file_rel_paths = get_changed_file_rel_paths(UBUNTU_REPO_PATH)
if ubuntu_changed_file_rel_paths:
    print('backing up changes in ubuntu, and going back to a clean branch.')
    print('ubuntu_changed_file_rel_paths:')
    print(ubuntu_changed_file_rel_paths)
    for rel_path in ubuntu_changed_file_rel_paths:
        backup_rel_path = f'{rel_path}_orenmn_backup'
        subprocess.run(f'cp {rel_path} {backup_rel_path}',
                       shell=True, check=True, cwd=UBUNTU_REPO_PATH)
    undo_changes_cmd = (f'git checkout {ubuntu_commit_hash} -- '
                        f'{" ".join(ubuntu_changed_file_rel_paths)}')
    print(undo_changes_cmd)
    subprocess.run(undo_changes_cmd,
                   shell=True, check=True, cwd=UBUNTU_REPO_PATH)
    subprocess.run(f'git checkout {BRANCH_NAME}',
                   shell=True, check=True, cwd=UBUNTU_REPO_PATH)

if windows_commit_hash != ubuntu_commit_hash:
    pull_cmd = f'git pull origin {BRANCH_NAME}'
    print(f'running cmd: {pull_cmd}')
    subprocess.run(pull_cmd, shell=True, check=True, cwd=UBUNTU_REPO_PATH)
    ubuntu_commit_hash = get_current_commit_hash(UBUNTU_REPO_PATH)
    if ubuntu_commit_hash != windows_commit_hash:
        raise RuntimeError(f'ubuntu_commit_hash != windows_commit_hash:\n'
                           f'ubuntu_commit_hash: {ubuntu_commit_hash}\n'
                           f'windows_commit_hash: {windows_commit_hash}')

windows_changed_file_rel_paths = get_changed_file_rel_paths(WINDOWS_REPO_PATH)
if windows_changed_file_rel_paths:
    copy_changed_files_cmd = (
        f'cp -pv --parents {" ".join(windows_changed_file_rel_paths)} {UBUNTU_REPO_PATH}')
    print(f'running cmd: {copy_changed_files_cmd}')
    subprocess.run(copy_changed_files_cmd,
                   shell=True, check=True, cwd=WINDOWS_REPO_PATH)
       

ubuntu_changed_file_rel_paths = get_changed_file_rel_paths(UBUNTU_REPO_PATH)
if ubuntu_changed_file_rel_paths != windows_changed_file_rel_paths:
    raise RuntimeError(
        f'ubuntu_changed_file_rel_paths != windows_changed_file_rel_paths:\n'
        f'ubuntu_changed_file_rel_paths: {ubuntu_changed_file_rel_paths}\n'
        f'windows_changed_file_rel_paths: {windows_changed_file_rel_paths}')

# subprocess.run('git commit -a -m "commit for sync between Windows and Ubuntu"',
#                shell=True, check=True, cwd=QEMU_MEM_TRACER_PATH)
# subprocess.run('git push origin mem_tracer',
#                shell=True, check=True, cwd=QEMU_MEM_TRACER_PATH)
    


