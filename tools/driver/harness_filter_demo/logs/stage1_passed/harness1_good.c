#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// 一个好的harness示例 - 能正常编译和执行，有输入依赖性
int main() {
    char buffer[1024];
    size_t bytes_read;
    
    // 从stdin读取输入
    bytes_read = read(STDIN_FILENO, buffer, sizeof(buffer) - 1);
    
    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        
        // 根据输入内容执行不同的代码路径
        if (strstr(buffer, "test") != NULL) {
            printf("Found test string\n");
            
            if (strstr(buffer, "json") != NULL) {
                printf("JSON test detected\n");
                // 模拟JSON解析路径
                for (int i = 0; i < strlen(buffer); i++) {
                    if (buffer[i] == '{' || buffer[i] == '}') {
                        printf("JSON bracket at position %d\n", i);
                    }
                }
            }
            
            if (strstr(buffer, "xml") != NULL) {
                printf("XML test detected\n");
                // 模拟XML解析路径
                for (int i = 0; i < strlen(buffer); i++) {
                    if (buffer[i] == '<' || buffer[i] == '>') {
                        printf("XML bracket at position %d\n", i);
                    }
                }
            }
        } else if (strstr(buffer, "data") != NULL) {
            printf("Found data string\n");
            
            // 模拟数据处理路径
            int sum = 0;
            for (int i = 0; i < strlen(buffer); i++) {
                sum += buffer[i];
            }
            printf("Data checksum: %d\n", sum);
            
        } else {
            printf("Unknown input format\n");
        }
        
        // 根据输入长度执行不同逻辑
        if (bytes_read < 10) {
            printf("Short input\n");
        } else if (bytes_read < 100) {
            printf("Medium input\n");
        } else {
            printf("Long input\n");
        }
    } else {
        printf("No input received\n");
        return 1;
    }
    
    return 0;
}