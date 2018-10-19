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

#define ARR_LEN 20000

int main() {
    int *arr = (int *)malloc(ARR_LEN * sizeof(int));

    PRINT_STR("-----begin test info-----");
    // printf("&arr: %p\n", (void *)&arr);
    printf("%p", (void *)arr);
    PRINT_STR("-----end test info-----");


    PRINT_STR("Ready for trace. Press any key to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    for (int j = 0; j < 4; ++j) {
        for (int i = 0; i < ARR_LEN; ++i) {
            arr[i] = i;
            // printf("%p\n", (void *)&arr[i]);
        }
    }


    PRINT_STR("End running test.\n");

    return 0;
}

