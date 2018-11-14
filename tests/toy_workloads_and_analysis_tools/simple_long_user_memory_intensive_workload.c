#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "long_memory_intensive.h"

int main() {
    int *arr = (int *)malloc(OUR_ARR_LEN * sizeof(int));

    #include "common_memory_intensive_workload.h"
}

