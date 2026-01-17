#include <stdio.h>
#include <stdlib.h>
#include <liblouis.h>

int main(int argc, char **argv) {
    /*
     * 触发逻辑分析：
     * 查询字符串: "language:en-123456789"
     * * 1. liblouis 解析 "language:" 前缀，进入 parseLanguageTag。
     * 2. 第一轮循环：解析 "en"。
     * - 长度合法，字符合法。
     * - malloc 分配内存存储 "en" 节点，挂载到局部变量 list 上。
     * 3. 第二轮循环：解析 "123456789"。
     * - 长度为 9。
     * - 命中代码: if (len < 1 || len > 8) return NULL;
     * 4. Bug 发生：函数直接返回 NULL，第一轮分配的 "en" 节点指针丢失，且未被释放。
     */
    const char *trigger_query = "language:en-123456789";

    printf("[+] Attempting to trigger leak with query: %s\n", trigger_query);

    // 1. 调用函数触发内部泄漏
    char *result = lou_findTable(trigger_query);

    // 2. 正常处理返回值（尽管这里预期返回 NULL）
    if (result) {
        printf("[-] Unexpected result found.\n");
        lou_freeTableFile(result);
    } else {
        printf("[+] lou_findTable returned NULL (expected behavior for invalid query).\n");
    }

    // 3. 调用全局清理。
    // 如果内存是全局缓存，这里会被释放。
    // 如果 ASan 仍然报错，说明这是真正的局部逻辑泄漏。
    lou_free();
    
    printf("[+] Exiting. AddressSanitizer should report a leak below:\n");
    return 0;
}