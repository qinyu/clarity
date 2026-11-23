---
baseline: f6627ff
verified_at: "2025-11-23"
topic: oil-temperature-display
---

# 油温显示

## 你要找什么

| 意图 | 优先打开 |
| --- | --- |
| 硬件引脚与仿真 | [docs/hardware.md](../hardware.md)、[docs/test.md](../test.md)（GPIO 39） |
| 传感器与配置项 | `include/sensors/oil_temperature_sensor.h`、`src/sensors/oil_temperature_sensor.cpp` |
| 表盘 Presenter | `src/panels/oem_oil_panel.cpp`、`include/panels/oem_oil_panel.h` |
| 右侧油温表盘 View | `src/components/oem/oem_oil_temperature_component.cpp` |
| 共用表盘逻辑（Refresh/主题色） | `src/components/oem/oem_oil_component.cpp` |
| 单位与量程常量 | `include/definitions/constants.h`（`TEMPERATURE_MAX_CELSIUS` 等） |
| `Reading` 类型 | `include/definitions/types.h` |

练习摘要中的定位词 **OilTemperatureSensor → OemOilPanel → OemOilTemperatureComponent** 与当前仓一致。

## 数据流（已核实 @ f6627ff）

```text
GPIO 39 (OIL_TEMPERATURE)  analogRead
  → OilTemperatureSensor::ReadRawValue
  → ConvertReading（scale/offset，再按 targetUnit_ 换算）
  → GetReading() 返回 Reading（正常为 int32_t）

OemOilPanel（Presenter）
  → 构造时 make_shared<OilTemperatureSensor>(gpio)
  → Init() 里 sensor->Init()，cachedTemperatureSensor_ 用于配置查询
  → update() → UpdateOilTemperature(forceRefresh)
      → std::get<int32_t>(sensor->GetReading())
      → MapTemperatureValue（显示刻度映射 + 单位配置）
      → deadband / LVGL 动画
      → oemOilTemperatureComponent_.Refresh(Reading{value})

OemOilTemperatureComponent
  → 继承 OemOilComponent：刻度 0–120、危险区、oil_temp_regular 图标
  → Refresh：按 StyleManager 主题色刷针/图标（Night 时图标恒为 gaugeNormal 红）
```

### 配置（NVS）

节名 `oil_temperature_sensor`（显示名 **Oil Temp.**），键见 `OilTemperatureSensor::CONFIG_*`：

- `unit`（C / F）
- `update_rate`、`offset`、`scale`
- 显示侧死区：`oil_temperature_component.deadband_percent`（`OemOilPanel` 读取）

菜单入口：ConfigPanel 动态菜单 → **Oil Temp.** 节（与 [config.md](../config.md) 一致）。

## 失败与错误（已核实）

### 采集失败

`OilTemperatureSensor::GetReading()` 在 ADC 无效时：

1. `ErrorManager::ReportError(ERROR, "OilTemperatureSensor", ...)`
2. 返回 **`std::monostate{}`**（无效 Reading）

### 面板侧

`OemOilPanel::UpdateOilTemperature` 直接：

```cpp
auto sensorValue = std::get<int32_t>(oemOilTemperatureSensor_->GetReading());
```

**未**先判断 `monostate`（已核实）：`UpdateOilTemperature` 在 `GetReading()` 为无效值时仍调用 `std::get<int32_t>(...)`，源码路径上未对 `std::monostate` 分支。

**待验证（未跑仿真/实机）**：无效 ADC 读返回 `monostate` 后，表盘/UI 是否冻结、是否仅 ErrorManager 提示、或是否触发未捕获的 `std::bad_variant_access`；与旧练习「仅 ErrorManager、表盘保持」的叙述尚未用 Wokwi 或硬件对照。

传感器为空指针时：打 Critical 并 `return`（不更新 UI）。

### 组件侧

`OemOilComponent::Refresh(const Reading&)` 假定 **`int32_t`**，不做 variant 分支（已核实）。

## 与主题的关系

油温表在 **OemOilPanel** 上；主题变化时 `update()` 设 `forceRefresh`，在数值未变时仍可能 `Refresh(Reading{value})` 以重刷颜色（`oem_oil_panel.cpp`）。表盘配色逻辑见 [theme-and-config-menu.md](theme-and-config-menu.md)。

## 文档漂移提示

- `docs/standards.md` 示例中 GPIO 34 作油温引脚；**代码**为 `gpio_pins::OIL_TEMPERATURE = 39`（`include/hardware/gpio_pins.h`）。以代码与 `docs/context.md` 为准。

## 验证

- 构建：`pio run -e test-wokwi`
- 自动化主路径在 Oil Panel 上验证表盘与主题，见 `test/wokwi/scenario_automated.yaml`
- Wokwi 原理图：`test/wokwi/diagram_automated.json`（GPIO 39 油温模拟）

## 未在本页展开

- 机油**压力**左侧表盘：同文件 `OemOilPanel` / `OilPressureSensor`（对称实现）
- 传感器与压力传感器代码重复：`docs/todo.md` 已记重构意向（**未做**）