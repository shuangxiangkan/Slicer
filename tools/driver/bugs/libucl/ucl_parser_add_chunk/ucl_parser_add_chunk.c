#include <ucl.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    FILE *f = fopen(argv[1], "rb");
    fseek(f, 0, SEEK_END);
    size_t size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    uint8_t *data = malloc(size);
    fread(data, 1, size, f);
    fclose(f);
    
    struct ucl_parser *parser = ucl_parser_new(0);
    ucl_object_t *obj = NULL;
    
    if (ucl_parser_add_chunk(parser, data, size)) {
        obj = ucl_parser_get_object(parser);
    }
    
    ucl_parser_free(parser);
    
    if (obj != NULL) {
        ucl_object_free(obj);
    }
    
    free(data);
    return 0;
}