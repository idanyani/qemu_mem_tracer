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

    PRINT_STR("-----begin workload info-----");
    printf("%p", (void *)arr);
    PRINT_STR("-----end workload info-----");

    PRINT_STR("Ready to trace. Press enter to continue");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    memory_intensive_loop(arr);



    PRINT_STR("Stop tracing");

    return 0;
}


void cleanup_module(void) {
    /* nothing to do. */
}

