# Scientific Research Workbench

[English](README.md)

[![CI](https://github.com/RunminYao/scientific-research-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RunminYao/scientific-research-workbench/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**面向长周期科研的证据约束型 Codex 工作流。**

Scientific Research Workbench 是面向 Codex 的科研工作流插件，用于在整个研究项目中保持科学问题、假设、证据、推导、计算、引文与 LaTeX 手稿相互一致。

```text
科学问题
    -> 项目定向
    -> 证据校准
    -> 文献 / 推导 / 计算
    -> 独立验证
    -> 引文与手稿一致性
```

## 解决的问题

- 防止长周期 agent-assisted 工作逐渐偏离原始科学目标；
- 区分物理结论、数学定理和实现检查，避免证据等级混淆；
- 在推导与代码、结果与手稿的不一致演变为结论前发现问题；
- 显式报告不支持的语法、不完整证据和 provenance 缺口，而不是靠猜测补全。

> [!IMPORTANT]
> 本项目是保守的文本与结构审计工具，**不是 LaTeX AST**、完整 TeX 宏展开器或 TeX 编译器。遇到不支持的结构时工具会报告诊断；编译结论仍以 TeX 引擎为准。

## 环境与支持范围

- Python 3.11、3.12 或 3.13；
- Codex CLI 0.144.6 或更新版本；
- 按 `requirements.txt` 的兼容范围安装运行依赖；CI 使用 `requirements-ci.txt` 中的精确版本；
- CI 覆盖 Ubuntu 与 macOS；当前不承诺 Windows；
- 仅承诺 Codex CLI 和 latest stable ChatGPT desktop/Codex 表面。官方目前不支持 IDE extension 插件，参见[官方插件文档](https://developers.openai.com/codex/plugins)。

## 安装

安装带版本 tag 的发布 marketplace 与插件：

```bash
codex plugin marketplace add RunminYao/scientific-research-workbench --ref v0.5.0
codex plugin add scientific-research-workbench@scientific-research-workbench
```

本地开发安装：

```bash
git clone https://github.com/RunminYao/scientific-research-workbench.git
cd scientific-research-workbench
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
codex plugin marketplace add "$PWD"
codex plugin add scientific-research-workbench@scientific-research-workbench
python scripts/self_check.py
```

## 一分钟 quick start

```bash
cd examples/minimal
latexmk -pdf main.tex
codex '使用 $edit-scientific-manuscripts 保守审阅 main.tex；报告不支持语法，不要虚构科学结论。'
```

最小项目见 [`examples/minimal`](examples/minimal)。完整 derive → compute → verify → edit 演示见 [`examples/pendulum-workflow`](examples/pendulum-workflow)。

## 定向复杂科研项目

恢复当前科学主线，同时不假设读者已经跟进每个近期推导或失败路线：

```bash
codex '使用 $orient-scientific-project 解释项目目前进展、我可能错过的重要结果以及理解它们所需的背景。'
```

同一技能也可以为 Codex 或子代理生成冷启动任务简报，检查局部工作是否仍影响项目决策，并在项目明确启用 `RESEARCH_NOTICES.md` 时综合面向人的关注记录。关注记录只用于导航，不代替科学证据；技能也不会要求正在完成紧邻判决的科研工作为了记录而暂停。

## 校准科学证据与路线选择

在选择下一项研究工作前，先区分明确假设下的物理结论、数学定理与实现检查：

```bash
codex '使用 $calibrate-scientific-evidence 分类当前主张，审计路线是否已经偏离目标可观测量，并选择最小的决策性结果。'
```

该技能将主张类型与证据状态分开，检查拟议定理是否确实控制目标可观测量，并在同一分支连续两个里程碑只产生新表示、证明、contract、verifier 或基础设施后，要求在第三步前重新比较路线。它还按决策价值与总成本对候选路线排序，默认只读，也不创建新的研究 ledger。

## 初始化或接入手稿项目

可以让 Codex 检查仓库并在写入前预览合适的脚手架：

```bash
codex '使用 $scaffold-manuscript-project 检查当前仓库，并预览初始化或接入统一科研与手稿 workspace；在我确认预览前不要写入文件。'
```

也可以直接运行 Python CLI。已有手稿使用：

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --root-tex paper/main.tex
# 审阅全部文件和命令后增加 --apply
```

空仓库必须省略 `--root-tex`，让脚手架创建分节手稿：

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --profile generic
```

生成的仓库指导会默认配置 `$orient-scientific-project`。如果要显式启用其面向人的关注日志，请增加 `--with-research-notices`；未指定该参数时，脚手架不会创建 `RESEARCH_NOTICES.md`。接入已有项目时会识别并保留已经存在的日志。

默认脚手架会一次性连接：

- 配置项目定向的冷启动指引、研究计划、有界结果索引、topic packets 与引文依据；
- 活跃 TeX include 图、参考文献资源与手稿上下文；
- 推导笔记、`calculations/{core,models,workflows,cli}` 提升路径及科学配置边界；
- 分层依赖契约、忽略跟踪的仓库本地 `env/`、生成物隔离、项目 manifest 与可执行结构验证。

新的非接入项目执行 `--apply` 时，脚手架会用运行命令的解释器离线创建 `env/`，但不会安装包或升级 pip。只有当环境由其他工具管理时才使用 `--no-bootstrap-environment`；接入模式默认保留现有环境方案，并优先沿用 manifest 已声明或唯一可识别的本地解释器。

对已有仓库使用 `--adopt`。接入模式逐字保留已有文件和 manifest，只创建缺失路径，并报告需要人工审阅的迁移缺口。旧 `--mature-research` 与 `--with-calculation-layout` 参数仍可解析，但只是兼容别名；这些组件已经属于统一默认框架。

空的 generic 项目会得到可编译的分节手稿。只有在需要显式领域约定时才选择 `--profile hep-astrophysics` 或 `--profile axion-phenomenology`。生成的路径只建立路由与证据边界，不建立项目特定科学结论；通过仓库环境运行结构验证后再依赖这些路由。

## 执行验证与安全边界

先预览将要运行的命令：

```bash
python skills/verify-manuscript-results/scripts/run_verification.py --project-root examples/pendulum-workflow
```

> [!WARNING]
> `--execute` 会执行当前仓库控制的任意程序，等同于运行仓库代码。使用前必须审阅仓库内容和命令预览。

默认环境模式只对白名单之外的继承环境变量做清理。它**不是** sandbox、容器、权限隔离或网络隔离。`--inherit-env` 暴露更多宿主环境，风险更高。timeout 会终止进程组，但自行 daemonize 或创建新会话的后代仍可能逃逸。报告中的 stdout/stderr 有大小上限，但子进程输出不承诺自动脱敏，因此 JSON/JUnit 报告可能包含敏感数据。

执行单摆示例并写出稳定 JSON/JUnit 报告：

```bash
python skills/verify-manuscript-results/scripts/run_verification.py \
  --project-root examples/pendulum-workflow --execute \
  --report verification/runner-report.json \
  --junit verification/runner-junit.xml
```

`[verification].default` 只表示默认命令集，不表示离线，也不提供网络隔离。已删除的 `[verification].offline` 会被拒绝，并给出迁移提示。

## 审计语义

写入前先预览物理、HEP 或天体物理论文的权威 INSPIRE BibTeX：

```bash
python skills/manage-manuscript-citations/scripts/fetch_inspire_bibtex.py \
  --arxiv 1207.7214 --bib paper/references.bib
# 审阅记录、key 与重复项检查后，再增加 --apply
```

引文审计使用 Pybtex，并可联合检查多个资源：

```bash
python skills/manage-manuscript-citations/scripts/audit_bibliography.py \
  --root-tex paper/main.tex --bib paper/references.bib --bib shared/library.bib --strict
```

Notation 审计分别报告 `literal` 与 `macro-generated-possibility`，并区分 `explicit-definition`、`heuristic-candidate` 和 `none`。动态 include、include 环、重复的规范化 include 路径、超过 256 个文件的 include 链、参数化宏、`\csname`、`\edef`/`\xdef`、catcode 修改等无法可靠解析的语法会使 JSON 标记为不完整，并在 `--strict` 下失败；每个规范化 TeX 文件最多扫描一次。

## Profile 与可选适配器

先预览领域 profile 和 adapter，再决定是否写入：

```bash
python skills/scaffold-manuscript-project/scripts/scaffold_project.py \
  --project-root /path/to/project \
  --profile axion-phenomenology \
  --adapter latexmk --adapter sympy
# 审阅后增加 --apply
```

可选 profile 为 `generic`、`hep-astrophysics` 和 `axion-phenomenology`。轴子 profile 用于显式记录项目采用的粒子模型、宇宙学、暗物质晕、实验装置、统计推断、相干性与近似有效域约定，不预填项目特定的数值结论。

隔离输出的 `latexmk` adapter 已属于统一默认框架；显式重复指定仍兼容。按需添加 `jupyter`、`sympy`、`mathematica` 和 `slurm`。它们只生成文件并诊断依赖，不安装软件、不提交作业；SLURM 始终要求人工提交。

## 开发与发布检查

```bash
python -m unittest discover -s tests -v
python -m compileall -q skills shared scripts tests examples
python scripts/check_templates.py
python scripts/validate_plugin.py
python scripts/self_check.py
```

版本策略和迁移说明见 [`CHANGELOG.md`](CHANGELOG.md)。主项目使用 Apache-2.0；第三方 fixture 另行保留归属与许可证说明。
