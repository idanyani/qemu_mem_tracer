/* 
sane people:
    Why did you write all of this code, when we simply wish to copy two files
    from the host to the qemu guest, and then make the guest run the first one?
orenmn:
    At first, I tried using scp and ssh from the host to do that, but for some
    reason, ssh from the host to the guest took a really long time on my laptop
    (several minutes).
    scp from the guest to the host was actually pretty fast, and I used that at
    first. But I think that was quite ugly, as you can see if you look at
    previous commits.
    I then thought about using a shared folder, but when I used a shared folder
    (by following the instructions at http://www.linux-kvm.org/page/9p_virtio),
    I found out that qemu doesn't support the `savevm` monitor command when
    using shared folders this way (as explained a bit at
    (https://patchwork.kernel.org/patch/9018051/).

    By the way, I used only printable characters in the communication over the
    serial port in order to avoid using serial control characters (which would
    mess things up).
*/

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
#include <assert.h>
#include <ctype.h>

#define TTYS0_PATH                      "/dev/ttyS0"
#define EXECUTABLE1_LOCAL_COPY_PATH     "/tmp/executable1"
#define EXECUTABLE2_LOCAL_COPY_PATH     "/tmp/executable2"
#define REDIRECT_TO_TTYS0               " 2>&1 | tee /dev/ttyS0"
#define RUN_EXECUTABLE1_CMD             (EXECUTABLE1_LOCAL_COPY_PATH REDIRECT_TO_TTYS0)
#define CHMOD_777                       "chmod 777 "
#define SYNC_BYTES                      "serial sync\n"
#define NUM_OF_SYNC_BYTES               (strlen(SYNC_BYTES))
#define UINT_DECIMAL_REPR_STR_LEN       (30)
#define DECIMAL_BASE                    (10)
#define HEXADECIMAL_BASE                (16)
#define BYTE_HEX_REPR_SIZE_INCLUDING_LF (3)


// Assumes that sync_cyclic_buf is a buffer of size NUM_OF_SYNC_BYTES.
static bool were_sync_bytes_received(char *sync_cyclic_buf,
                                     int cyclic_buf_start_idx) {
    assert(cyclic_buf_start_idx == cyclic_buf_start_idx % NUM_OF_SYNC_BYTES);
    char *sync_bytes = SYNC_BYTES;
    for (int i = 0; i < NUM_OF_SYNC_BYTES; ++i) {
        if (sync_cyclic_buf[(cyclic_buf_start_idx + i) % NUM_OF_SYNC_BYTES] !=
            sync_bytes[i])
        {
            return false;
        }
    }
    return true;
}

static bool wait_for_sync_bytes(FILE *serial_port_ttyS0) {
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

        i = (i + 1) % NUM_OF_SYNC_BYTES;
    }
    return true;
}

