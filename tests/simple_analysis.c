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
#include <assert.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

#define PIPE_MAX_SIZE_ON_MY_UBUNTU      (1 << 20)
#define OUR_ARR_LEN                     (10000)
#define OUR_BUF_SIZE                    (OUR_ARR_LEN * sizeof(int))



// see https://www.kernel.org/doc/Documentation/x86/x86_64/mm.txt
#define LINUX_USER_SPACE_END_ADDR       ((uint64_t)1 << 47)
#define CPU_ENTRY_AREA_START_ADDR       (0xfffffe0000000000)
#define CPU_ENTRY_AREA_END_ADDR         (0xfffffe7fffffffff)

typedef struct {
    uint8_t size_shift : 3; /* interpreted as "1 << size_shift" bytes */
    bool    sign_extend: 1; /* whether it is a sign-extended operation */
    uint8_t endianness : 1; /* 0: little, 1: big */
    bool    store      : 1; /* whether it is a store operation */
    uint8_t cpl        : 2;
    uint64_t unused2   : 56;
    uint64_t virt_addr : 64;
} GMBEOO_TraceRecord;


bool end_analysis = false;
uint64_t num_of_mem_accesses_by_CPL3_code = 0; 
uint64_t num_of_mem_accesses_by_non_CPL3_code = 0; 
uint64_t num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area = 0; 
uint64_t num_of_mem_accesses_to_our_buf = 0; 
uint64_t curr_offset = 0; 
uint64_t num_of_read_failures = 0; 
uint64_t num_of_read_failures_with_feof_1 = 0;
uint64_t our_buf_addr = 0;
uint64_t our_buf_end_addr = 0;
int argc_global;
char **argv_global;
int counter_arr[OUR_BUF_SIZE];

void handle_end_analysis_signal(int unused_signum) {
    PRINT_STR("-----begin analysis output-----");
    if (num_of_read_failures != 0) {
        printf("- - - - - ATTENTION - - - - -:\n"
               "num_of_read_failures: %lu\n"
               "num_of_read_failures_with_feof_1: %lu\n",
               num_of_read_failures, num_of_read_failures_with_feof_1);
    }
    printf("our_buf_addr:                                       %lu\n"
           "num_of_mem_accesses_by_CPL3_code:                   %lu\n"
           "num_of_mem_accesses_by_non_CPL3_code:               %lu\n"
           "num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area: %lu\n"
           "num_of_mem_accesses:                                %lu\n"
           "num_of_mem_accesses_to_our_buf:                     %lu\n",
           our_buf_addr,
           num_of_mem_accesses_by_CPL3_code,
           num_of_mem_accesses_by_non_CPL3_code,
           num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area,
           num_of_mem_accesses_by_CPL3_code + num_of_mem_accesses_by_non_CPL3_code +
                num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area,
           num_of_mem_accesses_to_our_buf);
    printf("counter_arr:\n");
    for (int i = 0; i < OUR_ARR_LEN; ++i) {
        printf("%d,", counter_arr[i]);
    }
    printf("\n");
    printf("analysis cmd args:");
    for (int i = 0; i < argc_global; ++i) {
        printf("%s,", argv_global[i]);
    }
    PRINT_STR("-----end analysis output-----");
    end_analysis = true;
}

int main(int argc, char **argv) {
    int ret_val = 0;

    memset(counter_arr, 0, sizeof(counter_arr[0]) * OUR_ARR_LEN);
    argc_global = argc;
    argv_global = argv;

    
    if (argc > 2) {
        our_buf_addr = strtoull(argv[2], NULL, 0);
        our_buf_end_addr = our_buf_addr + OUR_BUF_SIZE;
    }
    PRINT_STR("opening fifo.\n");
    
    FILE *qemu_trace_fifo = fopen(argv[1], "rb");
    if (qemu_trace_fifo == NULL) {
        printf("failed to open fifo. errno: %d\n", errno);
        return 1;
    }
    PRINT_STR("fifo opened.\n");

    signal(SIGUSR1, handle_end_analysis_signal);
    size_t num_of_trace_records_read = 0;
    GMBEOO_TraceRecord trace_record;

    // FILE *trace_file = fopen("/home/orenmn/my_trace_file", "wb");
    // if (trace_file == NULL) {
    //     printf("failed to open my_trace_file. errno: %d\n", errno);
    //     return 1;
    // }

    PRINT_STR("Ready to analyze");
    while (!end_analysis) {
        num_of_trace_records_read = fread(&trace_record, sizeof(trace_record),
                                          1, qemu_trace_fifo);
        if (num_of_trace_records_read == 1) {
            // size_t num_of_trace_records_written_to_file = 
            //     fwrite(&trace_record, sizeof(trace_record), 1, trace_file);
            // if (num_of_trace_records_written_to_file != 1) {
            //     printf("fwrite failed.\n");
            // }

            uint8_t cpl = trace_record.cpl;
            uint64_t virt_addr = trace_record.virt_addr;
            
            if (virt_addr >= our_buf_addr && virt_addr < our_buf_end_addr) {
                ++num_of_mem_accesses_to_our_buf;
                assert((virt_addr - our_buf_addr) % sizeof(int) == 0);
                ++(counter_arr[(virt_addr - our_buf_addr) / sizeof(int)]);
            }

            if (cpl == 3) {
                if (virt_addr >= CPU_ENTRY_AREA_START_ADDR &&
                    virt_addr <= CPU_ENTRY_AREA_END_ADDR)
                {
                    ++num_of_mem_accesses_by_CPL3_code_to_cpu_entry_area;
                }
                else {
                    ++num_of_mem_accesses_by_CPL3_code;
                }
            }
            else {
                ++num_of_mem_accesses_by_non_CPL3_code;
            }
        }
        else {
            num_of_read_failures++;
            if (feof(qemu_trace_fifo) == 1) {
                num_of_read_failures_with_feof_1++;
            }
            // printf("read failed.\n"
            //        "num_of_trace_records_read: %zu, ferror: %d, feof: %d, errno: %d\n",
            //        num_of_trace_records_read,
            //        ferror(qemu_trace_fifo), feof(qemu_trace_fifo), errno);
            

            // ret_val = 1;
            // goto cleanup;
        }
    }

// cleanup:
    fclose(qemu_trace_fifo);
    return ret_val;
}

