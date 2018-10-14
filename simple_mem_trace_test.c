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

int global_var;

int main() {
    PRINT_STR("-----begin test info-----");
    printf("&global_var: %p\n", (void *)&global_var);
    PRINT_STR("-----end test info-----");


    PRINT_STR("Ready for trace. Press any key to continue.");
    getchar(); /* The host would use 'sendkey' when it is ready. */


    global_var = 0;
    for (int i = 0; i < 100; ++i) {
        ++global_var;
    }


    PRINT_STR("End running test.");

    return 0;
}

