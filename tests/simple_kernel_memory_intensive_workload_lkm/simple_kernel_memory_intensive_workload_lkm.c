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


int main() {
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


/* uninitialized static variables are implicitly zero-initialized */
// static char *program_name;

// MODULE_PARM(program_name, "s");

// void** sys_call_table = NULL;

// asmlinkage long (*original_sys_kill)(int pid, int sig);

// asmlinkage long our_sys_kill(int pid, int sig) {
//     task_t *tsk = find_task_by_pid(pid);
//     if (pid > 0 && tsk && tsk->comm && program_name && sig == SIGKILL &&
//             strncmp(tsk->comm, program_name, 16) == 0) {
//         return -EPERM;
//     }
//     else {
//         return original_sys_kill(pid, sig);
//     }
// }

// void find_sys_call_table(int scan_range) {
//     int *addr = NULL;
//     int *end_addr = (int *)&system_utsname + scan_range;

//     for (addr = (int *)&system_utsname; addr < end_addr; addr++) {
//         if (*addr == (int)(&sys_read) &&
//                 *(addr + 1) == (int)(&sys_write)) {
//             sys_call_table = (void **)(addr - __NR_read);
//             return;
//         }
//     }
//     BUG();
// }

// int init_module(void) {
//     if (program_name != NULL) {
//         find_sys_call_table(5000);
//         /* store a reference to the original syscall */
//         original_sys_kill = sys_call_table[__NR_kill];
//         /* manipulate sys_call_table to point to our fake function */
//         sys_call_table[__NR_kill] = our_sys_kill;
//     }
//     return 0;
// }

// void cleanup_module(void) {
//     if (program_name != NULL) {
//         /* restore the original syscall */
//         sys_call_table[__NR_kill] = original_sys_kill;
//     }
// }

