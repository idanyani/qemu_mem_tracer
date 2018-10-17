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
    int *buf = (int *)malloc(sizeof(int));

    PRINT_STR("-----begin test info-----");
    printf("&buf: %p\n", (void *)&buf);
    PRINT_STR("-----end test info-----");


    PRINT_STR("Ready for trace. Press any key to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    buf = 0;
    for (int i = 0; i < 10; ++i) {
        ++buf;
    }


    PRINT_STR("End running test.");

    return 0;
}

