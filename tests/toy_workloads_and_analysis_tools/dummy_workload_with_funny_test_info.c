#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

int main() {
    PRINT_STR("-----begin workload info-----");
    printf("\t\n\n arg2     arg3          \t \n arg4 \n\n\narg5"
           "\n\n\t\t\narg6   \t \n \t \n \n    ");
    PRINT_STR("-----end workload info-----");

    PRINT_STR("Ready to trace. Press enter to continue");
    getchar(); /* The host would use 'sendkey' when it is ready. */

    PRINT_STR("Stop tracing");

    return 0;
}

