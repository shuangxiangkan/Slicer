# C/C++ 函数程序切片工具

基于 tree-sitter 的 C/C++ 函数程序切片工具，支持单函数的后向切片和前向切片分析。

## 功能特性

- **语法分析**: 使用 tree-sitter 进行精确的 C/C++ 语法分析
- **依赖分析**: 构建函数内变量的定义-使用依赖图
- **程序切片**: 支持后向切片（找到影响目标变量的语句）和前向切片（找到被目标变量影响的语句）
- **参数切片分析**: 生成代码片段供大模型分析数据流依赖关系
- **可视化输出**: 清晰显示切片结果和参数分析报告

## 安装依赖

首先创建并激活虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者
venv\Scripts\activate     # Windows
```

安装依赖包：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本语法

**程序切片**:
```bash
python slicer.py <源文件> <函数名> <目标变量> <目标行号> [选项]
```

**参数切片分析**:
```bash
python slicer.py <源文件> <函数名> --taint [选项]
```

### 参数说明

- `源文件`: C/C++ 源代码文件路径
- `函数名`: 要分析的函数名称
- `目标变量`: 切片的目标变量名（参数切片分析时不需要）
- `目标行号`: 目标变量所在的行号（参数切片分析时不需要）

### 可选参数

- `--language {c,cpp}`: 指定语言类型（默认: c）
- `--type {backward,forward,both}`: 切片类型（默认: both）
  - `backward`: 后向切片，找到影响目标变量的所有语句
  - `forward`: 前向切片，找到被目标变量影响的所有语句
  - `both`: 同时进行前向和后向切片（默认选项）
- `--taint`: 执行参数切片分析，生成代码片段供大模型分析数据流依赖关系
- `--no-save`: 不保存切片结果到文件，只显示在终端
- `--output-dir`: 指定输出目录（默认为当前目录）

### 使用示例

1. **综合切片分析**（默认，推荐）：
```bash
python slicer.py example.c example_function temp 13
```
这将同时进行前向和后向切片，并生成3个文件：
- `example_example_function_temp_line13_backward_slice.c` - 后向切片
- `example_example_function_temp_line13_forward_slice.c` - 前向切片  
- `example_example_function_temp_line13_combined_slice.c` - 综合切片

2. **仅后向切片分析**：
```bash
python slicer.py example.c example_function temp 13 --type backward
```

3. **仅前向切片分析**：
```bash
python slicer.py example.c example_function x 4 --type forward
```

4. **C++ 代码分析**：
```bash
python slicer.py example.cpp my_function var_name 10 --language cpp
```

5. **只显示不保存**：
```bash
python slicer.py example.c example_function temp 13 --no-save
```

6. **指定输出目录**：
```bash
python slicer.py example.c example_function temp 13 --output-dir ./slices
```

7. **参数切片分析**：
```bash
python slicer.py complex_example.c complex_function --taint
```

8. **参数切片分析并保存到指定目录**：
```bash
python slicer.py complex_example.c complex_function --taint --output-dir ./param_reports
```

## 示例代码

`example.c` 文件包含了一个示例函数：

```c
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
```

### 切片示例

对变量 `temp` 在第13行进行综合切片分析：

```bash
python slicer.py example.c example_function temp 13
```

输出结果将显示：
1. 影响 `temp` 变量的所有语句（后向切片）
2. 被 `temp` 变量影响的所有语句（前向切片）
3. 自动保存3个切片文件到当前目录

## 输出文件格式

切片结果会保存为带有详细信息的C文件：

### 单独切片文件
- 文件名格式：`原文件名_函数名_变量名_line行号_切片类型_slice.扩展名`
- 例如：`example_example_function_temp_line13_backward_slice.c`

### 综合切片文件  
- 文件名格式：`原文件名_函数名_变量名_line行号_combined_slice.扩展名`
- 包含前向和后向切片的合并结果，用标记区分：
  - `[B]` = 仅后向切片
  - `[F]` = 仅前向切片
  - `[BF]` = 前向和后向切片都包含

### 参数切片分析报告文件
- 文件名格式：`原文件名_函数名_param_slice_时间戳.txt`
- 例如：`complex_example_complex_function_param_slice_20241221_143022.txt`
- 包含详细的参数切片分析和代码片段，供大模型进行数据流分析

## 工作原理

### 程序切片
1. **语法分析**: 使用 tree-sitter 解析 C/C++ 代码，构建抽象语法树（AST）
2. **变量提取**: 从 AST 中提取每个语句的变量定义和使用信息
3. **依赖图构建**: 基于变量的定义-使用关系构建依赖图
4. **切片计算**: 使用深度优先搜索（DFS）在依赖图上进行切片计算
5. **结果输出**: 格式化输出切片结果

### 参数切片分析
1. **参数识别**: 提取函数参数作为分析起点
2. **前向切片**: 对每个参数进行前向切片，找到其影响的代码行
3. **后向切片**: 对返回值进行后向切片，找到影响返回值的代码行
4. **交互分析**: 检测参数间的相互影响关系
5. **代码片段生成**: 为每种分析生成对应的代码片段
6. **大模型提示**: 提供建议的问题供大模型进行数据流分析

## 局限性

- 目前只支持单函数内的程序切片
- 不支持跨函数的依赖分析
- 指针和复杂数据结构的分析有限
- 不处理宏定义和预处理器指令

## 参数切片分析示例

查看 `complex_example.c` 文件，其中包含复杂的参数交互场景，适合进行参数切片分析。

### 分析方法

本工具采用了一种实用的数据流分析方法：

1. **简单预处理**: 使用程序切片技术提取相关代码片段
2. **大模型分析**: 将代码片段提供给大模型进行数据流依赖分析
3. **高效准确**: 结合了程序分析的精确性和大模型的理解能力

### 与大模型结合使用

生成的代码片段可以直接提供给大模型（如ChatGPT、Claude等），询问诸如：
- "参数a是否会影响这些代码行的执行？是否存在数据流依赖？"
- "这些代码行是否会影响函数的返回值？存在什么样的数据流关系？"
- "参数x是否会影响参数y的值？是否存在数据流依赖？"

运行参数切片分析演示：
```bash
python param_slice_demo.py
```

## 扩展功能

未来可以扩展的功能：

- 跨函数调用的程序切片和参数分析
- 指针别名分析
- 控制流依赖分析
- 图形化切片结果展示
- 支持更多编程语言
- 更精确的数据流分析规则
- 与大模型API的直接集成 