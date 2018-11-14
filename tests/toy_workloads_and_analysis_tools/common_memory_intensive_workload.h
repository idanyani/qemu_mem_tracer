#pragma once

    PRINT_STR("-----begin workload info-----");
    printf("%p", (void *)arr);
    PRINT_STR("-----end workload info-----");

    PRINT_STR("Ready to trace. Press enter to continue");
    getchar(); /* The host would use 'sendkey' when it is ready. */

    for (int j = 0; j < NUM_OF_ITERS_OVER_OUR_ARR; ++j) {
        for (int i = 0; i < OUR_ARR_LEN; ++i) {
            ++arr[i];
        }
    }

    PRINT_STR("Stop tracing");
    return 0;
