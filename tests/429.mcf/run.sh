#! /bin/bash
export OMP_NUM_THREADS=4
export OMP_THREAD_LIMIT=4
export OMP_STACKSIZE=120M
./mcf_base.none inp.in > inp.out 2>> inp.err
