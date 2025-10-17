## Description

A memory leak occurs when parsing certain UCL formatted inputs. The leak happens in `ucl_hash_create`  function.

## test.c
```c
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
```

## Test Environment
- Ubuntu 22.04, 64-bit
- Compiled with: `clang -fsanitize=address,leak -g -o test test.c -lucl`

## How to Trigger
```bash
./test poc_file
```

## Version
Latest commit on master branch

## PoC File
https://github.com/X-ANOY/PoC/blob/main/libucl/ucl_parser_add_chunk/PoC

## LeakSanitizer Output
```
=================================================================
==2849668==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 48 byte(s) in 2 object(s) allocated from:
    #0 0x556a476562ee in __interceptor_malloc
    #1 0x556a476db1dd in ucl_hash_create /libucl/src/ucl_hash.c:237:8
    #2 0x556a476d1841 in ucl_parser_add_container /libucl/src/ucl_parser.c:687:21
    #3 0x556a476c1a6d in ucl_parse_value /libucl/src/ucl_parser.c:1831:11
    #4 0x556a476c1a6d in ucl_state_machine /libucl/src/ucl_parser.c:2562:29
    #5 0x556a476b9408 in ucl_parser_add_chunk_full /libucl/src/ucl_parser.c:3053:12
    #6 0x556a476cdd38 in ucl_parser_add_chunk /libucl/src/ucl_parser.c:3100:9
    #7 0x556a47691140 in main test.c:18:9

Indirect leak of 128 byte(s) in 2 object(s) allocated from:
    #0 0x556a476562ee in __interceptor_malloc
    #1 0x556a476a58bb in ucl_object_new_full /libucl/src/ucl_util.c:3014:9
    #2 0x556a476bcff0 in ucl_parse_key /libucl/src/ucl_parser.c:1543:9
    #3 0x556a476bcff0 in ucl_state_machine /libucl/src/ucl_parser.c:2527:9
    #4 0x556a476b9408 in ucl_parser_add_chunk_full /libucl/src/ucl_parser.c:3053:12
    #5 0x556a476cdd38 in ucl_parser_add_chunk /libucl/src/ucl_parser.c:3100:9
    #6 0x556a47691140 in main test.c:18:9

SUMMARY: LeakSanitizer: 176 byte(s) leaked in 4 allocation(s).
```