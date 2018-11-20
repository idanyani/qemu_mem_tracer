#!/usr/bin/expect -f
# exp_internal 1

# sane people:
#   Why didn't you write this code in Python, so that everyone would be able
#   to read it easily?
# orenmn:
#   That's a good question - I had a fair amount of struggling with expect
#   while writing this code, and if you can replace this code with something
#   better that does the same job, I think it would be great (and please let me
#   know about that).
#   However, I am not aware of a better tool for doing what this expect code
#   does (essentially, you need a tool to communicate with three different
#   processes: qemu's monitor, the workload, and the analysis tool):
#       - Start qemu_with_GMBEOO. (for brevity, I would refer to
#         qemu_with_GMBEOO simply as qemu.)
#       - Extract from a message that qemu prints the path of the
#         pseudo-terminal that qemu created for us.
#       - Let qemu keep running in the background.
#       - Start a reader of the pseudo-terminal, and let it run in the
#         background.
#       - Write the received executable files to the pseudo-terminal. (The
#         guest would write both of them to a temporary directory, and execute
#         the first.)
#       - Parse the workload info that the pseudo-terminal's reader has read.
#       - When the pseudo-terminal's reader reads
#         "Ready to trace. Press enter to continue", pause qemu and start the
#         analysis tool, while passing the workload info to it.
#       - When the analysis tool prints "Ready to analyze", start tracing and
#         then resume qemu and the workload (by using monitor commands).
#       - When the workload prints "Stop tracing":
#           * Pause qemu.
#           * Send monitor commands to qemu to make it write to the trace FIFO
#             traces that were left in its internal trace_buf.
#           * Stop the analysis tool and print its output.
#           * Send a monitor command to qemu to print extra info about the
#             tracing, and print it.
# sane people:
#   But why do we need this workload info? Why would we want memory_tracer to
#   run the analysis tool for us?
# orenmn: 
#   If workload info hadn't existed, then it wouldn't have made sense for
#   memory_tracer to run the analysis tool.
#   However, there are some scenarios in which you want the analysis tool to
#   have some info that the workload acquires only at runtime. E.g. in the main
#   test of memory_tracer, a toy workload mallocs a buffer, and then accesses
#   it many times. The test makes sure that the traces received by the analysis
#   tool include the expected number of memory accesses to the buffer. To
#   count the number of accesses to the buffer, the analysis tool has to know
#   the address of the buffer.
# sane peaple:
#   So why not just start tracing and then start the workload and the analysis
#   tool, and let them communicate with each other?
# orenmn:
#   If you start the tracing while the analysis tool is waiting for the
#   workload info, i.e. before the analysis tool starts reading from the trace
#   FIFO, it is very probable that the trace FIFO will get full, which will
#   cause qemu's internal trace_buf to get full, which will cause discarding
#   traces.
#   Also, you might want to start tracing only after the workload and/or the
#   analysis tool has finished running some initialization code.

set timeout 360000

# Silent various messages.
log_user 0
stty -echo

# necessary if workload_info or analysis_output are very large.
match_max -d 1000000

set guest_image_path [lindex $argv 0]
set snapshot_name [lindex $argv 1]
set file1_to_write_to_serial_path [lindex $argv 2]
set file2_to_write_to_serial_path [lindex $argv 3]
set write_executables_to_serial_path [lindex $argv 4]
set trace_only_CPL3_code_GMBE [lindex $argv 5]
set log_of_GMBE_block_len [lindex $argv 6]
set log_of_GMBE_tracing_ratio [lindex $argv 7]
set analysis_tool_path [lindex $argv 8]
set trace_fifo_path [lindex $argv 9]
set qemu_with_GMBEOO_dir_path [lindex $argv 10]
set verbose [lindex $argv 11]
set dont_exit_qemu_when_done [lindex $argv 12]
set print_trace_info [lindex $argv 13]
set dont_trace [lindex $argv 14]
set dont_add_communications [lindex $argv 15]
set dont_use_nographic [lindex $argv 16]
set guest_RAM_in_MBs [lindex $argv 17]

proc debug_print {msg} {
    if {$::verbose == "True"} {
        send_error -- $msg
    }
}

proc expect_and_check_eof {spawned_process_spawn_id spawn_process_name expected_str} {
    expect {
        -i $spawned_process_spawn_id
        $expected_str {}
        eof {
            debug_print "it seems that $spawn_process_name terminated unexpectedly.\n"
            exit 1
        }
    }
}


debug_print "---start run_qemu_and_workload.sh---\n"


# Start qemu while:
#   The monitor is redirected to our process' stdin and stdout.
#   /dev/ttyS0 of the guest is redirected to pseudo-terminal that qemu creates.
#   The snapshot $snapshot_name is loaded immediately.
debug_print "---starting qemu---\n"
if {$dont_use_nographic == "True"} {
    spawn $qemu_with_GMBEOO_dir_path/x86_64-softmmu/qemu-system-x86_64 \
        -m $guest_RAM_in_MBs -hda $guest_image_path -monitor stdio \
        -serial pty -loadvm $snapshot_name
} else {
    spawn $qemu_with_GMBEOO_dir_path/x86_64-softmmu/qemu-system-x86_64 \
        -m $guest_RAM_in_MBs -hda $guest_image_path -nographic \
        -serial pty -loadvm $snapshot_name
}
set monitor_spawn_id $spawn_id

