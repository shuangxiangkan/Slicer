# Slicer - C/C++变量切片工具

## 概述

Slicer是一个基于tree-sitter的C/C++函数级变量切片工具。给定一个函数体和变量名，它能够提取出与该变量相关的所有代码段，包括声明、赋值、使用、控制流等。

## 功能特性

- ✅ 支持C和C++语法解析
- ✅ 精确的变量识别和依赖分析
- ✅ 支持复杂控制流（if/while/for/switch等）
- ✅ 支持指针操作和数组访问
- ✅ 支持函数调用和表达式
- ✅ 尽量保证输出代码语法正确
- ✅ 与项目中的parser模块无缝集成

## 安装依赖

```bash
pip install tree-sitter tree-sitter-c tree-sitter-cpp
```

## 快速开始

```python
from slicer import slice_function_by_variable

# 示例函数
function_code = '''
int foo(int a) {
    int x = 0;
    int y = 1;
    x = a + 1;
    y = x * 2;
    if (x > 0) {
        y = y + x;
    }
    return y;
}
'''

# 对变量x进行切片
result = slice_function_by_variable(function_code, "x", language="c")
print(result)
```

输出：
```c
    int x = 0;
    x = a + 1;
    y = x * 2;
    if (x > 0) {
        y = y + x;
    }
```

## API参考

### slice_function_by_variable

```python
def slice_function_by_variable(function_code: str, variable: str, language: str = "c") -> str:
    """
    对函数体进行变量相关切片
    
    Args:
        function_code: 函数体源码字符串
        variable: 变量名
        language: "c" 或 "cpp"
    
    Returns:
        与变量相关的代码片段字符串
    """
```

### VariableSlicer类

```python
class VariableSlicer:
    """变量切片器"""
    
    def __init__(self, language: str = "c"):
        """初始化切片器"""
    
    def slice_function_by_variable(self, function_code: str, variable: str) -> str:
        """对函数体进行变量相关切片"""
```

## 与parser模块集成

Slicer工具设计为与项目中的parser模块协同工作，可以对benchmarks中的真实项目进行分析：

```python
from parser import RepoAnalyzer
from slicer import slice_function_by_variable

# 分析cJSON项目
analyzer = RepoAnalyzer('benchmarks/configs/cjson_config.json')
result = analyzer.analyze()

# 获取所有函数
functions = analyzer.get_functions()

# 找到目标函数
target_func = None
for func in functions:
    if func.name == 'parse_number' and not func.is_declaration:
        target_func = func
        break

# 对函数中的变量进行切片
if target_func:
    function_body = target_func.get_body()
    if function_body:
        # 对变量 'number' 进行切片
        slice_result = slice_function_by_variable(function_body, "number", language="c")
        print(f"函数 {target_func.name} 中变量 'number' 的切片结果：")
        print(slice_result)
```

## 示例

### 1. 简单变量跟踪

```python
code = '''
int calculate(int n) {
    int result = 1;
    for (int i = 1; i <= n; i++) {
        result *= i;
    }
    return result;
}
'''

# 跟踪result变量
print(slice_function_by_variable(code, "result"))
```

### 2. 复杂控制流

```python
code = '''
int search(int arr[], int size, int target) {
    int found = -1;
    for (int i = 0; i < size; i++) {
        if (arr[i] == target) {
            found = i;
            break;
        }
    }
    return found;
}
'''

# 跟踪found变量
print(slice_function_by_variable(code, "found"))
```

### 3. C++特性

```python
code = '''
void process(std::vector<int>& vec) {
    auto it = vec.begin();
    for (; it != vec.end(); ++it) {
        *it *= 2;
    }
}
'''

# 跟踪it变量
print(slice_function_by_variable(code, "it", language="cpp"))
```

## 文件结构

```
slicer/
├── __init__.py          # 包初始化文件
├── slice.py             # 核心切片实现
└── README.md            # 本文档

test/
└── test_variable_slicer.py  # 综合测试用例
```

## 测试

运行测试（包含benchmarks项目集成测试）：
```bash
python test/test_variable_slicer.py
```

测试内容包括：
- 基本变量切片功能
- cJSON项目真实函数测试
- miniz项目真实函数测试
- parser模块集成测试

## 测试项目支持

工具已在以下benchmarks项目中测试：

- **cJSON**: JSON解析库，测试函数如`parse_number`, `parse_string`等
- **miniz**: 压缩库，测试函数如`mz_deflateInit`, `mz_compress`等
- **zlib**: 压缩库（配置可用）
- **utf8**: UTF-8处理库（配置可用）

## 当前限制

1. 目前主要关注函数级别的切片，不支持跨函数分析
2. 变量识别基于名称匹配，可能存在变量作用域混淆
3. 语法修复功能有限，输出代码可能需要手动调整
4. 不支持宏展开和预处理器指令
5. 某些复杂函数的get_body()可能返回None

## 未来改进

- [ ] 更精确的作用域分析
- [ ] 数据流和控制流依赖分析
- [ ] 语法修复和代码补全
- [ ] 跨函数变量依赖追踪
- [ ] 可视化输出支持
- [ ] 改进get_body()的兼容性 