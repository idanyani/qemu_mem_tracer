/* - - - - - - - - - - - - - - - - ATTENTION - - - - - - - - - - - - - - - - */
/*                 assumes single_event_optimization is on.                  */
/* - - - - - - - - - - - - - - - - ATTENTION - - - - - - - - - - - - - - - - */

#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <stdbool.h>
#include <signal.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

#define PIPE_MAX_SIZE_ON_MY_UBUNTU      (1 << 20)
#define OUR_BUF_SIZE                    (20000)

// see https://www.kernel.org/doc/Documentation/x86/x86_64/mm.txt
#define LINUX_USER_SPACE_END_ADDR       ((uint64_t)1 << 47)

typedef struct {
    uint64_t event; /* event ID value */
    // uint64_t timestamp_ns;
    uint32_t length;   /*    in bytes */
    uint32_t padding;
    // uint32_t pid;
    uint64_t virtual_addr;
    uint64_t info;
} TraceRecord;

bool end_analysis = false;
unsigned long long num_of_mem_accesses_to_user_memory = 0; 
unsigned long long num_of_mem_accesses_to_kernel_memory = 0; 
unsigned long long num_of_mem_accesses_to_our_buf = 0; 

void handle_end_analysis_signal(int unused_signum) {
    end_analysis = true;
    printf("num_of_mem_accesses_to_user_memory: %llu\n"
           "num_of_mem_accesses_to_kernel_memory: %llu\n"
           "num_of_mem_accesses: %llu\n"
           "num_of_mem_accesses_to_our_buf: %llu\n",
           num_of_mem_accesses_to_user_memory,
           num_of_mem_accesses_to_kernel_memory,
           num_of_mem_accesses_to_user_memory + num_of_mem_accesses_to_kernel_memory,
           num_of_mem_accesses_to_our_buf);
    // printf("num_of_mem_accesses: %zd\n", num_of_mem_accesses);
}

int main(int argc, char **argv) {
    int ret_val = 0;
    uint64_t our_buf_addr = strtoull(argv[2], NULL, 0);
    uint64_t our_buf_end_addr = our_buf_addr + 20000 * sizeof(int);
    PRINT_STR("opening fifo.\n");
    FILE *qemu_trace_fifo = fopen(argv[1], "rb");
    if (qemu_trace_fifo == NULL) {
        printf("failed to open fifo. errno: %d\n", errno);
        return 1;
    }
    PRINT_STR("fifo opened.\n");

    signal(SIGUSR1, handle_end_analysis_signal);
    size_t num_of_trace_records_read = 0;
    TraceRecord trace_record;


    while (!end_analysis) {
        num_of_trace_records_read = fread(&trace_record, sizeof(trace_record), 1,
                                  qemu_trace_fifo);
        if (num_of_trace_records_read != 1) {
            printf("read failed.\n"
                   "num_of_trace_records_read: %zu, ferror: %d, feof: %d\n",
                   num_of_trace_records_read,
                   ferror(qemu_trace_fifo), feof(qemu_trace_fifo));
            ret_val = 1;
            goto cleanup;
        }

        uint64_t virt_addr = trace_record.virtual_addr;
        if (virt_addr < LINUX_USER_SPACE_END_ADDR) {
            ++num_of_mem_accesses_to_user_memory;
            if (virt_addr >= our_buf_addr && virt_addr < our_buf_end_addr) {
                ++num_of_mem_accesses_to_our_buf;
            }
        }
        else {
            ++num_of_mem_accesses_to_kernel_memory;
        }
    }

cleanup:
    fclose(qemu_trace_fifo);
    return ret_val;
}

