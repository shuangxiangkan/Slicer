基于 tree-sitter 的 C/C++ 分析。

## 安装依赖

首先创建并激活虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate  
```

安装依赖包：

```bash
pip install -r requirements.txt
```

## 使用方法

### 入口文件

主要入口文件是 `parser/repo_analyzer.py`，提供了 `RepoAnalyzer` 类来进行C/C++代码分析。

### 支持的分析模式

1. **单文件分析** - 直接传入C/C++文件路径
2. **配置文件分析** - 通过JSON配置文件指定分析目标
3. **直接参数分析** - 通过参数直接指定要分析的文件和目录

### 基本用法示例

```python
from parser.repo_analyzer import RepoAnalyzer

# 1. 单文件分析
analyzer = RepoAnalyzer("example.c")
result = analyzer.analyze()

# 2. 配置文件分析
analyzer = RepoAnalyzer("config.json")
result = analyzer.analyze()

# 3. 直接参数分析
analyzer = RepoAnalyzer(
    library_path="/path/to/library",
    include_files=["src/", "include/"],
    exclude_files=["test/", "examples/"]
)
result = analyzer.analyze()
```

### 详细用法和示例

更多详细的使用方法和示例代码，请参考 `test/` 目录下的测试脚本：

- `test_single_file.py` - 单文件分析示例
- `test_all_functions.py` - 函数提取和分析
- `test_api_extraction.py` - API函数提取
- `test_cfg_cdg_ddg_pdg.py` - 程序依赖图分析
- `test_call_graph_generation.py` - 调用图生成
- `test_type_analysis.py` - 类型分析
- 等等...