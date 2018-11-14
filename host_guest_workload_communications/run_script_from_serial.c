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

#define PRINT_TO_TTYS0(str) {           \
    fprintf(serial_port_ttyS0, str);    \
    fflush(serial_port_ttyS0);          \
}

#define TTYS0_PATH              ("/dev/ttyS0")
#define SCRIPT_LOCAL_COPY_PATH  ("~/workload_script_received_from_serial")
#define REDIRECT_TO_TTYS0       (" > /dev/ttyS0 2>&1")
#define SYNC_BYTES              ("serial sync ")
#define NUM_OF_SYNC_BYTES       (strlen(SYNC_BYTES))
#define SCRIPT_SIZE_STR_LEN     (30)
#define DECIMAL_BASE            (10)
#define HEXADECIMAL_BASE        (16)
#define BYTE_HEX_REPR_SIZE      (2)


bool were_sync_bytes_received(char *sync_cyclic_buf, int cyclic_buf_start_idx) {
    // Assumes that sync_cyclic_buf is a buffer of size NUM_OF_SYNC_BYTES.
    char *sync_bytes = SYNC_BYTES;
    for (int i = 0; i < NUM_OF_SYNC_BYTES; ++i) {
        if (sync_cyclic_buf[cyclic_buf_start_idx + i % NUM_OF_SYNC_BYTES] !=
            sync_bytes[i])
        {
            return false;
        }
    }
    return true;
}

