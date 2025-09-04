#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 这个harness有编译错误 - 缺少头文件和语法错误
int main() {
    char buffer[1024];
    
    // 语法错误：缺少分号
    size_t bytes_read = read(STDIN_FILENO, buffer, sizeof(buffer) - 1)
    
    // 未定义的函数调用
    undefined_function();
    
    // 类型错误
    int* ptr = "string";
    
    return 0;
}