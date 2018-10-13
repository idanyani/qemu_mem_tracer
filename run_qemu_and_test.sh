#!/usr/bin/expect -f

set host_password_chars [lindex $argv 0]
set guest_image_path [lindex $argv 1]
set pipe_for_serial [lindex $argv 2]

spawn cat $pipe_for_serial
# exec cat $pipe_for_serial &
set serial_reader_id $spawn_id

# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS0 of the guest is redirected to pipe_for_serial.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pipe:$pipe_for_serial
set monitor_id $spawn_id


# (required if -nographic was used)
# Switch to monitor interface 
# send "\x01"
# send "c"

expect -i $monitor_id "(qemu) "

puts "\n---loading snapshot---"
send -i $monitor_id "loadvm ready_for_test\r"
send -i $monitor_id "cont\r"

# run scp to download test_elf
puts "---copying test_elf from host---\n"
send -i $monitor_id "sendkey ret\r"
# wait for the scp connection to be established.
# we can remove this maybe! and make the test simpler...
# first do bash | tee /dev/ttyS0, and then do everything from there!
sleep 3

# type the password.
foreach pass_char $host_password_chars {
    send -i $monitor_id "sendkey $pass_char\r"
}
send -i $monitor_id "sendkey ret\r"

# the guest would now download elf_test and run it.

expect -i $serial_reader_id "Ready for trace. Press any key to continue."

puts "\n---starting to trace---\n"

send -i $monitor_id "sendkey ret\r"



expect -i $serial_reader_id "End running test."

# flush stdout
# sleep 2

# interact
