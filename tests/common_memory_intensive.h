#pragma once


#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

#define OUR_ARR_LEN                 (10000)
#define NUM_OF_ITERS_OVER_OUR_ARR   (5)

void memory_intensive_loop(int *arr) {
    for (int j = 0; j < NUM_OF_ITERS_OVER_OUR_ARR; ++j) {
        for (int i = 0; i < OUR_ARR_LEN; ++i) {
            ++arr[i];
        }
    }
}