bool wait_for_sync_bytes(FILE *serial_port_ttyS0) {
    char sync_cyclic_buf[NUM_OF_SYNC_BYTES];
    int i = 0;
    while (!were_sync_bytes_received(sync_cyclic_buf, i)) {
        size_t num_of_bytes_read = fread(
            &sync_cyclic_buf[i], 1, 1, serial_port_ttyS0);
        if (num_of_bytes_read != 1) {
            printf("failed to read while waiting for sync bytes. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_bytes_read);
            return false;
        }

        i = i + 1 % NUM_OF_SYNC_BYTES;
    }
    return true;
}

int receive_script_size(FILE *serial_port_ttyS0) {
    char script_size_str[SCRIPT_SIZE_STR_LEN];
    memset(script_size_str, 0, SCRIPT_SIZE_STR_LEN);
    for (int i = 0; i < SCRIPT_SIZE_STR_LEN; ++i) {
        size_t num_of_bytes_read = fread(
            &script_size_str[i], 1, 1, serial_port_ttyS0);
        if (num_of_bytes_read != 1) {
            printf("failed to read while receiving script size. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_bytes_read);
            return -1;
        }

        if (!isdigit(script_size_str[i])) {
            script_size_str[i] = 0;
            return strtol(script_size_str, NULL, DECIMAL_BASE);
        }
    }
    printf("received script size string is too long.\n");
    return -1;
}

bool receive_script_and_write_to_file(FILE *serial_port_ttyS0, int script_size) {
    assert(script_size > 0);

    uint8_t *script_contents = malloc(script_size);
    if (script_contents == NULL) {
        printf("malloc error\n");
        return false;
    }

    for (int i = 0; i < script_size; ++i) {
        char hex_repr[BYTE_HEX_REPR_SIZE + 1];
        hex_repr[BYTE_HEX_REPR_SIZE] = 0;
        
        size_t num_of_hex_reprs_read = fread(
            &hex_repr, BYTE_HEX_REPR_SIZE, 1, serial_port_ttyS0);
        if (num_of_hex_reprs_read != 1) {
            printf("failed to read while receiving script contents. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_hex_reprs_read);
            return false;
        }
        script_contents[i] = strtol(hex_repr, NULL, HEXADECIMAL_BASE);
    }

    FILE *script_local_copy = fopen(SCRIPT_LOCAL_COPY_PATH, "wb");
    if (script_local_copy == NULL) {
        printf("failed to open a file for the script's local copy. errno: %d\n",
               errno);
        return false;
    }

    size_t num_of_bytes_written = fwrite(script_contents, script_size, 1, 
                                         script_local_copy);
    if (num_of_bytes_written != 1) {
        printf("failed to write script contents to the local copy. "
               "ferror: %d, feof: %d, errno: %d\n",
               ferror(script_local_copy), feof(script_local_copy), errno);
        if (fclose(script_local_copy) != 0) {
            printf("failed to close script local copy.\n");
        }
        return false;
    }
    return true;
}

int main(int argc, char **argv) {
    size_t num_of_bytes_read = 0;
    int i = 0;
    int result = 0;

    // if (freopen(TTYS0_PATH, "w", stdout) == NULL) {
    //     printf("failed to redirect stdout to /dev/ttyS0. errno: %d\n", errno);
    //     return 1;
    // }

    // if (freopen(TTYS0_PATH, "w", stderr) == NULL) {
    //     printf("failed to redirect stderr to /dev/ttyS0. errno: %d\n", errno);
    //     result = 1;
    //     goto cleanup1;
    // }

    // This should work in case `sudo chmod 666 /dev/ttyS0` was executed.
    FILE *serial_port_ttyS0 = fopen(TTYS0_PATH, "rw");
    if (serial_port_ttyS0 == NULL) {
        printf("failed to open /dev/ttyS0. errno: %d\n", errno);
        return 1;
    }

    if (!wait_for_sync_bytes(serial_port_ttyS0)) {
        result = 1;
        goto cleanup1;
    }

    char dont_add_communications_with_host_to_workload;
    size_t num_of_bytes_read = fread(
            &dont_add_communications_with_host_to_workload, 1, 1, serial_port_ttyS0);
    if (num_of_bytes_read != 1) {
        printf("failed to read dont_add_communications_with_host_to_workload char. "
               "ferror: %d, feof: %d, errno: %d, num_of_bytes_read: %zu\n",
               ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
               num_of_bytes_read);
        result = 1;
        goto cleanup1;
    }
    if (dont_add_communications_with_host_to_workload != '1' && 
        dont_add_communications_with_host_to_workload != '0')
    {
        printf("dont_add_communications_with_host_to_workload = '%c', "
               "but it must be '0' or '1'.\n",
               dont_add_communications_with_host_to_workload);
        result = 1;
        goto cleanup1;
    }
    bool dont_add_communications = 
        dont_add_communications_with_host_to_workload == '1' ? true : false;

    int script_size = receive_script_size(serial_port_ttyS0);
    if (script_size == -1) {
        result = 1;
        goto cleanup1;
    }
    printf("script_size: %d\n", script_size);

    if (!receive_script_and_write_to_file(serial_port_ttyS0, script_size)) {
        result = 1;
        goto cleanup1;
    }


    

    
    char cmd_str[300];
    assert(strlen(SCRIPT_LOCAL_COPY_PATH) + strlen(REDIRECT_TO_TTYS0) <
           sizeof(cmd_str));
    if (cmd_str != strcpy(cmd_str, SCRIPT_LOCAL_COPY_PATH)) {
        printf("`strcpy()` failed.\n");
    }
    if (cmd_str != strcat(cmd_str, REDIRECT_TO_TTYS0)) {
        printf("`strcat()` failed.\n");
    }

    if (dont_add_communications_with_host_to_workload) {
        int system_result = system(cmd_str);
        if (system_result != 0) {
            printf("`system()` failed. result code: %d errno: %d\n",
                   system_result, errno);
            result = 1;
            goto cleanup2;
        }
    }
    else {
        PRINT_TO_TTYS0("-----begin workload info-----");
        PRINT_TO_TTYS0("-----end workload info-----");

        PRINT_TO_TTYS0("Ready to trace. Press enter to continue");
        getchar(); /* The host would use 'sendkey' when it is ready. */
        
        int system_result = system(cmd_str);
        if (system_result != 0) {
            printf("`system()` failed. result code: %d errno: %d\n",
                   system_result, errno);
            result = 1;
            goto cleanup2;
        }

        PRINT_TO_TTYS0("Stop tracing");
    }


    
cleanup1:
    if (fclose(serial_port_ttyS0) != 0) {
        printf("failed to close /dev/ttyS0.\n");
    }
    return result;
}

