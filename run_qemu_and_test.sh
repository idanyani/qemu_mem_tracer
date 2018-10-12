#!/usr/bin/expect -f

# start qemu with the monitor redirected to our process' stdin and stdout.
# start the guest not running (-S), as we load a snapshot anyway.
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 \
    -hda oren_vm_disk2.qcow2 -monitor stdio -S

# (required if -nographic was used)
# Switch to monitor interface 
# send "\x01"
# send "c"
# expect "(qemu)"

# load snapshot
send "loadvm ready_to_scp2\r"
send "cont\r"

# run scp to download test_elf
send "sendkey ret\r"

# wait for the connection to establish.
sleep 2

# enter the password 123456
send "sendkey 1\r"
send "sendkey 2\r"
send "sendkey 3\r"
send "sendkey 4\r"
send "sendkey 5\r"
send "sendkey 6\r"
send "sendkey ret\r"

# wait for scp to finish copying test_elf to the file named 1.
sleep 1

# ./0, while 0's contents are `chmod 777 1`.
send "sendkey dot\r"
send "sendkey slash\r"
send "sendkey 0\r"
send "sendkey ret\r"

# ./1 i.e. run test_elf
send "sendkey dot\r"
send "sendkey slash\r"
send "sendkey 1\r"
send "sendkey ret\r"

interact

