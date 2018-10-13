#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

#define READY_TO_TRACE_PRESS_ANY_KEY_STR "Ready for trace. Press any key to continue.\n"
#define END_TEST_STR "End running test.\n"


int main() {
    printf("Start running test.\n");

    int serial_fd = open("/dev/ttyS0", O_WRONLY | O_NOCTTY | O_SYNC);
    write(serial_fd, READY_TO_TRACE_PRESS_ANY_KEY_STR,
          strlen(READY_TO_TRACE_PRESS_ANY_KEY_STR));
    getchar(); /* The host would use 'sendkey' when it is ready. */


    // aoeu


    write(serial_fd, END_TEST_STR, strlen(END_TEST_STR));
    return 0;
}

