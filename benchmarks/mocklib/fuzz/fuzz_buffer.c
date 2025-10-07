#include "../mocklib.h"
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

// Fuzzing harness for mock_buffer_append function
// This tests the buffer management functionality

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0) {
        return 0;
    }
    
    // Create a buffer with random initial capacity
    size_t initial_capacity = (size % 100) + 10; // 10-109
    mock_buffer_t *buffer = mock_buffer_create(initial_capacity);
    if (!buffer) {
        return 0;
    }
    
    // Split the input data into chunks and append them
    size_t offset = 0;
    while (offset < size) {
        // Determine chunk size (1 to remaining size)
        size_t chunk_size = (size - offset > 10) ? (data[offset] % 10) + 1 : size - offset;
        if (chunk_size > size - offset) {
            chunk_size = size - offset;
        }
        
        // Create a null-terminated string from the chunk
        char *chunk_data = malloc(chunk_size + 1);
        if (!chunk_data) {
            mock_buffer_destroy(buffer);
            return 0;
        }
        
        memcpy(chunk_data, data + offset, chunk_size);
        chunk_data[chunk_size] = '\0';
        
        // Test mock_buffer_append with this chunk
        int result = mock_buffer_append(buffer, chunk_data, chunk_size);
        
        free(chunk_data);
        offset += chunk_size;
        
        // If append failed, we might be out of memory or hit a limit
        if (result != 0) {
            break;
        }
        
        // Occasionally test getting the data
        if (offset % 20 == 0) {
            const char *buffer_data = mock_buffer_get_data(buffer);
            (void)buffer_data; // Suppress unused variable warning
        }
    }
    
    // Test buffer resize if we have enough data
    if (size > 50) {
        size_t new_capacity = buffer->capacity + (data[0] % 100) + 1;
        mock_buffer_resize(buffer, new_capacity);
    }
    
    // Clean up
    mock_buffer_destroy(buffer);
    
    return 0;
}