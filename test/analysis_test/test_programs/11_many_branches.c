int many_branches_test(int op, int a, int b, int c) {
    int result = 0;
    int temp = a;
    
    if (op == 1) {
        result = temp + b;
    } else if (op == 2) {
        result = temp - b;
    } else if (op == 3) {
        result = temp * b;
    } else if (op == 4) {
        result = temp / b;
    } else if (op == 5) {
        result = temp % b;
    } else if (op == 6) {
        result = temp & b;
    } else if (op == 7) {
        result = temp | b;
    } else if (op == 8) {
        result = temp ^ b;
    } else if (op == 9) {
        result = temp << b;
    } else if (op == 10) {
        result = temp >> b;
    } else {
        result = 0;
    }
    
    if (result > 0) {
        if (c > 0) {
            result = result + c;
        } else {
            result = result - c;
        }
    }
    
    return result;
}

