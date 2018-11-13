#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <stdbool.h>
#include <signal.h>
#include <assert.h>

#define PRINT_STR(str) { \
    puts(str);           \
    fflush(stdout);      \
}

#define TTYS0_PATH              ("/dev/ttyS0")
#define SCRIPT_LOCAL_COPY_PATH  ("~/workload_script_received_from_serial")

int main(int argc, char **argv) {
    int result = 0;

    if (freopen(TTYS0_PATH, "w", stdout) == NULL) {
        printf("failed to redirect stdout to /dev/ttyS0. errno: %d\n", errno);
        return 1;
    }

    if (freopen(TTYS0_PATH, "w", stderr) == NULL) {
        printf("failed to redirect stderr to /dev/ttyS0. errno: %d\n", errno);
        result = 1;
        goto cleanup1;
    }

    FILE *serial_port_ttyS0 = fopen(TTYS0_PATH, "rb");
    if (serial_port_ttyS0 == NULL) {
        printf("failed to open /dev/ttyS0. errno: %d\n", errno);
        result = 1;
        goto cleanup2;
    }

    uint8_t dont_add_communications_with_host_to_workload = 0;
    size_t num_of_bytes_read = fread(
        &dont_add_communications_with_host_to_workload, 1, 1, serial_port_ttyS0);
    if (num_of_bytes_read != 1) {
        printf("failed to read script size. ferror: %d, feof: %d, errno: %d\n",
               ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno);
        result = 1;
        goto cleanup3;
    }
    assert(dont_add_communications_with_host_to_workload <= 1);

    size_t script_size = 0;
    assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__);
    size_t num_of_dwords_read = fread(&script_size, 4, 1, serial_port_ttyS0);
    if (num_of_dwords_read != 1) {
        printf("failed to read script size. ferror: %d, feof: %d, errno: %d\n",
               ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno);
        result = 1;
        goto cleanup3;
    }

    uint8_t *script_contents = malloc(script_size);
    if (script_contents == NULL) {
        printf("malloc error\n");
        result = 1;
        goto cleanup3;
    }

    num_of_bytes_read = fread(script_contents, script_size, 1, 
                              serial_port_ttyS0);
    if (num_of_bytes_read != 1) {
        printf("failed to read script contents. ferror: %d, feof: %d, errno: %d\n",
               ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno);
        result = 1;
        goto cleanup3;
    }

    FILE *script_local_copy = fopen(SCRIPT_LOCAL_COPY_PATH, "wb");
    if (script_local_copy == NULL) {
        printf("failed to open a file for the script's local copy. errno: %d\n",
               errno);
        result = 1;
        goto cleanup3;
    }

    size_t num_of_bytes_written = fwrite(script_contents, script_size, 1, 
                                         script_local_copy);
    if (num_of_bytes_written != 1) {
        printf("failed to write script contents to the local copy. "
               "ferror: %d, feof: %d, errno: %d\n",
               ferror(script_local_copy), feof(script_local_copy), errno);
        result = 1;
        goto cleanup4;
    }

    // char cmd_str[300];
    // if (cmd_str != strcpy(cmd_str, SCRIPT_LOCAL_COPY_PATH)) {
    //     printf("`strcpy` failed.\n");
    // }
    // if (cmd_str != strcat(cmd_str, " > /dev/ttyS0 2>&1")) {
    //     printf("`strcat` failed.\n");
    // }
    if (dont_add_communications_with_host_to_workload) {
        int system_result = system(SCRIPT_LOCAL_COPY_PATH);
        if (system_result != 0) {
            printf("`system()` failed. result code: %d errno: %d\n",
                   system_result, errno);
            result = 1;
            goto cleanup4;
        }
    }
    else {
        PRINT_STR("-----begin workload info-----");
        PRINT_STR("-----end workload info-----");

        PRINT_STR("Ready to trace. Press enter to continue");
        getchar(); /* The host would use 'sendkey' when it is ready. */
        
        int system_result = system(SCRIPT_LOCAL_COPY_PATH);
        if (system_result != 0) {
            printf("`system()` failed. result code: %d errno: %d\n",
                   system_result, errno);
            result = 1;
            goto cleanup4;
        }

        PRINT_STR("Stop tracing");
    }


cleanup4:
    if (fclose(script_local_copy) != 0) {
        printf("failed to close script local copy.\n");
    }
cleanup3:
    if (fclose(serial_port_ttyS0) != 0) {
        printf("failed to close /dev/ttyS0.\n");
    }
cleanup2:
    if (fclose(stderr) != 0) {
        printf("failed to close stderr.\n");
    }
cleanup1:
    if (fclose(stdout) != 0) {
        printf("failed to close stdout.\n");
    }
    return result;
}

