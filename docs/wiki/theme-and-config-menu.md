---
baseline: "3336c93"
verified_at: "2026-11-26"
topic: theme-and-config-menu
---

# 主题与配置菜单

## 你要找什么

| 意图 | 优先打开 |
| --- | --- |
| 菜单结构与 Display / Theme 选项 | [docs/config.md](../config.md)（Configuration Menu Tree） |
| 菜单 UI 与按键 | `src/panels/config_panel.cpp`、`src/components/config_component.cpp` |
| 主题令牌与 LVGL 样式 | `src/managers/style_manager.cpp`、`include/definitions/styles.h` |
| 车灯自动日夜切换 | `include/definitions/interrupts.h`（`TriggerType::STYLE`） |
| 从表盘进配置 | `src/panels/oem_oil_panel.cpp`（`HandleLongPress`）、`src/panels/lock_panel.cpp` |
| 主题菜单与车灯验收 | [主题菜单场景入口](../../test/wokwi/theme_menu_focus/run.sh) |

## 当前实现（已核实 @ 3336c93）

### 1. 配置菜单不是写死的「Theme Settings」

主菜单由 **ConfigurationManager 已注册节** 动态生成（`ConfigPanel::BuildDynamicMenus`），按 **显示名拼音/字母序** 排列。与代码一致的树见 [config.md](../config.md)：

- **Display**（内部节名 `style_manager`）：`Theme`（Day / Night）、`Brightness`
- 另有 Oil Pressure Sensor、Oil Temperature Sensor、Splash Screen、System、**Exit**

**漂移（已核实）**：`docs/scenarios.md` §15 仍写「Default Panel, Theme Settings, Exit」；`docs/restructure.md` 已记录应与 `config.md` 对齐。Wokwi 串口期望 `[T] ConfigPanel: Entering theme submenu` 等文案，**当前 `config_panel.cpp` 无对应 `log_t`**，测试日志可能来自旧构建或仅场景注释。

### 2. 用户路径：进菜单 → 改主题

```text
长按 GPIO32（ActionHandler LONG_PRESS）
  → Panel 的 HandleLongPress（如 OemOilPanel / LockPanel）
  → PanelManager 加载 ConfigPanel

ConfigPanel 主菜单：
  短按 → 循环 currentMenuIndex_（ConfigComponent 高亮）
  长按 → ExecuteMenuAction

进入 Display：
  action ENTER_SECTION → style_manager → BuildSectionMenu

改 Theme：
  节内项 action SHOW_OPTIONS → ShowOptionsMenu（key style_manager.theme）
  按配置值标记 Day 或 Night，并将匹配索引同时交给面板和组件
  选项 Day/Night → SET_CONFIG_VALUE → ConfigurationManager::UpdateConfig
  → 若 key 为 style_manager.theme → configComponent_.UpdateThemeColors()
```

NVS 键：`style_manager.theme`（`ConfigConstants::Keys::STYLE_MANAGER_THEME`）。Schema 在 `StyleManager::RegisterConfigSchema`（`src/managers/style_manager.cpp`）。

`ConfigPanel` 经 `IConfigurationManager::GetConfigSection()` 读取偏好，在生成枚举选项时记录第一个匹配项。该索引同时决定 `SetCurrentIndex()` 的渲染焦点及长按确认项。缺省 Day 同时获得高亮和 `>`。遇到 `Legacy` 等旧值时，Day 获得初始焦点，两个选项的 `>` 都为空，原值保留到显式保存。Brightness 继续从 0 高亮，并标记实际保存的亮度。

### 3. 运行时主题：车灯触发（不进菜单）

- **GPIO 33**：Lights 传感器（`docs/context.md`）
- `interrupts.h` 中 Lights 触发类型 **`STYLE`**，优先级 NORMAL
  - 激活：`StyleManager::Instance().SetTheme(Themes::NIGHT)`
  - 停用：`SetTheme(Themes::DAY)`
- **不调用** `UpdateConfig`（已核实）

### 4. 主题接缝：偏好 vs `SetTheme`（改代码时常踩）

| 机制 | 行为 |
| --- | --- |
| `GetCurrentTheme()` | 有 `ConfigurationManager` 时读取本机偏好 `style_manager.theme` |
| `SetTheme(theme)` | 应用共享 LVGL 样式并刷新当前屏 |
| 车灯 `SetTheme` | 即时改外观；偏好仍可能是用户曾在菜单选的 Day/Night |
| `OemOilPanel::update` | 用 `GetCurrentTheme()` 与 `lastTheme_` 比较决定是否 `ApplyThemeToScreen` |

车灯触发时即时切换仪表配色。Theme 菜单从已保存偏好定位，高亮浏览保留原有标记。已保存 Day 时开灯，仪表进入 Night，Theme 仍高亮 `> Day`。已保存 Night 时关灯，仪表回到 Day，Theme 仍高亮 `> Night`。

### 5. 面板如何吃到主题

- 各 Panel `Load` / `update` 调用 `styleManager_->ApplyThemeToScreen(screen_)`
- **OemOilPanel**：`update()` 检测主题变化后对压力/温度表 `Refresh(..., forceRefresh)`（`src/panels/oem_oil_panel.cpp`）
- **ConfigPanel**：Night 时对容器额外设深红背景（非纯黑）
- **ErrorPanel**：加载时用 `Themes::ERROR` 覆盖

### 6. 验证

```bash
pio run -e test-wokwi
./test/wokwi/wokwi_test_automation.sh
```

场景中与主题相关步骤见 `scenario_automated.yaml`（Lights 切换、Config 内选 Night 等）。
主题焦点的专用入口接受 `--case` 和浏览器采集。A5、A6 分别核对灯光边沿、仪表颜色、打开 Theme 的高亮，以及末帧后至少 500 ms 内的写入和配色记录。 [主题菜单检查入口](../../test/wokwi/theme_menu_focus/run.sh)

## 关键符号速查

| 符号 / 常量 | 位置 |
| --- | --- |
| `Themes::DAY` / `NIGHT` / `ERROR` | `include/definitions/styles.h` |
| `StyleManager` | `include/managers/style_manager.h` |
| `IStyleManager` | `include/interfaces/i_style_manager.h` |
| `ConfigPanel` | `include/panels/config_panel.h` |

## 未在本页展开

- ERROR 主题与 ErrorPanel 恢复链：见 [docs/error.md](../error.md)
- StyleManager brightness 项：已注册，表盘侧消费路径未在本专题逐项追踪（**未确认**是否全链路生效）
