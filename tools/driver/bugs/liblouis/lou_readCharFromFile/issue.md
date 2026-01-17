### Title

NULL pointer dereference in `lou_readCharFromFile`

### Description

Hi,

I discovered a segmentation fault in `lou_readCharFromFile` (in `compileTranslationTable.c`) while fuzzing `liblouis`.

The function dereferences the `mode` pointer immediately without checking if it is valid. Passing `NULL` as the second argument causes a direct crash.


```c
// compileTranslationTable.c
if (*mode == 1) { // Crashes here if mode is NULL

```

I noticed that **#1117** and **#1399** previously suggested removing this function entirely as it appears to be unused.

If it is not removed, I suggest to fix this bug by adding a NULL check.

