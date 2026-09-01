# TIKAZ Context On-Premise for Codex

<p align="center"><strong>本地优先的多模态上下文编译器：同时优化证据命中、保真和上下文成本。</strong></p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="docs/RESULTS.md">完整实测</a> ·
  <a href="docs/BENCHMARK.zh-CN.md">测试方法</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a>
</p>

<p align="center">
  <a href="https://github.com/TIKAZI/TIKAZ-Codex-Context-OnPremise/actions/workflows/validate.yml"><img src="https://github.com/TIKAZI/TIKAZ-Codex-Context-OnPremise/actions/workflows/validate.yml/badge.svg" alt="自动验证" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-60A5FA.svg" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-A78BFA.svg" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/inference-local--first-60A5FA.svg" alt="本地优先" />
</p>

| 20 / 20 | 89.57% | 53 / 53 | 37 / 37 |
|---:|---:|---:|---:|
| 固定全场景验收通过 | 7 个上下文样例的 Token 加权估算减少 | 声明的受保护事实完整保留 | 12 张合成图像的视觉事实命中 |

以上均为版本化固定样例结果，不是通用准确率、Provider 账单 Token 或对任意资料的节省承诺；失败项与 Pending 项同样公开。

本项目由 **TIKAZ** 主导设计、整合、独立实现和持续维护。Python 引擎与 CLI 的内部名称保留为 **Token Forge**。

## 它解决什么问题

Context On-Premise 是 TIKAZ 上下文工作流家族中由首词大写 `ON` 显式触发的重依赖路线，也是轻量 [Context Economy](https://github.com/TIKAZI/TIKAZ-Codex-Context-Economy) 的本地高保真搭档。它先把 PDF、Office、网页、图片、音视频、代码、表格等来源转换为可追溯证据，再用词法检索、BGE-M3、重排和受保护压缩生成有预算的 Context Pack。

```text
来源文件 / 网页 / 音视频 / 代码 / 长对话
  → 原件哈希与不可变来源
  → 转换、OCR、转写或结构化解析
  → canonical Markdown + 证据锚点
  → PP-OCRv5 + Qwen3-VL 视觉证据（需要时）
  → BM25 + BGE-M3 + 本地重排
  → 仅对低风险自然语言启用 LLMLingua-2
  → 有界 Context Pack + 命中账本 + 成本账本 + 遗漏/Pending
```

## 核心边界

- 代码、命令、错误、版本、URL、引用、表格、合同、财务和安全证据不会被学习式压缩改写。
- 扫描件、复杂布局或低置信视觉结果保留原件并显式回退。
- 本地模型失败时回退确定性选择，不静默输出不完整结果。
- 模型权重、真实本机配置、缓存、日志、媒体源文件和隐私资料不进入仓库。
- 检索命中、事实保真、OCR/ASR、估算 Token 和最终答案质量分别报告，不合成为一个营销总分。
- 已提交的 On-Premise v1 同清单检索结果仅作为历史数据；当前 v2 融合复跑在本机超时，因此 v2 命中与耗时明确标记为 **Pending**，不会套用旧百分比。

## 快速开始

需要 Python 3.11+。基础包本身不自动安装模型或下载大型依赖；请复制 `config.example.toml` 为 `.token-forge.local.toml`，再填写你自己的本地路径。

```powershell
python -m pip install -e .
$env:PYTHONPATH='src'
python -m token_forge doctor --config .token-forge.local.toml
python -m token_forge convert --input path\to\source.pdf --output path\to\result --config .token-forge.local.toml
python -m token_forge optimize --input path\to\canonical.md --query "需要回答的问题" --budget 2000 --output path\to\context-pack --config .token-forge.local.toml
```

依赖、文件格式、架构和完整命令见：

- [依赖与模型来源](docs/DEPENDENCIES.md)
- [文件格式矩阵](docs/FORMAT_MATRIX.md)
- [系统架构](docs/ARCHITECTURE.md)
- [完整测量结果](docs/RESULTS.md)
- [检索质量与失败样例](docs/RETRIEVAL_QUALITY.md)

## 与 Context Economy 如何配合

```text
上下文-ContextOrchestrator
├─ 上下文-ContextEconomy      默认；无依赖、轻量、安全直通
└─ 上下文-ContextOnPremise    首词 ON；本地模型、多模态、高保真
```

没有 `ON` 时默认使用 Economy。只有用户输入的首个非空控制词是大写 `ON`，或显式调用 Context On-Premise，才进入本仓库对应路线。

## 许可证与来源

TIKAZ 原创代码按 [MIT License](LICENSE) 发布。可选转换器、运行时和模型是独立第三方作品，许可证与来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；本仓库不重新分发其模型权重。
