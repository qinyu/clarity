# 主题菜单焦点 · Develop 执行记录

获批工作基线 `e3ea788eefe9b18e992658b249819c3ad992f93f`，原特性分支 `codex/theme-menu-focus`。PR 候选在独立工作树的 `codex/theme-menu-focus-pr` 上同步了远端 `main`。同版 A1–A3、A5–A8 共 7 项已在 Wokwi 通过，A4 仍缺同实例重启证据。 [Design 确认回执](theme-menu-focus-design-approval.md) · [任务清单](theme-menu-focus-tasks.md)

- [x] **T1 已完成。** 本地提交 `8632b074fa6bcdafac715f529965040d9310361e`。网页端完成 15 次按键派发、Day 写入、菜单刷新、GPIO33 开关与 Day／Night 配色。三张 LCD PNG 可判读，采集回执校验退出 0。
- [x] **T2 已完成。** 本地提交 `ae46078a70583a40cdbca3a8817cd3d24f4ebf2a`。A1 基线保存 Night 后重开，Night 带 `>`，Day 居中。直接长按写回 Day，检查按预期退出 1。候选 A1、A2、A3、A7 比对实际加载镜像与串口、逐帧判读通过。写入断言按每次长按的开始和结束限定归属，独立复审确认 A1 重开误写会失败。
- [x] **T3 已完成。** PR 分支本地提交 `3336c93`。A5、A6 的真实 GPIO33 正向事件、LCD 帧和 Theme 操作窗口均核对通过。A5 末帧后继续观察 633 ms，A6 继续观察 600 ms，两个窗口内主题写入、菜单配色刷新、共享配色应用均为零。
- [ ] **T4 同实例重启受阻。** 双向实跑均成功写入并立即刷新 Display 的标题与提示配色，确认窗口内的共享配色事件与 T1 一致。按下再释放 EN 无第二次 ROM 启动，工具栏按钮会启动网页示例固件。本机 `pio device list` 未检测到 ESP32 串口台架。已请求复位路径决策。
- [x] **T5 已完成。** PR 分支本地提交 `ed76e0b`。两次进入 Theme 均高亮 Day，两个主题均无 `>`，Display 两次读出 `Legacy`。第 12 次 GPIO32 动作才成功写入 Night，Display 与再次打开 Theme 均显示 Night，Theme 聚焦 `> Night`。复核命令通过，人工判读六张 LCD 帧。采集位于 `.pio/theme-menu-pr-paired/browser-captures/A8/`。

## T1 已执行

| 检查 | 结果与依据 |
| --- | --- |
| `./test/host/run_host_tests.sh` | 退出 0。1 个 C++17 冒烟套件。 |
| 固定 LVGL 9.2.2 的 `pio run -e test-wokwi` | 退出 0。构建配置和产物在 `.pio/theme-menu-focus-t1.53hpkacc/`，最后一次日志为 `build-final.log`。 |
| `run.sh --case probe --prepare-only` | 退出 0。4 MiB 全闪存镜像的应用段与候选应用 BIN 一致，验证了在 `0x9000` 处的 12 KiB 空 NVS。保存有各项 SHA-256。 |
| Bash、YAML、测试脚本与差异检查 | `bash -n`、69 步场景 YAML 解析、`git diff --check`、`wokwi-cli lint --offline` 通过。静态接线检查有既有板型提示。证据校验器的合成输入试验拒绝镜像指纹不匹配、采集文件被替换、写入事件错配、缺少车灯转换和截断 PNG。合成输入仅覆盖校验器。 |
| 独立源码审查 | 已按发现修正 C++ 局部变量命名、加入独立用例发现、绑定镜像及采集文件 SHA-256，并检查 PNG 的首块、尺寸和末块。实际画面仍逐帧判读。 |

最新应用 BIN SHA-256 为 `3a9a35b111a75892788bc23719c43c0f1f72ba786095b208b612f0247fc25d93`，完整闪存镜像 SHA-256 为 `64af2aa61fb44032f828d91cb42757e994c0809958479c328c875744b8b60291`。产物与 T1 本地提交的固件源码一致。网页端实际采集见 `.pio/theme-menu-focus-t1.53hpkacc/wokwi-web/probe-wd88g8dz/`，其中 `capture.json` 绑定了加载镜像、串口和三张画面。

