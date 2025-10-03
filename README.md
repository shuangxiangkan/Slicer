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

使用方法, 参考test/目录下的测试脚本