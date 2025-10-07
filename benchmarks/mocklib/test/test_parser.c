#include "../mocklib.h"
#include <stdio.h>
#include <assert.h>

// Simplified test cases for parser creation/destruction
// This tests only basic parser lifecycle management

void test_parser_create_destroy() {
    printf("Testing parser create/destroy...\n");
    
    // Test normal creation
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // Test destruction
    mock_parser_destroy(parser);
    
    printf("✓ Parser create/destroy test passed\n");
}

void test_multiple_parser_lifecycle() {
    printf("Testing multiple parser lifecycle...\n");
    
    // Test creating and destroying multiple parsers
    for (int i = 0; i < 5; i++) {
        mock_parser_t *parser = mock_parser_create();
        assert(parser != NULL);
        mock_parser_destroy(parser);
    }
    
    printf("✓ Multiple parser lifecycle test passed\n");
}

int main() {
    printf("Running simplified parser tests...\n\n");
    
    test_parser_create_destroy();
    test_multiple_parser_lifecycle();
    
    printf("\n✓ All tests passed!\n");
    return 0;
}