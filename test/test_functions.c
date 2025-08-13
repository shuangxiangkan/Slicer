// // 测试函数集合 - 用于CDG/DDG/PDG分析
// #include <stdio.h>

// http://zhuanlan.zhihu.com/p/572554127
int zhihu() {
    int i;
    scanf("%d", &i);

    if (i == 1) {
        printf("POS:\n");
    } else {
        i = 1;
    }

    printf("%d\n", i);
    return 0;
}

// https://uditagarwal.in/understanding-dependency-graphs-for-program-analysis/
void fuzzware() {
    int a = 10;
    int b, c;

    while (a > 0) {
        a = a - 1;
    }

    b = 3;

    if (a * b) {
        a = 10;
    } else {
        if (b) {
            b = 0;
        } else {
            b = 1;
        }
    }

    c = a + b;
}

// https://home.cs.colorado.edu/~kena/classes/5828/s99/lectures/lecture25.pdf
int lecture25() {
    int X, Y;
    scanf("%d", &X);
    scanf("%d", &Y);

    while (X > 10) {
        X = X - 10;
        if (X == 10) {
            break;
        }
    }

    if (Y < 20 && X % 2 == 0) {
        Y = Y + 20;
    } else {
        Y = Y - 20;
    }

    return 2 * X + Y;   
}


void ware() {
    int a = 1;
    int b = 2;
    int c = b;
    while (c > a) {
        a = a + 1;
        c = c + 2;
    }
    int d = c;
}

// 简单的加法函数
int add(int a, int b) {
    return a + b;
}

// 带条件的最大值函数
int max(int a, int b) {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

// 带循环的求和函数
int sum(int n) {
    int result = 0;
    int i = 1;
    while (i <= n) {
        result = result + i;
        i = i + 1;
    }
    return result;
}

// 递归阶乘函数
int factorial(int n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

// 斐波那契数列（带更复杂的控制结构）
int fibonacci(int n) {
    if (n <= 0) {
        return 0;
    } else if (n == 1) {
        return 1;
    } else {
        return fibonacci(n - 1) + fibonacci(n - 2);
    }
}

// 成绩转换函数（带switch语句）
int grade_to_points(char grade) {
    int points;
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

// // 数组求和函数（带for循环）
int array_sum(int arr[], int size) {
    int sum = 0;
    int i;
    for (i = 0; i < size; i++) {
        sum = sum + arr[i];
    }
    return sum;
}


// int processNumbers() {
//     int x, y, result = 0;
//     int attempts = 0;
    
//     printf("Enter two integers: ");
    
// input_retry:
//     attempts++;
//     if (attempts > 3) {
//         printf("Too many invalid attempts!\n");
//         goto cleanup;
//     }
    
//     if (scanf("%d %d", &x, &y) != 2) {
//         printf("Invalid input! Please enter two integers: ");
//         // Clear input buffer
//         int c;
//         while ((c = getchar()) != '\n' && c != EOF);
//         goto input_retry;
//     }
    
//     if (x <= 0 || y <= 0) {
//         printf("Numbers must be positive! Try again: ");
//         goto input_retry;
//     }
    
//     // Process the numbers
//     for (int i = 1; i <= x; i++) {
//         for (int j = 1; j <= y; j++) {
//             result += i * j;
            
//             // Special condition to jump to output
//             if (result > 1000) {
//                 printf("Result exceeded 1000, stopping early!\n");
//                 goto output;
//             }
//         }
//     }
    
//     // Additional processing
//     if (result % 2 == 0) {
//         result += 10;
//     } else {
//         result -= 5;
//     }
    
// output:
//     printf("Final result: %d\n", result);
//     printf("Processing completed successfully!\n");
//     return result;
    
// cleanup:
//     printf("Function terminated due to errors.\n");
//     return -1;
// }

// void check_number(int num) {
//     if (num > 5) {
//         goto greater;
//     }

//     // 如果 num <= 5，执行这里的代码
//     printf("数字小于或等于 5\n");
//     return;

// greater:
//     // goto greater; 语句会跳转到这里
//     printf("数字大于 5\n");
//     return;
}