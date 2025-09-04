# OGHarn 三步筛选流程演示

这个演示项目模拟了 OGHarn 的核心 Oracle 引导机制，展示了如何通过三个步骤筛选和选择最佳的模糊测试 Harness。

## 项目结构

```
harness_filter_demo/
├── README.md                    # 本文件
├── run_ogharn_demo.py          # 主控脚本
├── step1_compile_filter.py     # 第一步：编译筛选
├── step2_execution_filter.py   # 第二步：执行筛选
├── step3_coverage_filter.py    # 第三步：代码覆盖率筛选
├── harness_samples/            # 示例 Harness 文件
│   ├── harness1_good.c         # 好的 harness（能通过所有筛选）
│   ├── harness2_compile_fail.c # 编译失败的 harness
│   ├── harness3_crash.c        # 可能崩溃的 harness
│   ├── harness4_no_input_dependency.c  # 无输入依赖性的 harness
│   └── harness5_linear_coverage.c      # 线性覆盖率增长的 harness
├── seeds_validcp/              # 有效种子文件
│   ├── test_json.txt
│   ├── test_xml.txt
│   ├── data_sample.txt
│   └── short.txt
├── seeds_invalidcp/            # 无效种子文件
│   ├── crash_trigger.txt
│   └── overflow_trigger.txt
├── output/                     # 编译输出目录
└── logs/                       # 日志和统计文件
```

## OGHarn 三步筛选流程

### 第一步：编译筛选 (`step1_compile_filter.py`)

**目标**: 过滤掉无法编译的 Harness

**实现**:
- 使用 GCC 编译每个 C 文件
- 添加代码覆盖率支持的编译选项
- 记录编译成功和失败的统计信息
- 输出编译成功的 Harness 列表

**对应 OGHarn 源码**: `engine.py` 中的 `CompileHarness.checkSequence` 方法

### 第二步：执行筛选 (`step2_execution_filter.py`)

**目标**: 过滤掉执行时崩溃或异常的 Harness

**实现**:
- 使用有效和无效种子文件测试每个 Harness
- 检测崩溃、超时和执行异常
- 验证 Harness 能够区分有效和无效输入
- 支持 AFL++ 的 `showmap` 工具（如果可用）

**对应 OGHarn 源码**: `engine.py` 中的 `CompileHarness.compileHarness` 方法的执行部分

### 第三步：代码覆盖率筛选 (`step3_coverage_filter.py`)

**目标**: 使用 Oracle 引导机制选择最佳 Harness

**实现**:
- 分析每个 Harness 的代码覆盖率
- 检查输入依赖性（不同输入产生不同覆盖率）
- 检测线性覆盖率增长问题
- 计算相对于全局覆盖率的增益
- 使用贪心策略选择最佳 Harness

**对应 OGHarn 源码**: 
- `engine.py` 中的 `getBitmap` 方法
- `ogharn.py` 中的 `analyzeHarness` 和 `getBestHarnesses` 方法

## Oracle 引导机制核心特性

1. **代码覆盖率反馈**: 使用 AFL++ 或 gcov 获取覆盖率位图
2. **增量覆盖率计算**: 只选择能带来新覆盖率的 Harness
3. **质量过滤**: 过滤无输入依赖性和线性覆盖率增长的 Harness
4. **贪心优化**: 按覆盖率增益排序，优先选择高价值 Harness
5. **全局覆盖率维护**: 持续更新全局覆盖率位图

## 使用方法

### 前置要求

- Python 3.6+
- GCC 编译器
- AFL++ (可选，用于更精确的覆盖率分析)

### 运行演示

1. 进入演示目录:
```bash
cd /home/kansx/SVF-Tools/Slicer/tools/driver/harness_filter_demo
```

2. 运行完整演示:
```bash
python run_ogharn_demo.py
```

3. 或者分步执行:
```bash
# 第一步：编译筛选
python step1_compile_filter.py harness_samples output logs

# 第二步：执行筛选
python step2_execution_filter.py logs seeds_validcp seeds_invalidcp

# 第三步：代码覆盖率筛选
python step3_coverage_filter.py logs seeds_validcp
```

### 查看结果

演示完成后，查看 `logs/` 目录中的结果文件:

- `step1_compile_stats.json`: 编译统计信息
- `step2_execution_stats.json`: 执行统计信息
- `step3_coverage_stats.json`: 覆盖率统计信息
- `step3_best_harnesses.json`: 最终选择的最佳 Harness
- `global_coverage_bitmap.json`: 全局覆盖率位图

## 示例 Harness 说明

1. **harness1_good.c**: 设计良好的 Harness
   - 能正常编译和执行
   - 有明确的输入依赖性
   - 根据输入内容执行不同代码路径

2. **harness2_compile_fail.c**: 编译失败示例
   - 语法错误和未定义函数
   - 会在第一步被过滤掉

3. **harness3_crash.c**: 崩溃示例
   - 包含缓冲区溢出和空指针解引用
   - 会在第二步被过滤掉

4. **harness4_no_input_dependency.c**: 无输入依赖性
   - 不管输入什么都执行相同代码
   - 会在第三步被过滤掉

5. **harness5_linear_coverage.c**: 线性覆盖率增长
   - 覆盖率与输入大小成正比
   - 会在第三步被过滤掉

## 技术细节

### 覆盖率获取方法

1. **AFL++ showmap** (首选):
   - 使用 `afl-showmap` 获取精确的边覆盖率
   - 输出格式: `edge_id:hit_count`

2. **模拟覆盖率** (备选):
   - 基于程序输出和输入内容生成伪覆盖率
   - 用于没有 AFL++ 的环境

### 质量评估标准

- **good**: 有新覆盖率增益且有输入依赖性
- **no_new_coverage**: 没有新的覆盖率增益
- **no_input_dependency**: 缺乏输入依赖性
- **linear_coverage**: 线性覆盖率增长

### 贪心选择策略

1. 按覆盖率增益降序排序
2. 依次选择能提供新覆盖率的 Harness
3. 更新全局覆盖率位图
4. 限制最终选择的 Harness 数量

## 与 OGHarn 源码的对应关系

| 演示文件 | OGHarn 源码 | 功能 |
|---------|-------------|------|
| `step1_compile_filter.py` | `engine.py:CompileHarness.checkSequence` | 编译 Harness |
| `step2_execution_filter.py` | `engine.py:CompileHarness.compileHarness` | 执行测试 |
| `step3_coverage_filter.py` | `engine.py:getBitmap`, `ogharn.py:analyzeHarness` | 覆盖率分析 |
| `run_ogharn_demo.py` | `ogharn.py:begin_harnessing` | 主控流程 |

这个演示项目完整展示了 OGHarn 的 Oracle 引导机制如何通过代码覆盖率反馈来智能筛选和选择最佳的模糊测试 Harness。