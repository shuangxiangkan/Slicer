#include "../mocklib.h"
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

// Fuzzing harness for mock_parser_parse function
// This tests the parser functionality which internally calls mock_buffer_append

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size == 0) {
        return 0;
    }
    
    // Create a parser
    mock_parser_t *parser = mock_parser_create();
    if (!parser) {
        return 0;
    }
    
    // Convert input data to a null-terminated string for parsing
    // Filter out non-printable characters to make it valid input
    char *input_str = malloc(size + 1);
    if (!input_str) {
        mock_parser_destroy(parser);
        return 0;
    }
    
    size_t valid_size = 0;
    for (size_t i = 0; i < size; i++) {
        // Only include printable ASCII characters (32-126)
        if (data[i] >= 32 && data[i] <= 126) {
            input_str[valid_size++] = data[i];
        }
    }
    input_str[valid_size] = '\0';
    
    // If we have valid input, test the parser
    if (valid_size > 0) {
        // Test input validation first
        int validation_result = mock_validate_input(input_str, valid_size);
        
        // Test parsing (this will internally call mock_buffer_append)
        int parse_result = mock_parser_parse(parser, input_str, valid_size);
        
        // The parser should succeed if validation succeeded
        if (validation_result == 1 && parse_result != 0) {
            // This might indicate a bug in the parser logic
        }
        
        // Test with various chunk sizes if input is large enough
        if (valid_size > 10) {
            // Create a new parser for chunk testing
            mock_parser_t *parser2 = mock_parser_create();
            if (parser2) {
                // Test with first half of input
                size_t half_size = valid_size / 2;
                mock_parser_parse(parser2, input_str, half_size);
                mock_parser_destroy(parser2);
            }
        }
    }
    
    // Test with edge cases
    if (size > 0) {
        // Test with single character
        char single_char[2] = {0};
        if (data[0] >= 32 && data[0] <= 126) {
            single_char[0] = data[0];
            mock_parser_t *parser3 = mock_parser_create();
            if (parser3) {
                mock_parser_parse(parser3, single_char, 1);
                mock_parser_destroy(parser3);
            }
        }
        
        // Test with empty string
        mock_parser_t *parser4 = mock_parser_create();
        if (parser4) {
            mock_parser_parse(parser4, "", 0);
            mock_parser_destroy(parser4);
        }
        
        // Test with NULL input
        mock_parser_t *parser5 = mock_parser_create();
        if (parser5) {
            mock_parser_parse(parser5, NULL, size);
            mock_parser_destroy(parser5);
        }
    }
    
    // Clean up
    free(input_str);
    mock_parser_destroy(parser);
    
    return 0;
}