// 测试函数集合
// 用于CFG/DDG/PDG分析测试

// 简单顺序函数
int add(int a, int b) {
    int result = a + b;
    return result;
}

// 简单条件函数
int max(int a, int b) {

    
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

// 简单循环函数
int sum(int n) {
    int total = 0;
    int i = 1;
    while (i <= n) {
        total = total + i;
        i = i + 1;
    }
    return total;
}

// 简单嵌套函数
int factorial(int n) {
    int result = 1;
    if (n > 0) {
        int i = 1;
        while (i <= n) {
            result = result * i;
            i = i + 1;
        }
    }
    return result;
}

// 更复杂的函数
int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    
    int a = 0;
    int b = 1;
    int i = 2;
    
    while (i <= n) {
        int temp = a + b;
        a = b;
        b = temp;
        i = i + 1;
    }
    
    return b;
}

// 带switch的函数
int grade_to_points(char grade) {
    int points = 0;

    switch (grade) {
        case 'A':
            points = 4;
            break;
        case 'B':
            points = 3;
            break;
        case 'C':
            points = 2;
            break;
        case 'D':
            points = 1;
            break;
        default:
            points = 0;
            break;
    }

    return points;
}

// 带for循环的函数
int array_sum(int arr[], int size) {
    int total = 0;
    for (int i = 0; i < size; i++) {
        total = total + arr[i];
    }
    return total;
}
