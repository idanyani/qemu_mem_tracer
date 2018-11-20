#!/usr/bin/expect -f
# exp_internal 1

set timeout 360000

# Silent various messages.
log_user 0
stty -echo

# necessary if workload_info or analysis_output are very large.
match_max -d 1000000

set workload_path [lindex $argv 0]
set verbose [lindex $argv 1]

proc debug_print {msg} {
    if {$::verbose == "True"} {
        send_error -- $msg
    }
}


debug_print "---start run_workload_natively.sh---\n"

spawn $workload_path
set workload_spawn_id $spawn_id

debug_print "\n---expecting workload info---\n"
expect -i $workload_spawn_id -indices -re \
        "-----begin workload info-----(.*)-----end workload info-----" {
    set workload_info [string trim $expect_out(1,string)]
}
if {$workload_info != ""} {
    send_user "workload info:\n"
    send_user -- "$workload_info\n"
}

debug_print "\n---expecting ready to trace message---\n"
expect {
    -i $workload_spawn_id
    "Ready to trace. Press enter to continue" {}
    eof {
        debug_print "it seems that $workload_path terminated unexpectedly."
        exit 1
    }
}

debug_print "---storing start timestamp and starting to trace---\n"
set tracing_start_time [clock milliseconds]

# Resume the workload.
send -i $workload_spawn_id "\r"

debug_print "\n---expecting Stop tracing message---\n"
expect {
    -i $workload_spawn_id
    "Stop tracing" {}
    eof {
        debug_print "it seems that $workload_path terminated unexpectedly."
        exit 1
    }
}

set tracing_end_time [clock milliseconds]

set tracing_duration_in_milliseconds [expr $tracing_end_time - $tracing_start_time]
send_user "tracing_duration_in_milliseconds: $tracing_duration_in_milliseconds\n"

debug_print "---end run_workload_natively.sh---\n"


