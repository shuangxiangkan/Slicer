int nested_if_test(int x, int y) {
    int result = 0;
    if (x > 0) {
        if (y > 0) {
            result = x + y;
        } else {
            result = x - y;
        }
    }
    return result;
}

