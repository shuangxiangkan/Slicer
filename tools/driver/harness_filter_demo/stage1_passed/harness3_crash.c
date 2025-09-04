#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// 这个harness可能会崩溃 - 有缓冲区溢出和空指针解引用
int main() {
    char small_buffer[10];
    char* ptr = NULL;
    size_t bytes_read;
    
    // 从stdin读取输入
    bytes_read = read(STDIN_FILENO, small_buffer, 1000);  // 缓冲区溢出！
    
    if (bytes_read > 0) {
        small_buffer[bytes_read] = '\0';
        
        // 检查特定输入模式
        if (strstr(small_buffer, "crash") != NULL) {
            // 故意的空指针解引用
            *ptr = 'x';
        }
        
        if (strstr(small_buffer, "overflow") != NULL) {
            // 故意的缓冲区溢出
            strcpy(small_buffer, "This is a very long string that will definitely overflow the small buffer and cause problems");
        }
        
        printf("Input processed: %s\n", small_buffer);
    }
    
    return 0;
}