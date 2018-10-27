#!/usr/bin/expect -f
# exp_internal 1

set timeout 360000

set host_password [lindex $argv 0]
set guest_image_path [lindex $argv 1]
set snapshot_name [lindex $argv 2]
set trace_only_user_code_GMBE [lindex $argv 3]
set log_of_GMBE_block_len [lindex $argv 4]
set log_of_GMBE_tracing_ratio [lindex $argv 5]
# set snapshot_name fresh

set make_big_fifo_source_path "/mnt/hgfs/qemu_automation/make_big_fifo.c"
set simple_analysis_source_path "/mnt/hgfs/qemu_automation/simple_analysis.c"
set simple_analysis_py_path "/mnt/hgfs/qemu_automation/simple_analysis.py"
set dummy_fifo_reader_path "/mnt/hgfs/qemu_automation/dummy_fifo_reader.bash"

# exec cp $simple_analysis_py_path "simple_analysis.py"
# set simple_analysis_py_path "simple_analysis.py"
# set dos2unix_cmd [list dos2unix -q $simple_analysis_py_path]
# eval exec $dos2unix_cmd
# exec dos2unix $simple_analysis_py_path

set fifo_name "trace_fifo"
set fifo_name "trace_fifo_[timestamp]"

set gcc_cmd [list gcc -Werror -Wall -pedantic $make_big_fifo_source_path -o make_big_fifo]
eval exec $gcc_cmd

puts "---create big fifo---"
exec ./make_big_fifo $fifo_name 1048576
puts "---done creating big fifo $fifo_name---"

puts "---spawn a temp reader of $fifo_name to read the mapping of trace events---"
set temp_fifo_reader_pid [spawn $dummy_fifo_reader_path $fifo_name "trace_events_mapping"]
set temp_fifo_reader_id $spawn_id

set gcc_cmd2 [list gcc -Werror -Wall -pedantic $simple_analysis_source_path -o simple_analysis]
eval exec $gcc_cmd2

# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS0 of the guest is redirected to a pty that qemu creates.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
puts "---starting qemu---"
spawn ./qemu_mem_tracer/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pty -serial pty -trace file=$fifo_name
    # -serial pty -serial pty -trace file=my_trace_file
set monitor_id $spawn_id

puts "---parsing qemu's message about pseudo-terminals that it opened---"
expect -i $monitor_id "serial pty: char device redirected to " {
    expect -i $monitor_id -re {^/dev/pts/\d+} {
         set guest_ttyS0_pty_pid $expect_out(0,string)
    }
}

spawn cat $guest_ttyS0_pty_pid
set guest_ttyS0_reader_id $spawn_id

# (required if -nographic was used)
# Switch to monitor interface 
# send "\x01"
# send "c"

puts "\n---loading snapshot---"
send -i $monitor_id "loadvm $snapshot_name\r"
send -i $monitor_id "cont\r"

# run scp to download test_elf
puts "---copying test_elf from host---"

# IIUC, the following line doesn't manage to simulate "hitting Enter" in the
# guest, because the guest's /dev/tty is already open when we overwrite
# /dev/tty with a hard link to the file that /dev/ttyS0 points to.
#     exec echo > $serial_pty
# therefore, we use `sendkey`.
send -i $monitor_id "sendkey ret\r"

# wait for the scp connection to be established.
expect -i guest_ttyS0_reader_id "password:"
puts "\n---authenticating (scp)---"

# type the password.
# This works because scp directly opens /dev/tty, which we have overwritten in
# advance, so it is as if scp opens the serial port which is connected to
# guest_password_prompt_pty.
exec echo $host_password > $guest_ttyS0_pty_pid

# the guest would now download elf_test and run it.

puts "\n---expecting test info---"
expect -i $guest_ttyS0_reader_id -indices -re \
        "-----begin test info-----(.*)-----end test info-----" {
    set test_info [string trim $expect_out(1,string)]
}
exec echo -n "$test_info" > test_info.txt

puts "\n---expecting ready for trace message---"
expect -i $guest_ttyS0_reader_id "Ready for trace. Press any key to continue."
send -i $monitor_id "stop\r"

send -i $monitor_id "set_our_buf_address $test_info\r"

puts "---getting ready to trace---"
send -i $monitor_id "enable_tracing_single_event_optimization 2\r"
send -i $monitor_id "trace-event guest_mem_before_exec on\r"
send -i $monitor_id "update_trace_only_user_code_GMBE $trace_only_user_code_GMBE\r"
send -i $monitor_id "set_log_of_GMBE_block_len $log_of_GMBE_block_len\r"
send -i $monitor_id "set_log_of_GMBE_tracing_ratio $log_of_GMBE_tracing_ratio\r"
# set simple_analysis_pid [spawn ./simple_analysis $fifo_name $test_info]
set simple_analysis_pid [spawn python3.7 $simple_analysis_py_path $fifo_name $test_info]
set simple_analysis_id $spawn_id
sleep 1

puts "\n---killing and closing temp_fifo_reader---"
exec kill -SIGKILL $temp_fifo_reader_pid
close -i $temp_fifo_reader_id


puts "---starting to trace---"
set test_start_time [timestamp]

# Resume the test.
send -i $monitor_id "cont\r"
send -i $monitor_id "sendkey ret\r"

# interact -i $monitor_id

expect -i $guest_ttyS0_reader_id "End running test."
send -i $monitor_id "stop\r"
set test_end_time [timestamp]

sleep 1

exec kill -SIGUSR1 $simple_analysis_pid

expect -i $simple_analysis_id -indices -re {num_of_mem_accesses: +(\d+)} {
    set simple_analysis_output $expect_out(1,string)
}


set test_time [expr $test_end_time - $test_start_time]
exec echo "test_time: $test_time" >> test_info.txt

send -i $monitor_id "print_trace_results\r"

puts "test_time: $test_time"
puts "simple_analysis_output: $simple_analysis_output"


puts "---end run_qemu_and_test.sh---"


exec rm $fifo_name

interact -i $monitor_id

