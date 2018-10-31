#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/syscall.h>
#include <linux/unistd.h>
#include <linux/utsname.h>
#include <linux/sched.h>
#include <linux/signal.h>
#include <linux/errno.h>

MODULE_LICENSE("GPL");

#include "common_memory_intensive.h"


int init_module(void) {
    int *arr = (int *)kmalloc(OUR_ARR_LEN * sizeof(int), GFP_KERNEL);

    #include "common_memory_intensive_workload.h"
}


void cleanup_module(void) {
    /* nothing to do. */
}

