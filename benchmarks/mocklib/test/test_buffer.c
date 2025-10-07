#include "../mocklib.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

// Test cases for mock_buffer_append function

void test_buffer_create_destroy() {
    printf("Testing buffer create/destroy...\n");
    
    // Test normal creation
    mock_buffer_t *buffer = mock_buffer_create(100);
    assert(buffer != NULL);
    assert(buffer->capacity == 100);
    assert(buffer->size == 0);
    assert(buffer->data != NULL);
    
    mock_buffer_destroy(buffer);
    
    // Test creation with zero capacity
    buffer = mock_buffer_create(0);
    assert(buffer != NULL);
    assert(buffer->capacity == 1); // Should default to minimum capacity
    
    mock_buffer_destroy(buffer);
    
    printf("✓ Buffer create/destroy tests passed\n");
}

void test_buffer_append() {
    printf("Testing buffer append...\n");
    
    mock_buffer_t *buffer = mock_buffer_create(10);
    assert(buffer != NULL);
    
    // Test appending normal data
    const char *test_data1 = "Hello";
    int result = mock_buffer_append(buffer, test_data1, strlen(test_data1));
    assert(result == 0);
    assert(buffer->size == strlen(test_data1));
    assert(strncmp(buffer->data, test_data1, strlen(test_data1)) == 0);
    
    // Test appending more data
    const char *test_data2 = " World";
    result = mock_buffer_append(buffer, test_data2, strlen(test_data2));
    assert(result == 0);
    assert(buffer->size == strlen(test_data1) + strlen(test_data2));
    
    // Verify the complete data
    const char *buffer_data = mock_buffer_get_data(buffer);
    assert(strncmp(buffer_data, "Hello World", 11) == 0);
    
    // Test appending NULL data
    result = mock_buffer_append(buffer, NULL, 5);
    assert(result == -1); // Should fail
    
    // Test appending with zero size
    result = mock_buffer_append(buffer, "test", 0);
    assert(result == 0); // Should succeed but not change buffer
    
    mock_buffer_destroy(buffer);
    
    printf("✓ Buffer append tests passed\n");
}

void test_buffer_resize() {
    printf("Testing buffer resize...\n");
    
    mock_buffer_t *buffer = mock_buffer_create(5);
    assert(buffer != NULL);
    
    // Add some data first
    mock_buffer_append(buffer, "test", 4);
    assert(buffer->size == 4);
    
    // Test expanding buffer
    int result = mock_buffer_resize(buffer, 20);
    assert(result == 0);
    assert(buffer->capacity == 20);
    assert(buffer->size == 4); // Size should remain the same
    
    // Verify data is still intact
    const char *data = mock_buffer_get_data(buffer);
    assert(strncmp(data, "test", 4) == 0);
    
    // Test shrinking buffer (should not shrink below current size)
    result = mock_buffer_resize(buffer, 2);
    assert(result == 0);
    assert(buffer->capacity >= 4); // Should not shrink below current size
    
    mock_buffer_destroy(buffer);
    
    printf("✓ Buffer resize tests passed\n");
}

void test_buffer_edge_cases() {
    printf("Testing buffer edge cases...\n");
    
    // Test with very large capacity
    mock_buffer_t *buffer = mock_buffer_create(1000000);
    assert(buffer != NULL);
    
    // Test appending large data
    char large_data[1000];
    memset(large_data, 'A', 999);
    large_data[999] = '\0';
    
    int result = mock_buffer_append(buffer, large_data, 999);
    assert(result == 0);
    assert(buffer->size == 999);
    
    mock_buffer_destroy(buffer);
    
    printf("✓ Buffer edge case tests passed\n");
}

int main() {
    printf("Running buffer API tests...\n\n");
    
    test_buffer_create_destroy();
    test_buffer_append();
    test_buffer_resize();
    test_buffer_edge_cases();
    
    printf("\n✓ All buffer tests passed!\n");
    return 0;
}