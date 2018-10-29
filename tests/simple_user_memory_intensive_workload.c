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

void memory_intensive_loop(int *arr) {
    for (int j = 0; j < 2; ++j) {
        for (int i = 0; i < ARR_LEN; ++i) {
            ++arr[0];
            // ++arr[i];
            // printf("%p\n", (void *)&arr[i]);
        }
    }
}

int main() {
    int *arr = (int *)malloc(ARR_LEN * sizeof(int));
    memory_intensive_loop(arr);

    PRINT_STR("-----begin test info-----");
    // printf("&arr: %p\n", (void *)&arr);
    printf("%p ", (void *)arr);
    printf("1234 56789\n");
    printf("6 7 8\n");
    PRINT_STR("-----end test info-----");

    PRINT_STR("Ready to trace. Press enter to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    memory_intensive_loop(arr);



    PRINT_STR("Stop tracing.");

    return 0;
}

