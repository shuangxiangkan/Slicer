#include "mocklib.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* Buffer management functions */
mock_buffer_t* mock_buffer_create(size_t initial_capacity) {
    mock_buffer_t *buffer = malloc(sizeof(mock_buffer_t));
    if (!buffer) return NULL;
    
    buffer->data = malloc(initial_capacity);
    if (!buffer->data) {
        free(buffer);
        return NULL;
    }
    
    buffer->size = 0;
    buffer->capacity = initial_capacity;
    buffer->data[0] = '\0';
    
    return buffer;
}

void mock_buffer_destroy(mock_buffer_t *buffer) {
    if (!buffer) return;
    
    if (buffer->data) {
        free(buffer->data);
    }
    free(buffer);
}

int mock_buffer_append(mock_buffer_t *buffer, const char *data, size_t size) {
    if (!buffer || !data || size == 0) return -1;
    
    // Check if we need to resize
    if (buffer->size + size + 1 > buffer->capacity) {
        size_t new_capacity = buffer->capacity * 2;
        while (new_capacity < buffer->size + size + 1) {
            new_capacity *= 2;
        }
        
        if (mock_buffer_resize(buffer, new_capacity) != 0) {
            return -1;
        }
    }
    
    memcpy(buffer->data + buffer->size, data, size);
    buffer->size += size;
    buffer->data[buffer->size] = '\0';
    
    return 0;
}

int mock_buffer_resize(mock_buffer_t *buffer, size_t new_capacity) {
    if (!buffer || new_capacity <= buffer->size) return -1;
    
    char *new_data = realloc(buffer->data, new_capacity);
    if (!new_data) return -1;
    
    buffer->data = new_data;
    buffer->capacity = new_capacity;
    
    return 0;
}

const char* mock_buffer_get_data(mock_buffer_t *buffer) {
    if (!buffer) return NULL;
    return buffer->data;
}

/* Parser functions */
mock_parser_t* mock_parser_create(void) {
    mock_parser_t *parser = malloc(sizeof(mock_parser_t));
    if (!parser) return NULL;
    
    parser->state = 0;
    parser->input = NULL;
    parser->input_size = 0;
    parser->error_code = 0;
    
    return parser;
}

void mock_parser_destroy(mock_parser_t *parser) {
    if (!parser) return;
    
    if (parser->input) {
        free(parser->input);
    }
    free(parser);
}

int mock_parser_parse(mock_parser_t *parser, const char *input, size_t size) {
    if (!parser || !input || size == 0) {
        if (parser) parser->error_code = 1;
        return -1;
    }
    
    // Validate input first
    if (mock_validate_input(input, size) != 1) {
        parser->error_code = 2;
        return -1;
    }
    
    // Create a buffer to store processed data
    mock_buffer_t *buffer = mock_buffer_create(size * 2);
    if (!buffer) {
        parser->error_code = 3;
        return -1;
    }
    
    // Process input and append to buffer (this creates the call relationship)
    for (size_t i = 0; i < size; i++) {
        char processed_char = input[i];
        
        // Simple processing: convert to uppercase
        if (processed_char >= 'a' && processed_char <= 'z') {
            processed_char = processed_char - 'a' + 'A';
        }
        
        // Use mock_buffer_append (this is the key call relationship)
        if (mock_buffer_append(buffer, &processed_char, 1) != 0) {
            mock_buffer_destroy(buffer);
            parser->error_code = 4;
            return -1;
        }
    }
    
    // Store the processed data in parser
    if (parser->input) {
        free(parser->input);
    }
    
    const char *processed_data = mock_buffer_get_data(buffer);
    parser->input_size = buffer->size;
    parser->input = malloc(parser->input_size + 1);
    
    if (!parser->input) {
        mock_buffer_destroy(buffer);
        parser->error_code = 5;
        return -1;
    }
    
    memcpy(parser->input, processed_data, parser->input_size);
    parser->input[parser->input_size] = '\0';
    parser->state = 1; // parsed successfully
    
    mock_buffer_destroy(buffer);
    return 0;
}

/* Utility functions */
int mock_validate_input(const char *input, size_t size) {
    if (!input || size == 0) return 0;
    
    // Simple validation: check for printable characters
    for (size_t i = 0; i < size; i++) {
        if (input[i] < 32 || input[i] > 126) {
            return 0; // Invalid character found
        }
    }
    
    return 1; // Valid
}

const char* mock_get_version(void) {
    return MOCKLIB_VERSION;
}