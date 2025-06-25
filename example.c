#include <stdio.h>

int example_function(int a, int b) {
    int x = a + 1;          // 行4
    int y = b * 2;          // 行5
    int z = x + y;          // 行6
    int result = z * 3;     // 行7
    
    if (result > 10) {      // 行9
        result = result - 5;  // 行10
    }
    
    int temp = result + 1;  // 行13
    return temp;            // 行14
}

int main() {
    int num1 = 5;
    int num2 = 3;
    int output = example_function(num1, num2);
    printf("Result: %d\n", output);
    return 0;
} 