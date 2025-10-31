# Analysis Test Framework

用于测试和验证CFG/CDG/DDG/PDG构建正确性的测试框架。

## 目录结构

```
analysis_test/
├── test_programs/          # 测试用的C代码文件
│   ├── 01_simple_def_use.c
│   ├── 02_if_else.c
│   └── ...
├── expected_results/       # 基准JSON结果文件
│   ├── 01_simple_def_use.json
│   ├── 02_if_else.json
│   └── ...
├── build_baseline.py       # 构建基准脚本
├── compare_results.py      # 对比结果脚本
└── README.md              # 本文件
```

## 使用流程

### 1. 构建基准（修改前）

在修改DDG/CFG算法**之前**，先运行此脚本生成基准结果：

```bash
# 构建所有测试程序的基准
python build_baseline.py

# 只构建指定程序的基准
python build_baseline.py --program 01

# 清理已有的基准文件
python build_baseline.py --clean
```

这会在`expected_results/`目录下生成JSON文件，包含：
- CFG、CDG、DDG、PDG的节点和边信息
- 构建时间
- 元数据（代码行数、时间戳等）

### 2. 修改算法

修改`analysis/ddg.py`或`analysis/graph.py`中的算法实现。

### 3. 对比结果（修改后）

修改后，运行对比脚本验证结果是否一致：

```bash
# 对比所有测试程序
python compare_results.py

# 只对比指定程序
python compare_results.py --program 01

# 只对比DDG
python compare_results.py --graph ddg

# 显示详细差异
python compare_results.py --verbose

# 组合使用
python compare_results.py --program 01 --graph ddg --verbose
```

对比脚本会：
- ✅ 验证节点和边的数量是否相同
- ✅ 验证每条边的source、target、variables是否一致
- ✅ 验证节点的defs/uses是否一致
- 📊 显示性能对比（加速倍数）

### 4. 添加新测试用例

在`test_programs/`目录下创建新的`.c`文件：

```bash
# 文件命名格式：编号_描述.c
# 例如：
echo 'int test(int x) { return x + 1; }' > test_programs/11_new_test.c

# 构建新测试的基准
python build_baseline.py --program 11
```

## JSON格式说明

每个基准文件包含以下结构：

```json
{
  "program_name": "01_simple_def_use",
  "program_file": "01_simple_def_use.c",
  "code_lines": 5,
  "code": "int simple_def_use(int x) { ... }",
  "timestamp": "2025-10-31 20:00:00",
  "graphs": {
    "cfg": {
      "graph": {
        "graph_type": "CFG",
        "nodes": [
          {
            "id": 1,
            "type": "function_definition",
            "text": "int simple_def_use(int x)",
            "line": 1,
            "defs": [],
            "uses": []
          }
        ],
        "edges": [
          {
            "source_id": 1,
            "target_id": 2,
            "label": "",
            "type": "CFG"
          }
        ],
        "node_count": 5,
        "edge_count": 4
      },
      "time": 0.0123,
      "success": true
    },
    "ddg": { ... },
    "cdg": { ... },
    "pdg": { ... }
  }
}
```

## 测试用例说明

| 编号 | 文件名 | 测试目标 |
|------|--------|----------|
| 01 | simple_def_use.c | 简单的定义-使用链 |
| 02 | if_else.c | if-else分支 |
| 03 | while_loop.c | while循环 |
| 04 | for_loop.c | for循环 |
| 05 | nested_if.c | 嵌套if |
| 06 | switch_case.c | switch-case |
| 07 | multiple_paths.c | 多路径 |
| 08 | complex_function.c | 复杂函数（嵌套循环+分支） |
| 09 | large_switch.c | 大量分支（性能测试） |
| 10 | reassignment.c | 变量重赋值 |

## 典型工作流程

### 场景1：优化DDG构建算法

```bash
# 1. 修改前构建基准
python build_baseline.py

# 2. 修改 analysis/ddg.py 或 analysis/graph.py

# 3. 验证结果一致性
python compare_results.py --graph ddg

# 4. 如果有差异，查看详细信息
python compare_results.py --graph ddg --verbose

# 5. 如果某个测试失败，单独调试
python compare_results.py --program 09 --graph ddg --verbose
```

### 场景2：添加新的测试用例

```bash
# 1. 创建新测试文件
vim test_programs/11_my_test.c

# 2. 构建基准
python build_baseline.py --program 11

# 3. 验证
python compare_results.py --program 11
```

### 场景3：重新生成所有基准

```bash
# 清理旧基准
python build_baseline.py --clean

# 重新构建
python build_baseline.py
```

## 注意事项

1. **基准文件很重要** - 不要随意删除`expected_results/`目录
2. **修改前先构建基准** - 确保有正确的对照
3. **定期验证** - 每次修改算法后都应运行对比
4. **性能回归** - 对比脚本会显示性能变化，关注是否有性能下降
5. **版本控制** - 建议将`expected_results/`目录纳入git版本控制

## 扩展

可以添加更多复杂的测试用例来覆盖边界情况：
- 递归函数
- 函数指针
- goto语句
- 复杂的控制流
- 大型函数（100+行）

