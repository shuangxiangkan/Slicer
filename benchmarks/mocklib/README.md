# MockLib - Mock Library

MockLib is a mock C library designed for rapid toolchain testing, containing 10 simplified API functions specifically designed for testing without the need to compile complex real libraries.

## File Structure

```
src/
├── mocklib.h          # Header file defining all APIs
├── mocklib.c          # Implementation file
├── CMakeLists.txt     # Build configuration
├── README.md          # This document
├── fuzz/              # Fuzzing test programs
│   ├── fuzz_buffer.c  # Fuzzing tests for buffer APIs
│   └── fuzz_parser.c  # Fuzzing tests for parser APIs
└── test/              # Test cases
    ├── test_buffer.c  # Buffer API tests
    └── test_parser.c  # Parser API tests
```

## API Detailed Description

### 1. Buffer Management APIs

#### `mock_buffer_t* mock_buffer_create(size_t capacity)`
**Function**: Create a new buffer object
**Parameters**: 
- `capacity`: Initial capacity of the buffer
**Return Value**: Returns buffer pointer on success, NULL on failure
**Usage Example**:
```c
mock_buffer_t *buffer = mock_buffer_create(1024);
if (buffer) {
    // Use the buffer
    mock_buffer_destroy(buffer);
}
```

#### `void mock_buffer_destroy(mock_buffer_t* buffer)`
**Function**: Destroy buffer object and free memory
**Parameters**: 
- `buffer`: Buffer pointer to destroy
**Return Value**: None
**Usage Example**:
```c
mock_buffer_destroy(buffer);
```

#### `int mock_buffer_append(mock_buffer_t* buffer, const char* data, size_t size)`
**Function**: Append data to buffer
**Parameters**: 
- `buffer`: Target buffer
- `data`: Data to append
- `size`: Size of data
**Return Value**: Returns 0 on success, -1 on failure
**Usage Example**:
```c
const char *text = "Hello World";
int result = mock_buffer_append(buffer, text, strlen(text));
if (result == 0) {
    printf("Data appended successfully\n");
}
```

#### `int mock_buffer_resize(mock_buffer_t* buffer, size_t new_capacity)`
**Function**: Resize buffer capacity
**Parameters**: 
- `buffer`: Target buffer
- `new_capacity`: New capacity size
**Return Value**: Returns 0 on success, -1 on failure
**Usage Example**:
```c
int result = mock_buffer_resize(buffer, 2048);
if (result == 0) {
    printf("Buffer resized successfully\n");
}
```

#### `const char* mock_buffer_get_data(mock_buffer_t* buffer)`
**Function**: Get data from buffer
**Parameters**: 
- `buffer`: Target buffer
**Return Value**: Returns data pointer on success, NULL on failure
**Usage Example**:
```c
const char *data = mock_buffer_get_data(buffer);
if (data) {
    printf("Buffer content: %s\n", data);
}
```

### 2. Parser APIs

#### `mock_parser_t* mock_parser_create(void)`
**Function**: Create a new parser object
**Parameters**: None
**Return Value**: Returns parser pointer on success, NULL on failure
**Usage Example**:
```c
mock_parser_t *parser = mock_parser_create();
if (parser) {
    // Use the parser
    mock_parser_destroy(parser);
}
```

#### `void mock_parser_destroy(mock_parser_t* parser)`
**Function**: Destroy parser object and free memory
**Parameters**: 
- `parser`: Parser pointer to destroy
**Return Value**: None
**Usage Example**:
```c
mock_parser_destroy(parser);
```

#### `int mock_parser_parse(mock_parser_t* parser, const char* input, size_t size)`
**Function**: Parse input data (internally calls mock_buffer_append)
**Parameters**: 
- `parser`: Parser object
- `input`: Input data to parse
- `size`: Size of input data
**Return Value**: Returns 0 on success, -1 on failure
**Call Relationship**: This function internally calls `mock_buffer_append` to store parsed data
**Usage Example**:
```c
const char *input = "data to parse";
int result = mock_parser_parse(parser, input, strlen(input));
if (result == 0) {
    printf("Parsing successful\n");
}
```

### 3. Utility Functions

#### `int mock_validate_input(const char* input, size_t size)`
**Function**: Validate input data validity
**Parameters**: 
- `input`: Input data to validate
- `size`: Size of input data
**Return Value**: Returns 1 if valid, 0 if invalid
**Usage Example**:
```c
const char *input = "test data";
if (mock_validate_input(input, strlen(input))) {
    printf("Input data is valid\n");
}
```

#### `const char* mock_get_version(void)`
**Function**: Get library version information
**Parameters**: None
**Return Value**: Returns version string
**Usage Example**:
```c
printf("MockLib version: %s\n", mock_get_version());
```

## API Call Relationships

The following call relationships exist in this library:
- `mock_parser_parse()` → `mock_buffer_append()`

When `mock_parser_parse` is called, it internally calls `mock_buffer_append` to store the parsed data in the parser's internal buffer.

## Build Instructions

Build the library using CMake:

```bash
mkdir build
cd build
cmake ..
make
```

This will generate:
- `libmocklib.a` (static library)
- `libmocklib.so` (dynamic library)

## Testing Instructions

### Running Unit Tests
```bash
# Compile and run buffer tests
gcc -o test_buffer test/test_buffer.c mocklib.c
./test_buffer

# Compile and run parser tests
gcc -o test_parser test/test_parser.c mocklib.c
./test_parser
```

### Running Fuzzing Tests
```bash
# Compile fuzzing tests with libFuzzer
clang -fsanitize=fuzzer -o fuzz_buffer fuzz/fuzz_buffer.c mocklib.c
clang -fsanitize=fuzzer -o fuzz_parser fuzz/fuzz_parser.c mocklib.c

# Run fuzzing tests
./fuzz_buffer
./fuzz_parser
```

## Usage Example

```c
#include "mocklib.h"
#include <stdio.h>
#include <string.h>

int main() {
    // Create parser
    mock_parser_t *parser = mock_parser_create();
    if (!parser) {
        printf("Failed to create parser\n");
        return 1;
    }
    
    // Validate input
    const char *input = "Hello MockLib";
    if (mock_validate_input(input, strlen(input))) {
        // Parse data (internally calls buffer_append)
        if (mock_parser_parse(parser, input, strlen(input)) == 0) {
            printf("Parsing successful\n");
            
            // Get parsed data
            const char *data = mock_buffer_get_data(parser->buffer);
            printf("Parse result: %s\n", data);
        }
    }
    
    // Clean up resources
    mock_parser_destroy(parser);
    
    printf("Library version: %s\n", mock_get_version());
    return 0;
}
```

## Important Notes

1. All functions returning pointers return NULL on failure
2. Must call corresponding destroy functions to free memory after use
3. The `mock_parser_parse` function demonstrates inter-API call relationships
4. This library is designed specifically for testing purposes and is not suitable for production environments