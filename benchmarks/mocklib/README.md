# MockLib - 模拟库

MockLib 是一个用于快速测试工具链生成的模拟C库，包含10个简化的API函数，专门设计用于测试而无需实际编译复杂的真实库。

## 文件结构

```
src/
├── mocklib.h          # 头文件，定义所有API
├── mocklib.c          # 实现文件
├── CMakeLists.txt     # 构建配置
├── README.md          # 本文档
├── fuzz/              # 模糊测试程序
│   ├── fuzz_buffer.c  # 针对buffer API的模糊测试
│   └── fuzz_parser.c  # 针对parser API的模糊测试
└── test/              # 测试用例
    ├── test_buffer.c  # buffer API测试
    └── test_parser.c  # parser API测试
```

## API 详细说明

### 1. Buffer管理API

#### `mock_buffer_t* mock_buffer_create(size_t capacity)`
**功能**: 创建一个新的缓冲区对象
**参数**: 
- `capacity`: 缓冲区的初始容量
**返回值**: 成功返回缓冲区指针，失败返回NULL
**使用示例**:
```c
mock_buffer_t *buffer = mock_buffer_create(1024);
if (buffer) {
    // 使用缓冲区
    mock_buffer_destroy(buffer);
}
```

#### `void mock_buffer_destroy(mock_buffer_t* buffer)`
**功能**: 销毁缓冲区对象并释放内存
**参数**: 
- `buffer`: 要销毁的缓冲区指针
**返回值**: 无
**使用示例**:
```c
mock_buffer_destroy(buffer);
```

#### `int mock_buffer_append(mock_buffer_t* buffer, const char* data, size_t size)`
**功能**: 向缓冲区追加数据
**参数**: 
- `buffer`: 目标缓冲区
- `data`: 要追加的数据
- `size`: 数据大小
**返回值**: 成功返回0，失败返回-1
**使用示例**:
```c
const char *text = "Hello World";
int result = mock_buffer_append(buffer, text, strlen(text));
if (result == 0) {
    printf("数据追加成功\n");
}
```

#### `int mock_buffer_resize(mock_buffer_t* buffer, size_t new_capacity)`
**功能**: 调整缓冲区容量
**参数**: 
- `buffer`: 目标缓冲区
- `new_capacity`: 新的容量大小
**返回值**: 成功返回0，失败返回-1
**使用示例**:
```c
int result = mock_buffer_resize(buffer, 2048);
if (result == 0) {
    printf("缓冲区扩容成功\n");
}
```

#### `const char* mock_buffer_get_data(mock_buffer_t* buffer)`
**功能**: 获取缓冲区中的数据
**参数**: 
- `buffer`: 目标缓冲区
**返回值**: 返回数据指针，失败返回NULL
**使用示例**:
```c
const char *data = mock_buffer_get_data(buffer);
if (data) {
    printf("缓冲区内容: %s\n", data);
}
```

### 2. Parser API

#### `mock_parser_t* mock_parser_create(void)`
**功能**: 创建一个新的解析器对象
**参数**: 无
**返回值**: 成功返回解析器指针，失败返回NULL
**使用示例**:
```c
mock_parser_t *parser = mock_parser_create();
if (parser) {
    // 使用解析器
    mock_parser_destroy(parser);
}
```

#### `void mock_parser_destroy(mock_parser_t* parser)`
**功能**: 销毁解析器对象并释放内存
**参数**: 
- `parser`: 要销毁的解析器指针
**返回值**: 无
**使用示例**:
```c
mock_parser_destroy(parser);
```

#### `int mock_parser_parse(mock_parser_t* parser, const char* input, size_t size)`
**功能**: 解析输入数据（内部调用mock_buffer_append）
**参数**: 
- `parser`: 解析器对象
- `input`: 要解析的输入数据
- `size`: 输入数据大小
**返回值**: 成功返回0，失败返回-1
**调用关系**: 此函数内部会调用`mock_buffer_append`来存储解析的数据
**使用示例**:
```c
const char *input = "data to parse";
int result = mock_parser_parse(parser, input, strlen(input));
if (result == 0) {
    printf("解析成功\n");
}
```

### 3. 工具函数

#### `int mock_validate_input(const char* input, size_t size)`
**功能**: 验证输入数据的有效性
**参数**: 
- `input`: 要验证的输入数据
- `size`: 输入数据大小
**返回值**: 有效返回1，无效返回0
**使用示例**:
```c
const char *input = "test data";
if (mock_validate_input(input, strlen(input))) {
    printf("输入数据有效\n");
}
```

#### `const char* mock_get_version(void)`
**功能**: 获取库的版本信息
**参数**: 无
**返回值**: 返回版本字符串
**使用示例**:
```c
printf("MockLib版本: %s\n", mock_get_version());
```

## API调用关系

本库中存在以下调用关系：
- `mock_parser_parse()` → `mock_buffer_append()`

当调用`mock_parser_parse`时，它会内部调用`mock_buffer_append`来将解析的数据存储到解析器的内部缓冲区中。

## 构建说明

使用CMake构建库：

```bash
mkdir build
cd build
cmake ..
make
```

这将生成：
- `libmocklib.a` (静态库)
- `libmocklib.so` (动态库)

## 测试说明

### 运行单元测试
```bash
# 编译并运行buffer测试
gcc -o test_buffer test/test_buffer.c mocklib.c
./test_buffer

# 编译并运行parser测试
gcc -o test_parser test/test_parser.c mocklib.c
./test_parser
```

### 运行模糊测试
```bash
# 使用libFuzzer编译模糊测试
clang -fsanitize=fuzzer -o fuzz_buffer fuzz/fuzz_buffer.c mocklib.c
clang -fsanitize=fuzzer -o fuzz_parser fuzz/fuzz_parser.c mocklib.c

# 运行模糊测试
./fuzz_buffer
./fuzz_parser
```

## 使用示例

```c
#include "mocklib.h"
#include <stdio.h>
#include <string.h>

int main() {
    // 创建解析器
    mock_parser_t *parser = mock_parser_create();
    if (!parser) {
        printf("创建解析器失败\n");
        return 1;
    }
    
    // 验证输入
    const char *input = "Hello MockLib";
    if (mock_validate_input(input, strlen(input))) {
        // 解析数据（内部会调用buffer_append）
        if (mock_parser_parse(parser, input, strlen(input)) == 0) {
            printf("解析成功\n");
            
            // 获取解析后的数据
            const char *data = mock_buffer_get_data(parser->buffer);
            printf("解析结果: %s\n", data);
        }
    }
    
    // 清理资源
    mock_parser_destroy(parser);
    
    printf("库版本: %s\n", mock_get_version());
    return 0;
}
```

## 注意事项

1. 所有返回指针的函数在失败时返回NULL
2. 使用完毕后必须调用相应的destroy函数释放内存
3. `mock_parser_parse`函数展示了API间的调用关系
4. 本库专为测试目的设计，不适用于生产环境