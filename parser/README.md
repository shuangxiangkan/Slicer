# Parser 模块

这是一个基于 tree-sitter 的 C/C++ 代码解析模块，用于分析项目中的函数定义。

## 主要功能

- **文件发现**: 自动在目录中递归查找所有 C/C++ 文件
- **函数提取**: 解析代码并提取所有函数定义和声明
- **项目分析**: 对整个代码仓库进行全面的函数分析
- **搜索功能**: 支持正则表达式搜索特定函数
- **重复检测**: 自动发现重复的函数定义
- **报告生成**: 生成详细的分析报告

## 模块结构

```
parser/
├── __init__.py              # 模块初始化
├── file_finder.py           # 文件查找器
├── function_extractor.py    # 函数提取器
├── repo_analyzer.py         # 仓库分析器
└── README.md               # 说明文档
```

## 主要类

### FileFinder
负责在目录中查找 C/C++ 文件。

```python
from parser import FileFinder

finder = FileFinder()
files = finder.find_files("/path/to/project", recursive=True)
finder.print_file_list()
```

### FunctionExtractor
使用 tree-sitter 提取函数定义。

```python
from parser import FunctionExtractor

extractor = FunctionExtractor()
functions = extractor.extract_from_file("example.c")
extractor.print_functions(functions)
```

### RepoAnalyzer
整合文件查找和函数提取，对整个项目进行分析。

```python
from parser import RepoAnalyzer

analyzer = RepoAnalyzer()
result = analyzer.analyze_repository("/path/to/project")
analyzer.print_all_functions()
```

## 命令行使用

项目根目录提供了 `analyze_repo.py` 作为简化的命令行接口：

```bash
# 分析当前目录
python analyze_repo.py .

# 分析单个文件
python analyze_repo.py example.c

# 搜索特定函数
python analyze_repo.py . --search "main"

# 生成报告
python analyze_repo.py . --report analysis_report.md

# 只显示统计信息
python analyze_repo.py . --stats-only

# 查看帮助
python analyze_repo.py --help
```

## 支持的文件类型

- C 文件: `.c`, `.h`
- C++ 文件: `.cpp`, `.cxx`, `.cc`, `.hpp`, `.hxx`, `.hh`

## 输出信息

分析结果包含：

1. **文件统计**: 找到的文件数量和类型
2. **函数列表**: 所有找到的函数定义和声明
3. **重复函数**: 检测到的重复函数定义
4. **处理统计**: 分析耗时和成功率

## 应用场景

- **代码审查**: 快速了解项目中的函数结构
- **重构分析**: 发现重复的函数定义
- **依赖分析**: 为后续的依赖关系分析提供基础数据
- **文档生成**: 自动生成函数清单和接口文档
- **代码质量检查**: 检测代码中的潜在问题

## 与 Slicer 的集成

这个 parser 模块专门设计为 Slicer 项目的基础组件，可以：

1. 为程序切片提供函数列表
2. 支持跨文件的函数调用分析
3. 提供函数签名信息用于精确匹配
4. 检测函数重载和重复定义

## 性能特点

- **快速解析**: 基于 tree-sitter 的高效解析器
- **内存优化**: 流式处理大型项目
- **错误恢复**: 跳过有问题的文件继续分析
- **并发支持**: 支持并行处理多个文件（未来版本）

## 扩展性

模块设计支持：

- 添加新的编程语言支持
- 自定义函数过滤规则
- 插件式的分析功能
- 不同格式的报告输出 