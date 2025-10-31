int multiple_paths_test(int x, int y, int z) {
    int a = x + 1;
    int b = y + 1;
    int c;
    if (a > b) {
        c = a + z;
    } else {
        c = b + z;
    }
    int d = c * 2;
    return d;
}

