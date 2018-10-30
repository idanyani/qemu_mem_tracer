#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "common_memory_intensive.h"

int main() {
    int *arr = (int *)malloc(OUR_ARR_LEN * sizeof(int));

    PRINT_STR("-----begin workload info-----");
    printf("%p", (void *)arr);
    PRINT_STR("-----end workload info-----");

    PRINT_STR("Ready to trace. Press enter to continue");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    memory_intensive_loop(arr);



    PRINT_STR("Stop tracing");

    return 0;
}

