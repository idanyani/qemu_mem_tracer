#!/usr/bin/expect -f
# exp_internal 1

set timeout 360000


set guest_image_path [lindex $argv 0]
set snapshot_name [lindex $argv 1]
set host_password [lindex $argv 2]
set trace_only_user_code_GMBE [lindex $argv 3]
set log_of_GMBE_block_len [lindex $argv 4]
set log_of_GMBE_tracing_ratio [lindex $argv 5]
set analysis_tool_path [lindex $argv 6]
set qemu_mem_tracer_dir_path [lindex $argv 7]
set qemu_with_GMBEOO_dir_path [lindex $argv 8]
set verbose [lindex $argv 9]

if {$verbose == "False"} {
    log_user 0
    stty -echo
}

proc debug_print { msg } {
    if {$::verbose == "True"} {
        send_user -- $msg
    }
}

set make_big_fifo_path "$qemu_mem_tracer_dir_path/tracer_bin/make_big_fifo"
set dummy_fifo_reader_path "$qemu_mem_tracer_dir_path/dummy_fifo_reader.bash"
set verify_pid_dead_path "$qemu_mem_tracer_dir_path/verify_pid_dead.bash"
# set snapshot_name fresh

set fifo_name "trace_fifo"
set fifo_name "trace_fifo_[timestamp]"

debug_print "---create big fifo---\n"
set fifo_size [exec cat /proc/sys/fs/pipe-max-size]
exec $make_big_fifo_path $fifo_name $fifo_size
debug_print "---done creating big fifo $fifo_name (size: $fifo_size)---\n"

debug_print "---spawn a temp reader of $fifo_name to read the mapping of trace events---\n"
set temp_fifo_reader_pid [spawn $dummy_fifo_reader_path $fifo_name "trace_events_mapping"]
set temp_fifo_reader_id $spawn_id

# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS0 of the guest is redirected to a pty that qemu creates.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
debug_print "---starting qemu---\n"
spawn $qemu_with_GMBEOO_dir_path/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pty -serial pty -trace file=$fifo_name
    # -serial pty -serial pty -trace file=my_trace_file
set monitor_id $spawn_id

debug_print "---parsing qemu's message about pseudo-terminals that it opened---\n"
expect -i $monitor_id -ex "serial pty: char device redirected to " {
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

# debug_print "\ncp $qemu_mem_tracer_dir_path/copy_workload_from_host_and_run_it.bash ~/qemu_mem_tracer_temp_dir_for_guest_to_download_from/workload_runner.bash\n"
# set aoeu_cmd [list cp $qemu_mem_tracer_dir_path/copy_workload_from_host_and_run_it.bash /home/orenmn/qemu_mem_tracer_workload_runner.bash]
# eval exec $aoeu_cmd 

debug_print "\n---loading snapshot---\n"
send -i $monitor_id "loadvm $snapshot_name\r"
send -i $monitor_id "cont\r"
# interact -i $monitor_id

# run scp to download test_elf
debug_print "---copying test_elf from host---\n"
# IIUC, `exec echo > $serial_pty` doesn't simulate "hitting Enter" in the
# guest, because the guest's /dev/tty is already open when we overwrite
# /dev/tty with a hard link to the file that /dev/ttyS0 points to.
#     
# therefore, we use `sendkey`.
send -i $monitor_id "sendkey ret\r"

# wait for the scp connection to be established.
expect -i guest_ttyS0_reader_id -ex "password:"
debug_print "\n---authenticating (scp)---\n"

# type the password.
# This works because scp directly opens /dev/tty, which we have overwritten in
# advance, so it is as if scp opens the serial port which is connected to
# guest_password_prompt_pty.
exec echo $host_password > $guest_ttyS0_pty_pid

# the guest would now download elf_test and run it.

debug_print "\n---expecting test info---\n"
expect -i $guest_ttyS0_reader_id -indices -re \
        "-----begin test info-----(.*)-----end test info-----" {
    set test_info [string trim $expect_out(1,string)]
}

debug_print "\n---expecting ready for trace message---\n"
expect -i $guest_ttyS0_reader_id -ex "Ready to trace. Press enter to continue."
send -i $monitor_id "stop\r"

debug_print "---getting ready to trace---\n"
send -i $monitor_id "enable_tracing_single_event_optimization 2\r"
send -i $monitor_id "trace-event guest_mem_before_exec on\r"
send -i $monitor_id "update_trace_only_user_code_GMBE $trace_only_user_code_GMBE\r"
send -i $monitor_id "set_log_of_GMBE_block_len $log_of_GMBE_block_len\r"
send -i $monitor_id "set_log_of_GMBE_tracing_ratio $log_of_GMBE_tracing_ratio\r"

if {$analysis_tool_path != "/dev/null"} {
    set analysis_tool_pid [spawn $analysis_tool_path $fifo_name $test_info]
    set analysis_tool_id $spawn_id
    expect -i $analysis_tool_id -ex "Ready to analyze."
}

debug_print "\n---killing and closing temp_fifo_reader---\n"
exec kill -SIGKILL $temp_fifo_reader_pid
close -i $temp_fifo_reader_id
wait -i $temp_fifo_reader_id
exec $verify_pid_dead_path $temp_fifo_reader_pid


debug_print "---starting to trace---\n"
set tracing_start_time [timestamp]

# Resume the test.
send -i $monitor_id "cont\r"
send -i $monitor_id "sendkey ret\r"

# interact -i $monitor_id

expect -i $guest_ttyS0_reader_id -ex "Stop tracing."
send -i $monitor_id "stop\r"
set tracing_end_time [timestamp]

# sleep 1

debug_print "\n---$analysis_tool_path---\n"
if {$analysis_tool_path != "/dev/null"} {
    debug_print "\n---sending SIGUSR1 to $analysis_tool_path---\n"
    exec kill -SIGUSR1 $analysis_tool_pid

    debug_print "\n---expecting analysis output---\n"
    expect -i $analysis_tool_id -indices -re \
            "-----begin analysis output-----(.*)-----end analysis output-----" {
        set analysis_output [string trim $expect_out(1,string)]
    }

    send_user -- $analysis_output
    # expect -i $analysis_tool_id -indices -re {num_of_mem_accesses: +(\d+)} {
    #     set analysis_tool_output $expect_out(1,string)
    # }
}


set tracing_duration_in_seconds [expr $tracing_end_time - $tracing_start_time]
exec echo "tracing_duration_in_seconds: $tracing_duration_in_seconds" >> test_info.txt

send -i $monitor_id "print_trace_results\r"

debug_print "tracing_duration_in_seconds: $tracing_duration_in_seconds\n"


debug_print "---end run_qemu_and_test.sh---\n"


exec rm $fifo_name

interact -i $monitor_id

