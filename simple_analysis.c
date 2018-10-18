#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}


int main(int argc, char **argv) {

    int pipe_fd = open(argv[1], O_RDONLY);
    if (pipe_fd == -1) {
        mkfifo(argv[1], 0666);
        pipe_fd = open(argv[1], O_RDONLY);
        assert(pipe_fd != -1);
    }

    fcntl(pipe_fd, F_SETPIPE_SZ, 1 << 19);



    PRINT_STR("Ready for trace. Press any key to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    for (int i = 0; i < ARR_LEN; ++i) {
        arr[i] = i;
    }


    PRINT_STR("End running test.");

    return 0;
}

