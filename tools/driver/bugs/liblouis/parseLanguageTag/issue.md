### Title

**Memory leak in `parseLanguageTag` when parsing invalid queries**

### Description

Hi, I ran into a memory leak in `liblouis/metadata.c` while fuzzing. The issue is inside the `parseLanguageTag` function.

Basically, the function builds a linked list in a loop. If it successfully parses the first part of a string (allocating memory for it), but then hits an error on the next part (like if the subtag is too long), it returns `NULL` immediately.

The problem is that it forgets to free the list nodes allocated in the previous steps before returning, leaving them leaked.

### Reproduction

A minimal C program (`memory_leak.c`) to reproduce this without the full fuzzer:

```c
#include <liblouis.h>
#include <stdlib.h>

int main() {
    // "en" is valid (gets allocated). 
    // "123456789" is invalid (triggers the error return).
    // The "en" node gets leaked here.
    char *res = lou_findTable("language:en-123456789");
    
    if (res) lou_freeTableFile(res);
    lou_free();
    return 0;
}

```

### Build & Run

Use `afl-clang-fast` with ASan enabled:

```bash
afl-clang-fast -fsanitize=address -g \
       -I/path/to/liblouis/include \
       -L/path/to/liblouis/lib \
       memory_leak.c \
       -llouis \
       -o memory_leak

./memory_leak

```

### Logs

Here is the LeakSanitizer output showing the leak in `list_conj`:

```text
==652179==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 32 byte(s) in 1 object(s) allocated from:
    #0 0x5f7922c722b3 in malloc
    #1 0x5f7922ccd24c in list_conj liblouis/metadata.c:61:10
    #2 0x5f7922ccd24c in parseLanguageTag liblouis/metadata.c:305:11

Indirect leak of 3 byte(s) in 1 object(s) allocated from:
    #0 0x5f7922c59fbe in strdup
    #1 0x5f7922ccd23f in parseLanguageTag liblouis/metadata.c:305:27

SUMMARY: AddressSanitizer: 35 byte(s) leaked in 2 allocation(s).

```

### Possible Fix

We just need to check if the `list` isn't empty and free it before returning `NULL` on those error checks inside the loop.

Thanks!