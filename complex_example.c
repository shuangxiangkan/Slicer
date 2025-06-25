#include <stdio.h>

int complex_function(int a, int b, int c) {
    int x = a + 1;                    // 行4
    int y = b * 2;                    // 行5  
    int z = c - 3;                    // 行6
    
    int intermediate1 = x + y;        // 行8
    int intermediate2 = y + z;        // 行9
    int intermediate3 = x * z;        // 行10
    
    int sum = intermediate1 + intermediate2;  // 行12
    int product = intermediate3 * 2;          // 行13
    
    if (sum > 10) {                   // 行15
        sum = sum - 5;                // 行16
        product = product + sum;      // 行17
    } else {                          // 行18
        sum = sum + 2;                // 行19
        product = product - 1;        // 行20
    }
    
    int final_result = sum + product;         // 行23
    int unused_var = a * b * c;               // 行24 (不影响最终结果)
    
    return final_result;              // 行26
}

int main() {
    int result = complex_function(5, 3, 2);
    printf("Result: %d\n", result);
    return 0;
}
