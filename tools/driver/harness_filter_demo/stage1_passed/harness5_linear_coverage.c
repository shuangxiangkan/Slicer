#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// 这个harness有线性覆盖率增长问题 - 覆盖率与输入大小成正比
int main() {
    char buffer[1024];
    size_t bytes_read;
    
    // 从stdin读取输入
    bytes_read = read(STDIN_FILENO, buffer, sizeof(buffer) - 1);
    
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        
        printf("Processing %zu bytes\n", bytes_read);
        
        // 线性处理每个字符 - 覆盖率与输入长度成正比
        for (size_t i = 0; i < bytes_read; i++) {
            switch (buffer[i]) {
                case 'a': printf("Found a at %zu\n", i); break;
                case 'b': printf("Found b at %zu\n", i); break;
                case 'c': printf("Found c at %zu\n", i); break;
                case 'd': printf("Found d at %zu\n", i); break;
                case 'e': printf("Found e at %zu\n", i); break;
                case 'f': printf("Found f at %zu\n", i); break;
                case 'g': printf("Found g at %zu\n", i); break;
                case 'h': printf("Found h at %zu\n", i); break;
                case 'i': printf("Found i at %zu\n", i); break;
                case 'j': printf("Found j at %zu\n", i); break;
                case 'k': printf("Found k at %zu\n", i); break;
                case 'l': printf("Found l at %zu\n", i); break;
                case 'm': printf("Found m at %zu\n", i); break;
                case 'n': printf("Found n at %zu\n", i); break;
                case 'o': printf("Found o at %zu\n", i); break;
                case 'p': printf("Found p at %zu\n", i); break;
                case 'q': printf("Found q at %zu\n", i); break;
                case 'r': printf("Found r at %zu\n", i); break;
                case 's': printf("Found s at %zu\n", i); break;
                case 't': printf("Found t at %zu\n", i); break;
                case 'u': printf("Found u at %zu\n", i); break;
                case 'v': printf("Found v at %zu\n", i); break;
                case 'w': printf("Found w at %zu\n", i); break;
                case 'x': printf("Found x at %zu\n", i); break;
                case 'y': printf("Found y at %zu\n", i); break;
                case 'z': printf("Found z at %zu\n", i); break;
                default: printf("Other char at %zu\n", i); break;
            }
        }
    }
    
    return 0;
}