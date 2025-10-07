#ifndef MOCKLIB_H
#define MOCKLIB_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Mock library version */
#define MOCKLIB_VERSION "1.0.0"

/* Mock library API marker */
#define MOCKLIB_API

/* Mock data structures */
typedef struct mock_buffer {
    char *data;
    size_t size;
    size_t capacity;
} mock_buffer_t;

typedef struct mock_parser {
    int state;
    char *input;
    size_t input_size;
    int error_code;
} mock_parser_t;

/* Core API functions (10 total, with 2 having call relationships) */

/* Buffer management functions */
MOCKLIB_API mock_buffer_t* mock_buffer_create(size_t initial_capacity);
MOCKLIB_API void mock_buffer_destroy(mock_buffer_t *buffer);
MOCKLIB_API int mock_buffer_append(mock_buffer_t *buffer, const char *data, size_t size);
MOCKLIB_API int mock_buffer_resize(mock_buffer_t *buffer, size_t new_capacity);
MOCKLIB_API const char* mock_buffer_get_data(mock_buffer_t *buffer);

/* Parser functions (mock_parser_parse calls mock_buffer_append internally) */
MOCKLIB_API mock_parser_t* mock_parser_create(void);
MOCKLIB_API void mock_parser_destroy(mock_parser_t *parser);
MOCKLIB_API int mock_parser_parse(mock_parser_t *parser, const char *input, size_t size);  // Calls mock_buffer_append

/* Utility functions */
MOCKLIB_API int mock_validate_input(const char *input, size_t size);
MOCKLIB_API const char* mock_get_version(void);

#ifdef __cplusplus
}
#endif

#endif /* MOCKLIB_H */