static int receive_uint_decimal_repr(FILE *serial_port_ttyS0) {
    char uint_decimal_repr_str[UINT_DECIMAL_REPR_STR_LEN];
    memset(uint_decimal_repr_str, 0, UINT_DECIMAL_REPR_STR_LEN);
    for (int i = 0; i < UINT_DECIMAL_REPR_STR_LEN; ++i) {
        size_t num_of_bytes_read = fread(
            &uint_decimal_repr_str[i], 1, 1, serial_port_ttyS0);
        if (num_of_bytes_read != 1) {
            printf("failed to read while receiving decimal repr of a uint. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_bytes_read);
            return -1;
        }

        if (!isdigit(uint_decimal_repr_str[i])) {
            uint_decimal_repr_str[i] = 0;
            return strtol(uint_decimal_repr_str, NULL, DECIMAL_BASE);
        }
    }
    printf("received uint decimal representation is too long.\n");
    return -1;
}

static bool receive_executable_contents_and_write_to_file(
    FILE *serial_port_ttyS0, size_t executable_size,
    char *executable_local_path, uint16_t expected_16_bit_checksum)
{
    assert(executable_size > 0);
    bool result = true;

    uint8_t *executable_contents = malloc(executable_size);
    if (executable_contents == NULL) {
        printf("malloc error\n");
        return false;
    }

    uint16_t actual_16_bit_checksum = 0;
    for (int i = 0; i < executable_size; ++i) {
        char hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LF];
        
        size_t num_of_hex_reprs_read = fread(
            &hex_repr, BYTE_HEX_REPR_SIZE_INCLUDING_LF, 1, serial_port_ttyS0);
        if (num_of_hex_reprs_read != 1) {
            printf("failed to read while receiving executable contents. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_hex_reprs_read);
            result = false;
            goto cleanup1;
        }
        assert(hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LF - 1] == '\n');
        hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LF - 1] = 0;
        uint8_t byte_value = strtol(hex_repr, NULL, HEXADECIMAL_BASE);
        actual_16_bit_checksum += byte_value;
        executable_contents[i] = byte_value;
    }

    if (actual_16_bit_checksum != expected_16_bit_checksum) {
        printf("Checksum check failed.\n"
               "actual_16_bit_checksum: %u\n"
               "expected_16_bit_checksum: %u\n",
               actual_16_bit_checksum, expected_16_bit_checksum);
        result = false;
        goto cleanup1;
    }

    FILE *executable_local_copy = fopen(executable_local_path, "w+");
    if (executable_local_copy == NULL) {
        printf("failed to open a file for the executable's local copy. errno: %d\n",
               errno);
        result = false;
        goto cleanup1;
    }

    size_t num_of_bytes_written = fwrite(executable_contents, executable_size, 1, 
                                         executable_local_copy);
    if (num_of_bytes_written != 1) {
        printf("failed to write executable contents to the local copy. "
               "ferror: %d, feof: %d, errno: %d\n",
               ferror(executable_local_copy), feof(executable_local_copy), errno);
        if (fclose(executable_local_copy) != 0) {
            printf("failed to close executable local copy.\n");
        }
        result = false;
        goto cleanup1;
    }

    if (fclose(executable_local_copy) != 0) {
        printf("failed to close executable local copy.\n");
        result = false;
        goto cleanup1;
    }

    char chmod_cmd_str[300];
    assert(strlen(CHMOD_777) + strlen(executable_local_path) < sizeof(chmod_cmd_str));
    strcpy(chmod_cmd_str, CHMOD_777);
    strcat(chmod_cmd_str, executable_local_path);
    int system_result = system(chmod_cmd_str);
    if (system_result != 0) {
        printf("`system(\"%s\")` failed. result code: %d errno: %d\n",
               chmod_cmd_str, system_result, errno);
        result = false;
        goto cleanup1;
    }

cleanup1:
    free(executable_contents);
    return result;
}

static bool receive_executable(FILE *serial_port_ttyS0,
                               char *executable_local_path) {
    int executable_size = receive_uint_decimal_repr(serial_port_ttyS0);
    if (executable_size == -1) {
        return false;
    }
    printf("Received executable_size: %d\n", executable_size);
    if (executable_size == 0) {
        return true;
    }

    int expected_16_bit_checksum = receive_uint_decimal_repr(serial_port_ttyS0);
    if (expected_16_bit_checksum == -1) {
        return false;
    }
    printf("Received expected_16_bit_checksum: %d\n", expected_16_bit_checksum);

    if (!receive_executable_contents_and_write_to_file(
            serial_port_ttyS0, (size_t)executable_size, executable_local_path,
            (uint16_t)expected_16_bit_checksum)) {
        return false;
    }
    printf("Received executable and wrote it to local file.\n");
    return true;
}

int main(int argc, char **argv) {
    int result = 0;

    // This should work in case `sudo chmod 666 /dev/ttyS0` was executed.
    FILE *serial_port_ttyS0 = fopen(TTYS0_PATH, "r");
    if (serial_port_ttyS0 == NULL) {
        printf("failed to open /dev/ttyS0. errno: %d\n", errno);
        return 1;
    }
    printf("Opened /dev/ttyS0.\n");

    if (!wait_for_sync_bytes(serial_port_ttyS0)) {
        result = 1;
        goto cleanup;
    }
    printf("Received sync bytes.\n");

    if (!receive_executable(serial_port_ttyS0, EXECUTABLE1_LOCAL_COPY_PATH)) {
        result = 1;
        goto cleanup;
    }
    printf("Done Receiving executable1.\n");
    if (!receive_executable(serial_port_ttyS0, EXECUTABLE2_LOCAL_COPY_PATH)) {
        result = 1;
        goto cleanup;
    }
    printf("Done Receiving executable2.\n");

    int system_result = system(RUN_EXECUTABLE1_CMD);
    if (system_result != 0) {
        printf("`system(\"%s\")` failed. result code: %d errno: %d\n",
               RUN_EXECUTABLE1_CMD, system_result, errno);
        result = 1;
        goto cleanup;
    }
    
cleanup:
    if (fclose(serial_port_ttyS0) != 0) {
        printf("failed to close /dev/ttyS0.\n");
    }
    return result;
}

