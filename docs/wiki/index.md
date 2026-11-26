---
baseline: f6627ff
verified_at: "2025-11-23"
---

# Clarity 项目知识库（L0）

面向 **Clarity**（ESP32 圆屏表盘，`demo/theme-menu-focus` 分支）的 AI 可读知识层。事实以仓库源码与 `docs/` 为准；本目录只整理**从哪里找**与**当前实现核对结果**，不替代原文档。

## 权威文档（先读这些）

| 文档 | 用途 |
| --- | --- |
| [README.md](../../README.md) | 构建命令、文档总索引 |
| [docs/context.md](../context.md) | 架构术语、GPIO、面板与中断概览 |
| [docs/architecture.md](../architecture.md) | MVP 与工厂装配 |
| [docs/config.md](../config.md) | 动态配置与 **ConfigPanel 菜单树（与代码一致）** |
| [docs/interrupts.md](../interrupts.md) | Trigger / Action 与优先级 |
| [docs/scenarios.md](../scenarios.md) | Wokwi 集成场景（部分菜单文案已与代码漂移，见专题页） |
| [docs/test.md](../test.md) | `test-wokwi` 与 `test/wokwi/` 自动化 |
| [AGENTS.md](../../AGENTS.md) | Agent 构建与验证入口 |

## 专题索引（本轮）

| 专题 | 文件 | 一句话 |
| --- | --- | --- |
| 主题与配置菜单 | [theme-and-config-menu.md](theme-and-config-menu.md) | Day/Night、车灯 GPIO 触发、Display 配置节与 ConfigPanel 导航 |
| 油温显示 | [oil-temperature-display.md](oil-temperature-display.md) | ADC → `OilTemperatureSensor` → `OemOilPanel` → 右侧表盘 |

## 后续工作线索

分支名 **theme-menu-focus**：专题页标出主题菜单焦点与「偏好里保存的主题 vs 运行时 `SetTheme`」等接缝，便于改需求时对照源码。

## 练习摘要来源

「日夜外观」和「机油工况」用于组织两个专题。各专题页记录对应的源码版本和核对日期。
