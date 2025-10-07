#include "../mocklib.h"
#include <stdint.h>
#include <stddef.h>

// Simplified fuzzing harness for buffer creation/destruction
// This tests only basic buffer lifecycle management

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0) {
        return 0;
    }
    
    // Use input data to determine buffer capacity
    size_t capacity = (size % 1000) + 1; // 1-1000
    
    // Test buffer creation
    mock_buffer_t *buffer = mock_buffer_create(capacity);
    if (!buffer) {
        return 0;
    }
    
    // Test buffer destruction
    mock_buffer_destroy(buffer);
    
    return 0;
}