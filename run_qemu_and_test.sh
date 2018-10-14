#!/usr/bin/expect -f
# exp_internal 1

set host_password_chars [lindex $argv 0]
set guest_image_path [lindex $argv 1]
set pipe_for_serial [lindex $argv 2]
set snapshot_name [lindex $argv 3]
set host_password [lindex $argv 4]

set timeout 5

# spawn sudo chmod 666 /dev/ttyS4
# set serial_chmod_id $spawn_id
# expect -i serial_chmod_id "sudo] password "
# send -i serial_chmod_id "$host_password\r"


# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS4 of the guest is redirected to pipe_for_serial.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pty \
    -serial pty
set monitor_id $spawn_id
expect -i $monitor_id "serial pty: char device redirected to " {
    expect -i $monitor_id -re {^/dev/pts/\d+} {
        set guest_stdout_pty $expect_out(0,string)
    }
}

# puts "-----------------$serial0_pty-----------------"
expect -i $monitor_id "serial pty: char device redirected to " {
    expect -i $monitor_id -re {^/dev/pts/\d+} {
        set password_prompt_pty $expect_out(0,string)
    }
}
# puts "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
# puts "-----------------$serial1_pty-----------------"
# puts "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

# expect -i $monitor_id "(qemu) "

# expect -i monitor_id "sudo] password "
# send -i monitor_id "$host_password\r"

# spawn cat $pipe_for_serial
spawn cat $serial_pty
# exec cat $pipe_for_serial &
set serial_reader_id $spawn_id
# expect -i serial_reader_id "sudo] password "
# send -i serial_reader_id "$host_password\r"

# (required if -nographic was used)
# Switch to monitor interface 
# send "\x01"
# send "c"

# expect -i $monitor_id "(qemu) "

puts "\n---loading snapshot---"
send -i $monitor_id "loadvm $snapshot_name\r"
send -i $monitor_id "cont\r"

# run scp to download test_elf
puts "---copying test_elf from host---\n"

send -i $monitor_id "sendkey ret\r"
# IIUC, the following line doesn't manage to simulate "hitting Enter" in the
# guest, because the guest
# exec echo > $serial_pty


# wait for the scp connection to be established.
# Unfortunately, I didn't manage to remove this ugly hacky sleep, as when scp
# asks for the password, it is neither to stdout nor to stderr! can remove this maybe! and make the test simpler...
# first do bash | tee /dev/ttyS4, and then do everything from there!
# sleep 3
expect -i serial_reader_id "password:"
puts "\n---authenticating (scp)---\n"
sleep 0.1

# type the password.
exec echo $host_password > $serial_pty
# foreach pass_char $host_password_chars {
#     send -i $monitor_id "sendkey $pass_char\r"
# }
# send -i $monitor_id "sendkey ret\r"

# the guest would now download elf_test and run it.

puts "\n---expecting ready for trace message---\n"
expect -i $serial_reader_id "Ready for trace. Press any key to continue."

puts "\n---starting to trace---\n"

# send -i $monitor_id "sendkey ret\r"
exec echo > $serial_pty



expect -i $serial_reader_id "End running test."


interact
