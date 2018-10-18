#include <stdio.h>
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

#define MEM_ACCESS_TRACE_RECORD_SIZE    (0x30)
#define LOCAL_BUF_SIZE                  (1 << 16)

bool end_analysis = false;

void handle_end_analysis_signal(int unused_signum) {
    end_analysis = true;
    printf("SIGUSR1 signal caught.\n");
}

int main(int argc, char **argv) {
    int ret_val = 0;
    PRINT_STR("opening fifo.\n");
    int pipe_fd = open(argv[1], O_RDONLY | O_NONBLOCK);
    if (pipe_fd == -1) {
        PRINT_STR("failed to open fifo.\n");
        return 1;
    }

    signal(SIGUSR1, handle_end_analysis_signal);
    unsigned long long num_of_mem_accesses = 0; 
    ssize_t num_of_bytes_read = 0;
    ssize_t leftovers_size = 0;
    char buf[LOCAL_BUF_SIZE];


    while (!end_analysis) {
        num_of_bytes_read = read(pipe_fd, buf, LOCAL_BUF_SIZE);
        if (num_of_bytes_read == -1 && errno != EAGAIN) {
            printf("read failed. errno: %d\n", errno);
            ret_val = 1;
            goto cleanup;
        }
        num_of_mem_accesses += (leftovers_size + num_of_bytes_read) /
                               MEM_ACCESS_TRACE_RECORD_SIZE;
        leftovers_size = (leftovers_size + num_of_bytes_read) %
                         MEM_ACCESS_TRACE_RECORD_SIZE;
    }
    printf("num_of_mem_accesses: %llu\n", num_of_mem_accesses);
    // printf("num_of_mem_accesses: %zd\n", num_of_mem_accesses);

cleanup:
    close(pipe_fd);
    return ret_val;
}

