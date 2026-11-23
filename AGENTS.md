# Agent 指引（Clarity）

## 项目

**Clarity**：ESP32 上的车载表盘式显示管理器（MVP + LVGL，`platformio.ini` 中 `esp32_base` / `nodemcu-32s`）。细则见 `docs/`、`README.md`。

## 集成验证构建

在项目根目录：

```bash
pio run -e test-wokwi
```

产出：`.pio/build/test-wokwi/firmware.bin` 与 `firmware.elf`。该环境开启 `WOKWI_EMULATOR`、`TEST_LOGS`，`CORE_DEBUG_LEVEL=0`（见 `platformio.ini` 的 `[env:test-wokwi]`）。

## Wokwi 验证入口（`test/wokwi/`）

| 路径 | 用途 |
| --- | --- |
| `wokwi_test_automation.sh` | **主入口**：检查固件与 `wokwi-cli`，以 `diagram_automated.json` + `scenario_automated.yaml` 跑全自动场景 |
| `wokwi_automated.toml` | 自动化配置，固件路径指向 `../../.pio/build/test-wokwi/` |
| `wokwi.toml` | 手动/交互仿真基线配置 |
| `diagram_automated.json` / `scenario_automated.yaml` | 自动化连线图与场景 |

典型流程：

```bash
pio run -e test-wokwi
./test/wokwi/wokwi_test_automation.sh
```

需已安装 [wokwi-cli](https://github.com/wokwi/wokwi-cli)。更多说明见 `docs/test.md`。

## 主机单测（`test/host/`）

本机 **C++17 系统编译器** 入口，不依赖 PlatformIO `native` 平台、不拉 Unity/LVGL，**不修改** 根目录 `platformio.ini`。

| 路径 | 用途 |
| --- | --- |
| `test/host/run_host_tests.sh` | **主入口**：选 `CXX` 或 `clang++`/`g++`，编译并执行各套件；编译或运行失败则非零退出 |
| `test/host/smoke/` | 工具链冒烟（当前唯一套件） |
| `test/host/cases/` | 开发阶段业务用例目录（主题菜单、油温无效读等；本轮未添加） |

典型流程：

```bash
./test/host/run_host_tests.sh
```

可选：`CXX=clang++ ./test/host/run_host_tests.sh`。产物在 `test/host/.build/`（本地生成，勿提交）。

## 固件构建预检（LVGL 版本）

基线预检中，根 `platformio.ini` 的 `lvgl/lvgl @ ^9.2.0` 解析为 **9.6.0**。编译在 `include/managers/style_manager.h` 的 `LV_PART_* | LV_STATE_*` 组合处报 `lv_part_t` 转换错误。

验收时从本次待验提交复制 `platformio.ini` 到一个独立产物目录，把副本的 LVGL 依赖固定为 `lvgl/lvgl @ 9.2.2`。从仓库根运行以下命令，`out` 指向该产物目录。

```bash
PLATFORMIO_BUILD_DIR="$out/build" PLATFORMIO_LIBDEPS_DIR="$out/libdeps" \
  pio run -d "$PWD" -c "$out/platformio.ini" -e test-wokwi
```

记录待验提交和 `"$out/build/test-wokwi/firmware.bin"` 的 SHA-256。模拟验收使用该 BIN。

## Spec 工作流

`.workflow/` 为 workflow-lite **Alpha 2 默认模板**（四阶段稿 + `resolved.yaml`）。推进单份 spec 时读 `resolved.yaml` 与对应阶段 `*.md`。

## 项目知识（Wiki）

- 理解架构、模块边界或专题实现时，优先读 `docs/wiki/index.md` 与 `docs/context.md`；维护知识库时使用 `wiki` 技能。
- 已落地改动影响模块接口或术语时，按证据增量更新 `docs/wiki/`（不把未实现计划写成现状）。

## CodeGraph（符号与调用关系）

- 查符号、调用关系或改动影响时，优先用本项目 MCP `clarity-codegraph`，再按需核对源码。MCP 不可用时，从仓库根用 `DO_NOT_TRACK=1 codegraph query <符号>`。
- 索引缺失时运行项目 Setup 扩展。手动刷新已有索引用 `DO_NOT_TRACK=1 codegraph sync`。索引位于被 Git 忽略的 `.codegraph/`。
- 项目 MCP 配置更新后，重开 Cursor 会话并检查工具是否可调用。
