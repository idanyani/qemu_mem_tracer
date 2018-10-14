#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

int main() {
    PRINT_STR("Start running test.");

    PRINT_STR("Ready for trace. Press any key to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    // aoeu


    PRINT_STR("End running test.");

    return 0;
}

