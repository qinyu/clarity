# 主题菜单焦点 · Design 方案

候选方案基于代码 `e3ea788eefe9b18e992658b249819c3ad992f93f`，对应已确认规格 `b0baf9b2dd9204621e1ae55916a9aae5b9d2f861b295388c31b471cd2259e4d6`。 [产品规格](theme-menu-focus.md) · [Define 确认回执](theme-menu-focus-define-approval.md) · [任务清单](theme-menu-focus-tasks.md)

## 调用路径与改动接缝

| 路径 | 已核实的行为和归属 |
| --- | --- |
| GPIO32 → `ActionHandler::ExecutePendingActions` → `ConfigPanel` | 短按循环推进索引，长按按面板索引执行动作。`ShowOptionsMenu` 打开所有选项子菜单时把面板、视图索引都重置为 0。 [动作派发](../../src/handlers/action_handler.cpp#L122) · [菜单动作](../../src/panels/config_panel.cpp#L177) · [菜单构造](../../src/panels/config_panel.cpp#L559) |
| `IConfigurationManager::GetConfigSection` → `ConfigPanel::ShowEnumOptionsMenu` | 面板拿到配置快照，按原始选项比较 `ConfigItem::value` 并添加 `>`。偏好缺项时由配置层加载默认 Day。未知字符串按原值读出，标记当前就不会命中。 [枚举标记](../../src/panels/config_panel.cpp#L674) · [默认值](../../include/managers/style_manager.h#L172) · [NVS 读取](../../src/providers/storage_provider.cpp#L197) |
| `ConfigPanel` → `ConfigComponent::SetMenuItems` / `SetCurrentIndex` | **改动接缝**在 Presenter 发布菜单项和初始焦点的位置。面板持有可执行动作的索引，视图使用同一个索引决定居中高亮。 [视图入口](../../src/components/config_component.cpp#L158) |
| `HandleSetConfigValue` → `UpdateConfig` → NVS；设置菜单刷新 | 长按才走更新入口，返回 Display 并刷新标题、提示颜色。Back 回到设置主菜单。 [保存与返回](../../src/panels/config_panel.cpp#L363) · [持久化](../../src/providers/storage_provider.cpp#L346) |
| GPIO33 → `TriggerHandler` 的 STYLE 触发 → `StyleManager::SetTheme` | 车灯开启/关闭分别应用 Night/Day 的即时样式。该路径独立于配置保存。部分面板进入时还有既有的主题处理，验收只把 Display 稳定后此次 Theme 操作内的事件归因给 Theme。 [车灯定义](../../include/definitions/interrupts.h#L82) · [面板切换](../../src/managers/panel_manager.cpp#L579) |

## ADR · 在 ConfigPanel 复用枚举匹配结果

**状态** Proposed。

**取舍** 对比以下三种接口。

| 方案 | 接缝与调用成本 | 验证代价与影响 |
| --- | --- | --- |
| **A · 构造枚举时返回匹配索引（推荐）** | 把已有的比较结果交回唯一调用方。该比较同时决定标记和候选索引，调用方只判断是否采用它。 | 只改两个生产文件里的私有接口。通过真实按键场景做红绿，依赖固件模拟可用。 |
| B · 抽出 C++17 纯匹配函数 | 传原始选项与保存值，返回匹配索引。主题构造可以复用同一结果给标记和焦点。 | 有主机级快速反馈，新增内部头文件和测试接口。实际焦点、长按与保存仍需端到端验证。 |
| C · 通用菜单焦点策略 | 枚举菜单接收显式的「首项／保存值」策略，主题单独启用。 | 多个菜单需要不同策略时有复用价值。目前只有一个启用点，调用契约比 A 大。若交由视图从渲染文本推断，会使高亮和长按动作发生偏差。 |

**决定** 选择 A，修改 `src/panels/config_panel.cpp` 及 `include/panels/config_panel.h`。同一个枚举匹配既有标记，又能给出对应位置。把决定留在面板能保留现有视图职责，也覆盖主题与亮度两者不同的初始焦点行为。

**接口与调用顺序**

1. 保留 `ShowOptionsMenu(const std::string& fullKey, const Config::ConfigItem& item)`。在清空旧菜单前复制 `fullKey`，避免引用旧 `actionParam`。
2. 将私有的 `ShowEnumOptionsMenu(const std::string& fullKey, const Config::ConfigItem& item, const std::vector<std::string>& options)` 返回值改为 `std::optional<std::size_t>`。在现有的一次循环中生成原有行和标记，返回首个与原始配置值匹配的行索引。无匹配返回空，调用方以 0 作为初始焦点。只有 `UIStrings::ConfigKeys::STYLE_MANAGER_THEME` 的枚举分支采用返回索引。枚举选项先建，Back 最后追加。
3. 完整列表就绪后给 `currentMenuIndex_` 赋值。组件就绪时按现有顺序发布标题和选项，再把同一索引交给 `SetCurrentIndex`。对未就绪组件，面板仍保有该索引。实现隐藏了标记文本和行构造顺序，按键调用方仍只需要面板原有入口。

**后果与回滚** 公开接口、配置键、NVS 格式及配置读写时机沿用现状。焦点在打开时使用同一配置快照，复用既有动作和触发的调度顺序。无需迁移，已保存值与旧值都按获批规格读取。回退焦点提交即可恢复首项定位，测试探针和场景可分别回退。

**Compliance** 生产层的差异检视限定在上述两个文件和私有路径，检查面板与视图取同一索引，亮度从首项打开，且焦点计算只取配置快照。T1 的测试探针单独检视，限定在测试构建并只观察已有操作。T2 的 A1 基线失败／候选通过与 A7 回归是接缝行为护栏。未增加跨模块依赖或公开入口，沿用项目现有边界检查与构建入口。

## 验证入口与判定

### 基线与取证

- **已执行** `./test/host/run_host_tests.sh` 通过，当前只运行 C++17 工具链冒烟。已有本地构建日志记录固定 LVGL 9.2.2 的基线产物构建成功。本轮用已有产物离线合并全闪存镜像，核对了应用段逐字节一致和 NVS 区间擦除态。带 EN 按键的临时接线图通过 `wokwi-cli lint --offline`，该检查只有既有板型提示。
- **待实跑** 本机 Wokwi CLI 0.29.1 在启动模拟前报告缺少 `WOKWI_CLI_TOKEN`。由 Develop 的 T1 先确认模拟器实际支持本方案的逐步截图和输入时序。EN 图的静态校验不代表芯片已重启。T5 的预置 NVS 在本机还缺可用的 Espressif 生成工具。
- **既有护栏** 按键端到端和主题焦点当前为 `unprotected`。旧通用场景的车灯日志给出触发线索，设置菜单步骤等待的旧文案已失效，无法作为 A1–A8 的通过依据。已确认规格要求的即时配色保留与持久化为高优先级。亮度回归为本次相关约束。
- **已知文档漂移** 主题 Wiki 将样式管理器的节级回调写成了必然生效，当前存储侧按完整配置键匹配。长按后即时验收范围用 Display 的标题和按键提示，加仪表共享配色的基线对照。 [回调注册](../../src/managers/style_manager.cpp#L398) · [回调匹配](../../src/providers/storage_provider.cpp#L389)

### 运行和证据规则

1. 从指定提交构建，依照 AGENTS.md 将 `platformio.ini` 复制到独立产物目录并固定 LVGL 9.2.2。使用 `PLATFORMIO_BUILD_DIR="$out/build" PLATFORMIO_LIBDEPS_DIR="$out/libdeps" pio run -d "$PWD" -c "$out/platformio.ini" -e test-wokwi`。记录源码 SHA、应用 BIN、ELF、分区表及实际加载的全镜像摘要。T1 只加观察探针，作为 A1 的行为基线和 A4 的配色对照；其父版本为上述代码基线。
2. 在 `test/wokwi/theme_menu_focus/` 新增场景、离线镜像准备及运行入口，复用 `diagram_automated.json` 的 GPIO32 `btn1`、GPIO33 `trigger_btn4`、`lcd1`。从仪表长按进入 Configuration，短按至 Display 并长按进入，再长按 Theme。默认阈值下以约 800 ms / 2000 ms 驱动短按 / 长按，释放后等该动作完成再观察。基线和候选分别按可见焦点导航到同一目标。
3. 拟定命令 `bash test/wokwi/theme_menu_focus/run.sh --build-dir "$out/build/test-wokwi" --out "$out/checks" --case A1`，支持 A1–A8 与 `all`。运行 A4 或 `all` 必须传 `--reference-build-dir "$ref/build/test-wokwi"`，运行 A8 或 `all` 必须传 `--nvs-gen "$nvs_gen"`。T1 的入口自测使用 `--case probe`。入口准备临时 Wokwi 项目，执行 `wokwi-cli "$sim" --scenario "$scenario" --serial-log-file "$serial" --timeout 120000`，保留串口、退出码和逐步 `lcd1` PNG。执行器自动检查日志和图像文件是否齐全，按表逐帧判读高亮、`>`、标题及颜色，并逐项写通过或失败。视觉部分当前设计为必做的人工断言。先在 T1 验证 `take-screenshot`，若已装版本只支持 CLI 定时截图参数，则重放同一场景前缀取各帧，同时保留一次完整连续运行的时序日志。每个重启后检查的重放前缀均须包含实际保存和同实例重启。 [Wokwi 场景与截图](https://docs.wokwi.com/wokwi-ci/automation-scenarios) · [Wokwi CLI 参数](https://docs.wokwi.com/wokwi-ci/cli-usage)
4. 在实际的按键派发、配置写入、设置菜单主题刷新和共享主题应用路径加测试构建限定的稳定事件。记录动作开始／完成、主题与亮度写入尝试／成功、设置菜单配色及共享主题实际应用值。事件带动作号或时间及不同的边界文案，避免既有 `log_t` 连续行去重造成漏检。显式保存和两种车灯变化作为阳性对照。A5/A6 只检查 Display 已稳定之后，从打开 Theme 的长按开始，持续到最后一次操作完成、界面稳定取帧并保持 500 ms 无输入后结束，期间固定车灯输入。场景在该窗口结束后停止，运行器检查到串口记录末尾。A4 基线与候选均从确认动作开始，取稳定的 Display 帧后保持相同无输入时段，再结束对照窗口。候选随后才拉低 EN，以第二次启动的开端截断重启前记录。未观察到预期按键分发或阳性事件时，检查失败。
5. A4 重启须在**同一模拟实例和同一份闪存**完成。测试图增加 EN → GND 的按键，短暂拉低并释放，串口需出现后续启动标记和仪表就绪，首次进入 Theme 前不再保存主题。若 Wokwi 实测不响应 EN，使用已获授权、能运行相同 test-wokwi 固件且接有 ILI9341 的受控 ESP32 台架按 EN 保留闪存，以同样的前／后证据判定。缺授权或台架时该项保留未通过。 [ESP32-DevKitC EN 定义](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp-dev-kits-en-master-esp32.pdf)
6. A8 单独运行全闪存镜像。用 Espressif 工具从测试 CSV 生成 `0x3000` 字节未加密 NVS 镜像，namespace 为 `cfg_style_manag`，字符串键值为 `theme=Legacy`。命令为 `python "$nvs_gen" generate "$fixture_csv" "$fixture_bin" 0x3000 --version 2`。以 PlatformIO 的偏移合并 bootloader、分区表、boot_app0 和应用，在 `0x9000` 放入 NVS 镜像，核对候选应用段逐字节与普通镜像相同。模拟启动经真实 NVS 加载，Display 先显示 Legacy。A2 的未保存分支使用 NVS 擦除态镜像，其他用例按表通过实际按钮准备偏好。 [分区表](../../partitions.csv) · [NVS 名称推导](../../src/providers/storage_provider.cpp#L437) · [Espressif NVS 生成工具](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/nvs_partition_gen.html) · [Wokwi 全闪存镜像](https://docs.wokwi.com/vscode/platformio#esp32-application-image-vs-full-image)

### A1–A8 检查矩阵

| 验收 | 可执行场景及通过条件 | 任务 |
| --- | --- | --- |
| A1 | 通过 GPIO32 保存 Night，再打开 Theme。留首帧 Night 居中带 `>`，直接长按，串口记录成功写 Night，Display 显示 Night，再开仍居中。在 T1 基线用同一路径复现初开 Day 的失败。 | T2 |
| A2 | 两个独立运行。一份使用擦除态 NVS，另一份通过长按保存 Day。两份首次验收打开均截取居中 `> Day`，保存分支另有成功写入记录。 | T2 |
| A3 | GPIO32 从 `> Day` 逐次短按，分别取 Night / Back / Day 居中帧，进入 Back 长按回 Configuration 后回到 Theme。帧证实 `>` 随配置留在 Day，且浏览、返回、重开区间无写入和手动配色。 | T2 |
| A4 | Day→Night 和 Night→Day 分开运行。固定车灯状态，确认目标后截 Display 的 Theme 值、标题和按键提示。对比 T1 基线同目标确认至 Display 稳定帧后的共享配色事件。保持同一闪存触发 EN，等第二次启动后重开 Theme，应高亮带 `>` 的新值。 | T4 |
| A5 | 保存 Day，仪表上通过 GPIO33 开灯，取 Night 仪表帧及触发事件。Display 稳定后打开 Theme，再短按聚焦 Night。两帧依次核对 `> Day` 居中、Night 居中但 `>` 在 Day，窗口中无主题写入、菜单配色刷新、共享配色应用事件。 | T3 |
| A6 | 保存 Night，仪表上开灯再关灯。保存两种配色帧与对应事件，再稳定进入 Display 并打开 Theme。首帧为 `> Night` 居中，Theme 操作窗口无主题写入、菜单配色刷新或共享配色应用事件。 | T3 |
| A7 | 先通过 GPIO32 在 Brightness 保存 50%。重开 Brightness 先截 0 居中，再只短按至 50 可见并截取 `> 50`，窗口中保持亮度未再保存。视图初开只显示中心附近的行。 | T2 |
| A8 | 从预置 Legacy 镜像启动。Display 显示 `Theme: Legacy`，打开 Theme 截 Day 居中且两个主题均无标记。Back 后重进 Display 确认值仍为 Legacy，再打开复验。显式确认前主题写入尝试为零。最后通过 GPIO32 长按 Night，串口确认成功，Display 与再次打开 Theme 均显示 Night，后者居中带 `>`。保留阶段之间的完整日志。 | T5 |

缺少任何必做断言的证据时，记录未通过及缺项。主机冒烟、纯逻辑、CLI 退出 0 或单张截图均不足以替代 A1–A8 的场景验证。
