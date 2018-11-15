/* 
sane people:
    Why did you write all of this code, when we simply have to copy a file
    from the host to the qemu guest, and then make the guest run it?
orenmn:
    At first, I tried using scp and ssh from the host to do that, but for some
    reason ssh from the host to the guest took a really long time on my laptop
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
    serial port in order to avoid using serial control characters.
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
#include <signal.h>
#include <assert.h>
#include <ctype.h>

#define PRINT_TO_TTYS0(str) {           \
    printf(str);                        \
    fprintf(serial_port_ttyS0, str);    \
    fflush(serial_port_ttyS0);          \
}

#define TTYS0_PATH              ("/dev/ttyS0")
#define EXECUTABLE1_LOCAL_COPY_PATH  ("/tmp/executable1_from_serial")
#define EXECUTABLE2_LOCAL_COPY_PATH  ("/tmp/executable2_from_serial")
#define REDIRECT_TO_TTYS0       (" 2>&1 | tee /dev/ttyS0")
#define CHMOD_777               ("chmod 777 ")
#define SYNC_BYTES              ("serial sync\n")
#define NUM_OF_SYNC_BYTES       (strlen(SYNC_BYTES))
#define EXECUTABLE_SIZE_STR_LEN     (30)
#define DECIMAL_BASE            (10)
#define HEXADECIMAL_BASE        (16)
#define BYTE_HEX_REPR_SIZE_INCLUDING_LINE_FEED      (3)


static bool were_sync_bytes_received(char *sync_cyclic_buf,
                                     int cyclic_buf_start_idx) {
    assert(cyclic_buf_start_idx == cyclic_buf_start_idx % NUM_OF_SYNC_BYTES);
    // Assumes that sync_cyclic_buf is a buffer of size NUM_OF_SYNC_BYTES.
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
        // printf("received: %c\n", sync_cyclic_buf[i]);
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
    char executable_size_str[EXECUTABLE_SIZE_STR_LEN];
    memset(executable_size_str, 0, EXECUTABLE_SIZE_STR_LEN);
    for (int i = 0; i < EXECUTABLE_SIZE_STR_LEN; ++i) {
        size_t num_of_bytes_read = fread(
            &executable_size_str[i], 1, 1, serial_port_ttyS0);
        if (num_of_bytes_read != 1) {
            printf("failed to read while receiving decimal repr of a uint. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_bytes_read);
            return -1;
        }

        if (!isdigit(executable_size_str[i])) {
            executable_size_str[i] = 0;
            return strtol(executable_size_str, NULL, DECIMAL_BASE);
        }
    }
    printf("received executable size string is too long.\n");
    return -1;
}

static bool receive_executable_contents_and_write_to_file(
    FILE *serial_port_ttyS0, int executable_size, char *executable_local_path,
    uint16_t expected_16_bit_checksum)
{
    if (executable_size == 0) {
        return true;
    }
    bool result = true;

    uint8_t *executable_contents = malloc(executable_size);
    if (executable_contents == NULL) {
        printf("malloc error\n");
        return false;
    }

    uint16_t actual_16_bit_checksum = 0;
    for (int i = 0; i < executable_size; ++i) {
        // printf("i: %d\n", i);
        char hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LINE_FEED];
        
        size_t num_of_hex_reprs_read = fread(
            &hex_repr, BYTE_HEX_REPR_SIZE_INCLUDING_LINE_FEED, 1, serial_port_ttyS0);
        if (num_of_hex_reprs_read != 1) {
            printf("failed to read while receiving executable contents. "
                   "ferror: %d, feof: %d, errno: %d\n, fread_return_value: %zu",
                   ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
                   num_of_hex_reprs_read);
            result = false;
            goto cleanup1;
        }
        assert(hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LINE_FEED - 1] == '\n');
        hex_repr[BYTE_HEX_REPR_SIZE_INCLUDING_LINE_FEED - 1] = 0;
        // printf("hex_repr: %s\n", hex_repr);
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

    char cmd_str[300];
    assert(strlen(CHMOD_777) + strlen(executable_local_path) < sizeof(cmd_str));
    if (cmd_str != strcpy(cmd_str, CHMOD_777)) {
        printf("`strcpy()` failed.\n");
        result = false;
        goto cleanup1;
    }
    if (cmd_str != strcat(cmd_str, executable_local_path)) {
        printf("`strcat()` failed.\n");
        result = false;
        goto cleanup1;
    }
    int system_result = system(cmd_str);
    if (system_result != 0) {
        printf("`system(\"%s\")` failed. result code: %d errno: %d\n",
               cmd_str, system_result, errno);
        result = false;
        goto cleanup1;
    }

cleanup1:
    free(executable_contents);
    return result;
}

static bool receive_executable(FILE *serial_port_ttyS0,
                               char *executable_local_path) {
    int expected_16_bit_checksum = receive_uint_decimal_repr(serial_port_ttyS0);
    if (expected_16_bit_checksum == -1) {
        return false;
    }
    int executable_size = receive_uint_decimal_repr(serial_port_ttyS0);
    if (executable_size == -1) {
        return false;
    }
    printf("Received executable_size: %d\n", executable_size);

    if (!receive_executable_contents_and_write_to_file(
            serial_port_ttyS0, executable_size, executable_local_path,
            (uint16_t)expected_16_bit_checksum)) {
        return false;
    }
    printf("Received executable and wrote it to local file.\n");
    return true;
}

int main(int argc, char **argv) {
    int result = 0;

    // This should work in case `sudo chmod 666 /dev/ttyS0` was executed.
    FILE *serial_port_ttyS0 = fopen(TTYS0_PATH, "rw");
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

    char dont_add_communications_with_host_to_workload;
    size_t num_of_bytes_read = fread(
            &dont_add_communications_with_host_to_workload, 1, 1, serial_port_ttyS0);
    if (num_of_bytes_read != 1) {
        printf("failed to read dont_add_communications_with_host_to_workload char. "
               "ferror: %d, feof: %d, errno: %d, num_of_bytes_read: %zu\n",
               ferror(serial_port_ttyS0), feof(serial_port_ttyS0), errno,
               num_of_bytes_read);
        result = 1;
        goto cleanup;
    }
    if (dont_add_communications_with_host_to_workload != '1' && 
        dont_add_communications_with_host_to_workload != '0')
    {
        printf("dont_add_communications_with_host_to_workload = '%c', "
               "but it must be '0' or '1'.\n",
               dont_add_communications_with_host_to_workload);
        result = 1;
        goto cleanup;
    }
    bool dont_add_communications = 
        dont_add_communications_with_host_to_workload == '1' ? true : false;
    printf("Received dont_add_communications_with_host_to_workload: %d\n",
           dont_add_communications);

    if (!receive_executable(serial_port_ttyS0, EXECUTABLE1_LOCAL_COPY_PATH)) {
        result = 1;
        goto cleanup;
    }
    if (!receive_executable(serial_port_ttyS0, EXECUTABLE2_LOCAL_COPY_PATH)) {
        result = 1;
        goto cleanup;
    }

    char cmd_str[300];
    assert(strlen(EXECUTABLE1_LOCAL_COPY_PATH) + strlen(REDIRECT_TO_TTYS0) <
           sizeof(cmd_str));
    if (cmd_str != strcpy(cmd_str, EXECUTABLE1_LOCAL_COPY_PATH)) {
        printf("`strcpy()` failed.\n");
        result = 1;
        goto cleanup;
    }
    if (cmd_str != strcat(cmd_str, REDIRECT_TO_TTYS0)) {
        printf("`strcat()` failed.\n");
        result = 1;
        goto cleanup;
    }

    if (dont_add_communications) {
        int system_result = system(cmd_str);
        if (system_result != 0) {
            printf("`system(\"%s\")` failed. result code: %d errno: %d\n",
                   cmd_str, system_result, errno);
            result = 1;
            goto cleanup;
        }
    }
    else {
        PRINT_TO_TTYS0("-----begin workload info-----");
        PRINT_TO_TTYS0("-----end workload info-----");

        PRINT_TO_TTYS0("Ready to trace. Press enter to continue");
        getchar(); /* The host would use 'sendkey' when it is ready. */
        
        int system_result = system(cmd_str);
        if (system_result != 0) {
            printf("`system(\"%s\")` failed. result code: %d errno: %d\n",
                   cmd_str, system_result, errno);
            result = 1;
            goto cleanup;
        }

        PRINT_TO_TTYS0("Stop tracing");
    }
    
cleanup:
    if (fclose(serial_port_ttyS0) != 0) {
        printf("failed to close /dev/ttyS0.\n");
    }
    return result;
}

