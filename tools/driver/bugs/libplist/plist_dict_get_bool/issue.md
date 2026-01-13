## Crash when passing NULL key to plist_dict_* functions

Hey! I've been fuzzing libplist and found that passing a NULL key to `plist_dict_copy_int()` and related functions causes a segfault.

According to the API docs, `plist_dict_copy_int()` should return `PLIST_ERR_INVALID_ARG` for invalid arguments, but when you pass a NULL key it crashes instead.

```c
plist_t target = plist_new_dict();
plist_t source = plist_new_dict();
plist_dict_set_item(source, "test", plist_new_int(42));

// Should return PLIST_ERR_INVALID_ARG, but crashes
plist_err_t err = plist_dict_copy_int(target, source, NULL, NULL);
```

The crash happens in `strcmp()` because `plist_dict_get_item()` doesn't check if the key is NULL before using it. Interestingly, the function does check `alt_source_key`:

```c
if (plist_dict_get_item(source_dict, (alt_source_key) ? alt_source_key : key) == NULL) {
    return PLIST_ERR_INVALID_ARG;
}
```

So it tries to handle the case where the item doesn't exist, but crashes before reaching this check when both `key` and `alt_source_key` are NULL.

This affects all the dict functions that take a key parameter - `plist_dict_get_item()`, `plist_dict_get_int()`, `plist_dict_copy_int()`, etc.

I know passing NULL isn't normal usage, but crashing instead of returning an error seems inconsistent with what the API promises. 