debug_print "---parsing qemu's message about the pseudo-terminal that it opened---\n"
expect {
    -i $monitor_spawn_id
    "serial pty: char device redirected to " {
        expect -i $monitor_spawn_id -re {^/dev/pts/\d+} {
             set pty_path $expect_out(0,string)
        }
    }
    eof {
        debug_print "it seems that qemu terminated unexpectedly.\n"
        exit 1
    }
}

spawn cat $pty_path
set pty_reader_spawn_id $spawn_id

sleep 0.5
debug_print "\n---writing executables to $pty_path---\n"
exec python3.7 $write_executables_to_serial_path $file1_to_write_to_serial_path \
               $file2_to_write_to_serial_path $pty_path

# The guest would now receive the executables and run the first one.

debug_print "\n---expecting workload info---\n"
expect -i $pty_reader_spawn_id -indices -re \
        "-----begin workload info-----(.*)-----end workload info-----" {
    set workload_info [string trim $expect_out(1,string)]
}
if {$workload_info != ""} {
    send_user "workload info:\n"
    send_user -- "$workload_info\n"
}

debug_print "\n---expecting ready to trace message---\n"
expect_and_check_eof $pty_reader_spawn_id "pty_reader" \
    "Ready to trace. Press enter to continue"
send -i $monitor_spawn_id "stop\r"



if {$analysis_tool_path != "/dev/null"} {
    debug_print "\n---spawning analysis tool---\n"
    # https://stackoverflow.com/questions/5728656/tcl-split-string-by-arbitrary-number-of-whitespaces-to-a-list/5731098#5731098
    set workload_info_with_spaces [join $workload_info " "]
    set analysis_tool_pid \
        [eval spawn $analysis_tool_path $trace_fifo_path $workload_info_with_spaces]
    set analysis_tool_spawn_id $spawn_id
    
    debug_print "\n---expecting ready to analyze message---\n"
    expect_and_check_eof $analysis_tool_spawn_id $analysis_tool_path "Ready to analyze"
}

if {$::dont_trace == "False"} {
    debug_print "---configure qemu_with_GMBEOO for tracing---\n"
    send -i $monitor_spawn_id "enable_GMBEOO\r"
    # Enabling GMBEOO before setting the trace file causes the mapping of events to
    # never be written to our FIFO.
    send -i $monitor_spawn_id "trace-file set $trace_fifo_path\r"
    send -i $monitor_spawn_id "trace-event guest_mem_before_exec on\r"
    send -i $monitor_spawn_id "update_trace_only_CPL3_code_GMBE $trace_only_CPL3_code_GMBE\r"
    send -i $monitor_spawn_id "set_log_of_GMBE_block_len $log_of_GMBE_block_len\r"
    send -i $monitor_spawn_id "set_log_of_GMBE_tracing_ratio $log_of_GMBE_tracing_ratio\r"

    expect_and_check_eof $monitor_spawn_id "monitor" "GMBEOO log_of_GMBE_tracing_ratio was set."
}

debug_print "---storing start timestamp and starting to trace---\n"
set tracing_start_time [clock milliseconds]

# Resume the workload.
send -i $monitor_spawn_id "cont\r"
send -i $monitor_spawn_id "sendkey ret\r"

debug_print "\n---expecting Stop tracing message---\n"
expect_and_check_eof $pty_reader_spawn_id "pty_reader" "Stop tracing"

send -i $monitor_spawn_id "stop\r"
set tracing_end_time [clock milliseconds]

# flush the trace file twice, to make GMBEOO's code in `writeout_thread` run
# twice, which might be needed due to the way GMBEOO's code works (and the fact
# that `trace_buf` is a cyclic buffer).
sleep 0.5
send -i $monitor_spawn_id "trace-file flush\r"
send -i $monitor_spawn_id "trace-file flush\r"

set tracing_duration_in_milliseconds [expr $tracing_end_time - $tracing_start_time]
send_user "tracing_duration_in_milliseconds: $tracing_duration_in_milliseconds\n"

debug_print "\n---$analysis_tool_path---\n"
if {$analysis_tool_path != "/dev/null"} {
    # Give the analysis tool a moment to finish reading from the FIFO.
    sleep 0.5
    
    debug_print "\n---sending SIGUSR1 to $analysis_tool_path---\n"
    exec kill -SIGUSR1 $analysis_tool_pid
    debug_print "\n---expecting analysis output---\n"
    expect {
        -i $analysis_tool_spawn_id
        -indices -re "-----begin analysis output-----(.*)-----end analysis output-----" {
            set analysis_output [string trim $expect_out(1,string)]
        }
        eof {
            debug_print "it seems that $analysis_tool_path terminated unexpectedly.\n"
            exit 1
        }
    } 
    debug_print "\n---received analysis output---\n"

    send_user "analysis output:\n"
    send_user -- "$analysis_output\n"
}


if {$print_trace_info == "True" && $dont_trace == "False"} {
    send -i $monitor_spawn_id "print_trace_info\r"
    debug_print "\n---expecting trace info---\n"
    expect -i $monitor_spawn_id -indices -re \
            "-----begin trace info-----(.*)-----end trace info-----" {
        set trace_info [string trim $expect_out(1,string)]
    }
    send_user "trace info:\n"
    send_user -- "$trace_info\n"
}


debug_print "---end run_qemu_and_workload.sh---\n"

if {$dont_exit_qemu_when_done == "True"} {
    interact -i $monitor_spawn_id
}

