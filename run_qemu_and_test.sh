#!/usr/bin/expect -f


# The host's password chars, separated by spaces. E.g. my host's password
# is "123456".
set HOST_PASSWORD_CHARS [list 1 2 3 4 5 6]

set GUEST_IMAGE_PATH "oren_vm_disk2.qcow2"


# start qemu with the monitor redirected to our process' stdin and stdout.
# start the guest not running (-S), as we load a snapshot anyway.
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 \
    -hda $GUEST_IMAGE_PATH -monitor stdio -S

# (required if -nographic was used)
# Switch to monitor interface 
# send "\x01"
# send "c"

expect "(qemu) "

# load snapshot
send "loadvm ready_for_test\r"
send "cont\r"

# run scp to download test_elf
send "sendkey ret\r"

# wait for the scp connection to be established.
sleep 3

# type the password.

foreach pass_char $HOST_PASSWORD_CHARS {
    send "sendkey $pass_char\r"
}
# send "sendkey 2\r"
# send "sendkey 3\r"
# send "sendkey 4\r"
# send "sendkey 5\r"
# send "sendkey 6\r"
send "sendkey ret\r"

# the guest would now download elf_test and run it.

interact
expect "Ready for trace."

