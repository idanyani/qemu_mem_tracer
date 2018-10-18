#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

/*  argv[1] - pipe name
 *  argv[2] - pipe size
 */

int main(int argc, char **argv) {
    int ret_val = 0;
    int pipe_fd = open(argv[1], O_RDONLY | O_NONBLOCK);
    if (pipe_fd != -1) {
        printf("fifo already exists. This is considered a problem because "
               "if there might be some other process that reads from theFIFO, "
               "and so we would miss some of the data.\n");
        ret_val = 1;
        goto cleanup;
    }

    printf("creating fifo.\n");
    mkfifo(argv[1], 0666);
    pipe_fd = open(argv[1], O_RDONLY | O_NONBLOCK);

    if (pipe_fd == -1) {
        printf("failed to open fifo after running mkfifo.\n");
        return 1;
    }

    int original_size = fcntl(pipe_fd, F_GETPIPE_SZ);
    printf("fifo's original size: %d.\n", original_size);
    
    int wanted_new_size = atoi(argv[2]);
    int actual_new_size = fcntl(pipe_fd, F_SETPIPE_SZ, wanted_new_size);
    printf("the fifo's new file size is %d.\n", actual_new_size);
    // weirdly, the docs don't say it returns the new size, but whatever.
    if (actual_new_size < wanted_new_size) {
        printf("the fifo's new file size is smaller than wanted. errno: %d.\n",
               errno);
        ret_val = 1;
        goto cleanup;
    }

cleanup:
    close(pipe_fd);
    return ret_val;
}

