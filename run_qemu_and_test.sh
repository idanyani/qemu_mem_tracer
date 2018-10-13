#!/usr/bin/expect -f

set host_password_chars [lindex $argv 0]
set guest_image_path [lindex $argv 1]
set pipe_for_serial [lindex $argv 2]

# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS0 of the guest is redirected to pipe_for_serial.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pipe:$pipe_for_serial 

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

foreach pass_char $host_password_chars {
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

