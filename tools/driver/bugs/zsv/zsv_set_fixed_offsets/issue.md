### Issue Title

**`zsv_set_fixed_offsets` crashes on NULL offsets (segfault)**

### Description

Hey, I noticed a crash in `zsv_set_fixed_offsets`.

It looks like the function validates `count` (checking if it's 0), but it **forgets to check if the `offsets` pointer itself is NULL** before using it.

So if I pass `NULL` by mistake, it immediately triggers a Segfault. Since you are already doing validation for other args, it would make sense to handle `NULL` gracefully here too, rather than crashing.

### Quick Repro

```c
zsv_set_fixed_offsets(parser, 5, NULL); // <--- BOOM

```

### Fix

Just adding a check like this should fix it:

```c
if (!count) {
    // ... existing check ...
}

// Add this:
if (!offsets) {
    return zsv_status_invalid_option;
}

```
