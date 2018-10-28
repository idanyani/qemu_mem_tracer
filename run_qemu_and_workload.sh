#!/usr/bin/expect -f
# exp_internal 1

set timeout 360000


set guest_image_path [lindex $argv 1]
set snapshot_name [lindex $argv 2]
set host_password [lindex $argv 0]
set trace_only_user_code_GMBE [lindex $argv 3]
set log_of_GMBE_block_len [lindex $argv 4]
set log_of_GMBE_tracing_ratio [lindex $argv 5]
set qemu_mem_tracer_dir_path [lindex $argv 6]
set analysis_tool_path [lindex $argv 7]

set make_big_fifo_path "$qemu_mem_tracer_dir_path/tracer_bin/make_big_fifo"
set dummy_fifo_reader_path "$qemu_mem_tracer_dir_path/dummy_fifo_reader.bash"
# set snapshot_name fresh

set fifo_name "trace_fifo"
set fifo_name "trace_fifo_[timestamp]"

puts "---create big fifo---"
set fifo_size [exec cat /proc/sys/fs/pipe-max-size]
exec $make_big_fifo_path $fifo_name $fifo_size
puts "---done creating big fifo $fifo_name (size: $fifo_size)---"

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

# puts "\ncp $qemu_mem_tracer_dir_path/copy_workload_from_host_and_run_it.bash ~/qemu_mem_tracer_temp_dir_for_guest_to_download_from/workload_runner.bash"
# set aoeu_cmd [list cp $qemu_mem_tracer_dir_path/copy_workload_from_host_and_run_it.bash /home/orenmn/qemu_mem_tracer_workload_runner.bash]
# eval exec $aoeu_cmd 

puts "\n---loading snapshot---"
send -i $monitor_id "loadvm $snapshot_name\r"
send -i $monitor_id "cont\r"

# run scp to download test_elf
puts "---copying test_elf from host---"
# IIUC, `exec echo > $serial_pty` doesn't simulate "hitting Enter" in the
# guest, because the guest's /dev/tty is already open when we overwrite
# /dev/tty with a hard link to the file that /dev/ttyS0 points to.
#     
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
# interact -i $monitor_id

puts "\n---expecting test info---"
expect -i $guest_ttyS0_reader_id -indices -re \
        "-----begin test info-----(.*)-----end test info-----" {
    set test_info [string trim $expect_out(1,string)]
}
exec echo -n "$test_info" > test_info.txt

puts "\n---expecting ready for trace message---"
expect -i $guest_ttyS0_reader_id "Ready to trace. Press enter to continue."
send -i $monitor_id "stop\r"

send -i $monitor_id "set_our_buf_address $test_info\r"

puts "---getting ready to trace---"
send -i $monitor_id "enable_tracing_single_event_optimization 2\r"
send -i $monitor_id "trace-event guest_mem_before_exec on\r"
send -i $monitor_id "update_trace_only_user_code_GMBE $trace_only_user_code_GMBE\r"
send -i $monitor_id "set_log_of_GMBE_block_len $log_of_GMBE_block_len\r"
send -i $monitor_id "set_log_of_GMBE_tracing_ratio $log_of_GMBE_tracing_ratio\r"

if {$analysis_tool_path != ""} {
    set simple_analysis_pid [spawn analysis_tool_path $fifo_name $test_info]
    set simple_analysis_id $spawn_id
    expect -i $simple_analysis_id "Ready to analyze."
}

puts "\n---killing and closing temp_fifo_reader---"
exec kill -SIGKILL $temp_fifo_reader_pid
close -i $temp_fifo_reader_id
exec 


puts "---starting to trace---"
set test_start_time [timestamp]

# Resume the test.
send -i $monitor_id "cont\r"
send -i $monitor_id "sendkey ret\r"

# interact -i $monitor_id

expect -i $guest_ttyS0_reader_id "Stop tracing."
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