## T2 实跑与目标同步

- 基线失败证据在 `.pio/theme-menu-focus-t1.53hpkacc/wokwi-web/A1-red/`，包括实际写回 Day 的 `serial.log`、`result.json` 和两张 LCD 帧。候选应用 BIN 为 `afd219b85495c89228ba140f69753d3af9d1af561c3d65a5d269898af8d5eba9`。候选采集位于 `.pio/theme-menu-profiles-t2/browser-captures/`，逐例用指定 BIN 核验镜像与动作。A1 两次打开均聚焦 `> Night`，直接确认的长按写 Night。A2 两种起点均聚焦 `> Day`。A3 保留 Day 标记并按 Night、Back、Day 循环，经 Back 返回设置主菜单后仍聚焦 Day。A7 首项为 0，滑到 50 后可见持久化标记 `>`。
- 远端 `main` 的 `2e0c9ab` 已包含较早的主题焦点实现。独立工作树的同步提交 `711f13d` 经复审保留方案 A，去掉仅供旧实现使用的 helper 和其主机测试，保留上游油温套件。本轮规格材料在 PR 分支放入 `docs/theme-menu-focus-2026-11-26/`，使 11 月 23 日的历史材料仍可按原路径读取，并保留本轮获批文件的字节摘要。本次同步后的 C++17 冒烟和油温套件通过。双档探针校验通过，网页候选应用 BIN 为 `eb9921aca228c9add1cc99a8adea6b69336b71d9e364c775fc908074721170e3`。A1–A8 的准备回执与证据位于 `.pio/theme-menu-pr-paired/`，基线红测继续引用 T1 产物。

## 本地模拟

已检查 OrbStack、启动后的 Docker Desktop 以及正在运行的 Podman 环境。在可访问的引擎里未找到 Wokwi／Velxio 容器，也未找到历史记录中的 Velxio 固定摘要镜像。现有 Wokwi 浏览器页可运行公开示例。在页面离线、阻断 HTTP(S) 与 WebSocket 后加载本机电路和本机 T1 固件，仍未观测到 T1 的仪表初始化和探针事件。预加载同型 ESP32 与 ILI9341 后复试，模拟时间停在 0；输出位于 `.pio/theme-menu-focus-t1.53hpkacc/browser-warmed/probe-oavuhxag/`。运行采集校验返回 1，缺实际运行的 `capture.json`。当前本机 Wokwi CLI 环境也缺 `WOKWI_CLI_TOKEN`。

## Wokwi 路线复核

