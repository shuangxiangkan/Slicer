#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

// 这个harness没有输入依赖性 - 不管输入什么都执行相同的代码路径
int main() {
    char buffer[1024];
    size_t bytes_read;
    
    // 读取输入但不使用
    bytes_read = read(STDIN_FILENO, buffer, sizeof(buffer) - 1);
    
    // 不管输入是什么，都执行相同的代码
    printf("Starting fixed execution path\n");
    
    for (int i = 0; i < 10; i++) {
        printf("Loop iteration %d\n", i);
    }
    
    printf("Fixed calculation: %d\n", 42 * 3);
    
    printf("Always the same output\n");
    
    return 0;
}