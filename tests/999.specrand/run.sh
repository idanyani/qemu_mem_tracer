#! /bin/bash
export OMP_NUM_THREADS=4
export OMP_THREAD_LIMIT=4
export OMP_STACKSIZE=120M
cd workload
echo "-----begin workload info----------end workload info-----"
echo "Ready to trace. Press enter to continue"
read -n1
./specrand_base.none 1255432124 234923 > rand.234923.out 2>> rand.234923.err
echo "Stop tracing"

