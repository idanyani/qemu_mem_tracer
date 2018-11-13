#!/usr/bin/expect -f
# exp_internal 1

set timeout 360000

# Silent various messages.
log_user 0
stty -echo

# necessary if workload_info or analysis_output are very large.
match_max -d 1000000

set guest_image_path [lindex $argv 0]
set snapshot_name [lindex $argv 1]
set workload_runner_path [lindex $argv 2]
set write_script_to_serial_path [lindex $argv 3]
set trace_only_CPL3_code_GMBE [lindex $argv 4]
set log_of_GMBE_block_len [lindex $argv 5]
set log_of_GMBE_tracing_ratio [lindex $argv 6]
set analysis_tool_path [lindex $argv 7]
set trace_fifo_path [lindex $argv 8]
set qemu_with_GMBEOO_dir_path [lindex $argv 9]
set verbose [lindex $argv 10]
set dont_exit_qemu_when_done [lindex $argv 11]
set print_trace_info [lindex $argv 12]
set dont_trace [lindex $argv 13]

proc debug_print {msg} {
    if {$::verbose == "True"} {
        send_error -- $msg
    }
}


debug_print "---start run_qemu_and_workload.sh---\n"


# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   Both /dev/ttyS0 and /dev/ttyS1 of the guest are redirected to pseudo
#   terminals that qemu creates.
#   The guest doesn't start running (-S), as we load a snapshot anyway.
debug_print "---starting qemu---\n"
spawn $qemu_with_GMBEOO_dir_path/x86_64-softmmu/qemu-system-x86_64 -m 2560 -S \
    -hda $guest_image_path -monitor stdio \
    -serial pty -serial pty
set monitor_id $spawn_id

debug_print "---parsing qemu's message about pseudo-terminals that it opened---\n"
expect -i $monitor_id "serial pty: char device redirected to " {
    expect -i $monitor_id -re {^/dev/pts/\d+} {
         set guest_ttyS0_pty_path $expect_out(0,string)
    }
}

spawn cat $guest_ttyS0_pty_path
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

debug_print "\n---writing $workload_runner_path to $guest_ttyS0_pty_path---\n"
exec python3.7 $write_script_to_serial_path $workload_runner_path $guest_ttyS0_pty_path

# The guest would now receive the workload_runner script and run it.

debug_print "\n---expecting workload info---\n"
expect -i $guest_ttyS0_reader_id -indices -re \
        "-----begin workload info-----(.*)-----end workload info-----" {
    set workload_info [string trim $expect_out(1,string)]
}
if {$workload_info != ""} {
    send_user "workload info:\n"
    send_user -- "$workload_info\n"
}

debug_print "\n---expecting ready to trace message---\n"
expect {
    -i $guest_ttyS0_reader_id
    "Ready to trace. Press enter to continue" {}
    eof {
        debug_print "it seems that guest_ttyS0_reader terminated unexpectedly."
        exit 1
    }
}
send -i $monitor_id "stop\r"



if {$analysis_tool_path != "/dev/null"} {
    debug_print "\n---spawning analysis tool---\n"
    # https://stackoverflow.com/questions/5728656/tcl-split-string-by-arbitrary-number-of-whitespaces-to-a-list/5731098#5731098
    set workload_info_with_spaces [join $workload_info " "]
    set analysis_tool_pid [eval spawn $analysis_tool_path $trace_fifo_path $workload_info_with_spaces]
    set analysis_tool_id $spawn_id
    debug_print "\n---expecting ready to analyze message---\n"
    expect {
        -i $analysis_tool_id
        "Ready to analyze" {}
        eof {
            debug_print "it seems that $analysis_tool_path terminated unexpectedly."
            exit 1
        }
    }
}

if {$::dont_trace == "False"} {
    debug_print "---configure qemu_with_GMBEOO for tracing---\n"
    send -i $monitor_id "enable_GMBEOO\r"
    # Enabling GMBEOO before setting the trace file causes the mapping of events to
    # never be written to our FIFO.
    send -i $monitor_id "trace-file set $trace_fifo_path\r"
    send -i $monitor_id "trace-event guest_mem_before_exec on\r"
    send -i $monitor_id "update_trace_only_CPL3_code_GMBE $trace_only_CPL3_code_GMBE\r"
    send -i $monitor_id "set_log_of_GMBE_block_len $log_of_GMBE_block_len\r"
    send -i $monitor_id "set_log_of_GMBE_tracing_ratio $log_of_GMBE_tracing_ratio\r"

    # The second GMBEOO_mask_of_GMBE_block_idx is the up to date one.
    expect -i $monitor_id -indices -re \
            {GMBEOO_mask_of_GMBE_block_idx: __.*GMBEOO_mask_of_GMBE_block_idx: __(.*)__} {
        set mask_of_GMBE_block_idx [string trim $expect_out(1,string)]
    }
    debug_print "GMBEOO_mask_of_GMBE_block_idx: $mask_of_GMBE_block_idx\n"
}

debug_print "---storing start timestamp and starting to trace---\n"
set tracing_start_time [clock milliseconds]

# Resume the workload.
send -i $monitor_id "cont\r"
send -i $monitor_id "sendkey ret\r"

# interact -i $monitor_id

debug_print "\n---expecting Stop tracing message---\n"
expect {
    -i $guest_ttyS0_reader_id
    "Stop tracing" {}
    eof {
        debug_print "it seems that guest_ttyS0_reader terminated unexpectedly."
        exit 1
    }
}

send -i $monitor_id "stop\r"
# flush the trace file twice, to make GMBEOO's code in `writeout_thread` run
# twice, which might be needed due to the way GMBEOO's code works (and the fact
# that `trace_buf` is a cyclic buffer).
send -i $monitor_id "trace-file flush\r"
send -i $monitor_id "trace-file flush\r"
set tracing_end_time [clock milliseconds]

set tracing_duration_in_milliseconds [expr $tracing_end_time - $tracing_start_time]
send_user "tracing_duration_in_milliseconds: $tracing_duration_in_milliseconds\n"

debug_print "\n---$analysis_tool_path---\n"
if {$analysis_tool_path != "/dev/null"} {
    # Give the analysis tool a second to finish reading from the FIFO.
    sleep 1
    
    debug_print "\n---sending SIGUSR1 to $analysis_tool_path---\n"
    exec kill -SIGUSR1 $analysis_tool_pid
    sleep 3
    debug_print "\n---expecting analysis output---\n"
    expect -i $analysis_tool_id -indices -re \
            "-----begin analysis output-----(.*)-----end analysis output-----" {
        set analysis_output [string trim $expect_out(1,string)]
    }
    debug_print "\n---received analysis output---\n"

    send_user "analysis output:\n"
    send_user -- "$analysis_output\n"
}


if {$print_trace_info == "True" && $dont_trace == "False"} {
    send -i $monitor_id "print_trace_info\r"
    debug_print "\n---expecting trace info---\n"
    expect -i $monitor_id -indices -re \
            "-----begin trace info-----(.*)-----end trace info-----" {
        set trace_info [string trim $expect_out(1,string)]
    }
    send_user "trace info:\n"
    send_user -- "$trace_info\n"
}


debug_print "---end run_qemu_and_workload.sh---\n"

if {$dont_exit_qemu_when_done == "True"} {
    interact -i $monitor_id
}

