#include "../mocklib.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

// Test cases for mock_parser_parse function

void test_parser_create_destroy() {
    printf("Testing parser create/destroy...\n");
    
    // Test normal creation
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    assert(parser->buffer != NULL);
    assert(parser->state == 0);
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser create/destroy tests passed\n");
}

void test_parser_parse_valid_input() {
    printf("Testing parser with valid input...\n");
    
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // Test parsing simple valid input
    const char *valid_input = "Hello World";
    int result = mock_parser_parse(parser, valid_input, strlen(valid_input));
    assert(result == 0); // Should succeed
    assert(parser->state == 1); // Should be in parsed state
    
    // Verify that data was stored in the internal buffer
    const char *buffer_data = mock_buffer_get_data(parser->buffer);
    assert(buffer_data != NULL);
    assert(strncmp(buffer_data, valid_input, strlen(valid_input)) == 0);
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser valid input tests passed\n");
}

void test_parser_parse_invalid_input() {
    printf("Testing parser with invalid input...\n");
    
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // Test parsing NULL input
    int result = mock_parser_parse(parser, NULL, 10);
    assert(result == -1); // Should fail
    assert(parser->state == 0); // Should remain in initial state
    
    // Test parsing with zero size
    result = mock_parser_parse(parser, "test", 0);
    assert(result == 0); // Should succeed but not change state significantly
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser invalid input tests passed\n");
}

void test_parser_multiple_parses() {
    printf("Testing parser with multiple parse operations...\n");
    
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // First parse
    const char *input1 = "First";
    int result = mock_parser_parse(parser, input1, strlen(input1));
    assert(result == 0);
    
    // Second parse (should append to existing data)
    const char *input2 = " Second";
    result = mock_parser_parse(parser, input2, strlen(input2));
    assert(result == 0);
    
    // Verify combined data
    const char *buffer_data = mock_buffer_get_data(parser->buffer);
    assert(strncmp(buffer_data, "First Second", 12) == 0);
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser multiple parse tests passed\n");
}

void test_parser_edge_cases() {
    printf("Testing parser edge cases...\n");
    
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // Test with very long input
    char long_input[1000];
    memset(long_input, 'A', 999);
    long_input[999] = '\0';
    
    int result = mock_parser_parse(parser, long_input, 999);
    assert(result == 0); // Should succeed
    
    // Test with single character
    result = mock_parser_parse(parser, "X", 1);
    assert(result == 0); // Should succeed
    
    // Verify the buffer contains all the data
    const char *buffer_data = mock_buffer_get_data(parser->buffer);
    assert(buffer_data != NULL);
    assert(parser->buffer->size == 1000); // 999 + 1
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser edge case tests passed\n");
}

void test_parser_buffer_interaction() {
    printf("Testing parser-buffer interaction...\n");
    
    mock_parser_t *parser = mock_parser_create();
    assert(parser != NULL);
    
    // Verify initial buffer state
    assert(parser->buffer->size == 0);
    assert(parser->buffer->capacity > 0);
    
    // Parse some data and verify buffer changes
    const char *test_data = "TestData";
    int result = mock_parser_parse(parser, test_data, strlen(test_data));
    assert(result == 0);
    
    // Verify buffer was updated
    assert(parser->buffer->size == strlen(test_data));
    const char *buffer_data = mock_buffer_get_data(parser->buffer);
    assert(strncmp(buffer_data, test_data, strlen(test_data)) == 0);
    
    mock_parser_destroy(parser);
    
    printf("✓ Parser-buffer interaction tests passed\n");
}

int main() {
    printf("Running parser API tests...\n\n");
    
    test_parser_create_destroy();
    test_parser_parse_valid_input();
    test_parser_parse_invalid_input();
    test_parser_multiple_parses();
    test_parser_with_validation();
    test_parser_edge_cases();
    test_parser_buffer_interaction();
    
    printf("\n✓ All parser tests passed!\n");
    return 0;
}