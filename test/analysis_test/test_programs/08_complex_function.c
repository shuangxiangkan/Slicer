int complex_function_test(int x, int y, int z) {
    int a = x + 1;
    int b = y + 2;
    int result = 0;
    
    if (a > b) {
        for (int i = 0; i < a; i++) {
            if (i % 2 == 0) {
                result = result + i;
            } else {
                result = result - i;
            }
        }
    } else {
        int temp = b;
        while (temp > 0) {
            result = result + temp;
            temp = temp - 1;
        }
    }
    
    result = result + z;
    return result;
}

