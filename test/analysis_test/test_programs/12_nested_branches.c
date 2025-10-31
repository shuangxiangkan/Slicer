int nested_branches_test(int a, int b, int c, int d) {
    int result = 0;
    
    if (a > 0) {
        if (b > 0) {
            if (c > 0) {
                if (d > 0) {
                    result = a + b + c + d;
                } else {
                    result = a + b + c - d;
                }
            } else {
                if (d > 0) {
                    result = a + b - c + d;
                } else {
                    result = a + b - c - d;
                }
            }
        } else {
            if (c > 0) {
                result = a - b + c;
            } else {
                result = a - b - c;
            }
        }
    } else {
        if (b > 0) {
            result = -a + b;
        } else {
            result = -a - b;
        }
    }
    
    return result;
}