以前的 Clarity B 录屏索引记录的是官方 Wokwi 网页加载本机合并固件 `b-588dc1a8-merged.bin`。Wokwi 也公开了用于本地 CI 仿真的 Docker 镜像 `wokwi/wokwi-ci-server` 及 `WOKWI_CLI_SERVER` 连接方式。本机已重新检查可访问的 Docker 和 Podman 镜像及容器，未发现这套服务，默认端口 3000 无监听。对临时回环地址试跑已安装的 `wokwi-cli 0.29.1`，缺 `WOKWI_CLI_TOKEN` 时退出 1，未建立 WebSocket 连接。这些结果记录了网页实跑之前的环境。随后按用户授权复用联网 Wokwi 网页完成 T1。 [Wokwi CI 容器说明](https://github.com/wokwi/wokwi-ci-server-action#usage-as-a-service-container)

## 架构 lint

规则与适用范围经本轮用户确认，仅检查 ConfigPanel、ConfigComponent 的头文件和实现。持久化检查识别直接字面头文件依赖，视图检查识别指定配置接口及主题键。采用项目原有的配置接口和渲染入口为正例。未设置冻结基线。

- `python3 test/architecture/check_config_menu.py` 在四个文件上退出 0，`python3 -B test/architecture/test_check_config_menu.py -v` 的 6 条隔离用例通过，包含越界、注释、普通及原始字符串、宏与二进制反例。源码快检已接入 Wokwi 运行入口，重新执行 T1 采集校验也通过。对应本地提交 `890daa7cd6a128fa7da4de0ceb9fef33a6481aa1`。
- `.pio/theme-menu-lint.kluzmj3k/` 保存实际展开后的 PlatformIO 编译数据库。四个探针翻译单元的 test-wokwi 命令定义 `WOKWI_EMULATOR` 和 `TEST_LOGS`，release 命令均未定义。原 release 构建使用项目参数并外置固定 LVGL 9.2.2，在 `HardwareSerial.cpp:60` 因 `Serial` 未声明退出 1。日志为 `release-build.log`。
- 按本轮用户授权移除仓库 `[env:release]` 的 `ARDUINO_USB_MODE=1` 和 `ARDUINO_USB_CDC_ON_BOOT=1`。本地提交 `84006ad` 的精确暂存快照完成 `test-wokwi` 和 `release` 两档固件构建。构建沿用 AGENTS.md 的外置 LVGL 9.2.2 预检。四个探针翻译单元的实际宏和两个 BIN 的四类探针标记均符合预期。双档证据在 `.pio/probe-release-staged.LPRncUBj/evidence/`，构建日志为同目录上级的 `build.log`。
- `--case all` 已启用探针隔离门禁，需要 `--build-evidence`。构建助手 `python3 -B test/architecture/build_probe_profiles.py <新目录>` 生成两个 BIN、两份编译数据库及一份配对摘要。门禁核对待验 BIN 和四项摘要后才发现验收用例。7 条隔离用例通过。独立复审确认分别换入旧 release BIN 或旧 release 编译数据库时均在发现用例前退出 1。A1–A8 的实跑与画面判读仍按各用例执行。

## 当前 A4 诊断

两种方向和 T1 对照的运行目录位于 `.pio/theme-menu-pr-paired/browser-captures/`，目录名以 `A4-` 开头。候选 Day→Night 的 `pre-reset.log` 及 Night→Day 的 `partial.log` 显示真实写入、菜单即时刷新，并分别与同方向基线核对确认窗口内的共享配色事件。两个候选方向均只记录首次 ROM 启动。用 10 kΩ 上拉的 EN 诊断也只有一次启动，见 `.pio/theme-menu-next/a4-en-pullup/`。工具栏重启前已记录 Night 保存成功，重启后串口输出网页示例的 `Please view the instructions in the source code!`，这次启动不计入候选验收。交接仍在 Develop。

PR 工作树的汇总检查通过 A1–A3 及双档探针隔离后，在 A4 缺重启采集回执处退出 1。见 `.pio/theme-menu-pr-paired/all-browser-check.log`。单项复验仍可运行其余场景。

在 PR 工作树根目录，使用可运行 Espressif NVS 工具的 Python 环境执行下列命令。`pair` 指向同次双档构建证据，`ref_build` 指向 T1 的 `test-wokwi` 目录，`nvs_gen` 指向 Espressif 生成脚本。浏览器模式用 `--prepare-only` 生成场景目录，用 `--check-capture` 回读同一批目录。LCD 的高亮、标记和配色由人工对照验收例判读。

```bash
test/wokwi/theme_menu_focus/run.sh --case all \
  --build-dir "$pair/build/test-wokwi" --build-evidence "$pair" \
  --reference-build-dir "$ref_build" --nvs-gen "$nvs_gen" \
  --out "$pair/browser-captures" --check-capture
```

## 恢复入口

用能加载本机全闪存镜像、支持 GPIO32/33、串口和 ILI9341 画面的本地模拟环境复跑 T1。准备和回读命令从仓库根执行。

```bash
out="$PWD/.pio/theme-menu-focus-t1.53hpkacc"
test/wokwi/theme_menu_focus/run.sh --case probe --build-dir "$out/build/test-wokwi" --out "$out/local" --prepare-only
test/wokwi/theme_menu_focus/run.sh --case probe --out "$actual_capture_dir" --check-capture
```

本地采集使用同一个准备好的目录。依据 `probe.yaml` 记录串口与三张截图，保存 `capture.json` 中的 `loaded_image_sha256` 及 `files` 文件摘要，校验后按 T1 的完成标准判读 LCD。重复执行 T1 时使用同一场景、实际加载的镜像和同次采集回执。
