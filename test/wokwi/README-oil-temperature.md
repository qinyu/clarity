# 油温失效的模拟验收

从仓库根目录运行。常规与验收镜像分别放在独立目录，以便核对两个构建是否正确隔离仿真注入。两个配置副本都固定 LVGL 9.2.2。

```bash
for variant in regular acceptance; do
  out="$PWD/.pio/oil-temperature/$variant"
  python3 test/wokwi/prepare_oil_temp_config.py "$variant" "$out"
  PLATFORMIO_BUILD_DIR="$out/build" PLATFORMIO_LIBDEPS_DIR="$out/libdeps" \
    pio run -d "$PWD" -c "$out/platformio.ini" -e test-wokwi || exit 1
done
```

验收构建使用 `diagram_oil_temp_acceptance.json` 与各 `scenario_oil_temp_*.yaml`，UART0 RX 接 GPIO17。启动串口应出现 `oil-temp acceptance rx=17`。常规构建使用现有自动化线路图，可用红色调试按钮回归全局错误面板。

若模拟器加载应用镜像后在程序启动前反复复位，使用 PlatformIO 随附的 esptool 和当前构建产物合并完整闪存镜像。对应偏移为 `0x1000` 的 bootloader、`0x8000` 的分区表、`0xe000` 的 Arduino `boot_app0.bin` 和 `0x10000` 的应用 BIN。记录应用和实际加载镜像的 SHA-256。通过 `wokwi-cli --elf <实际镜像> --diagram-file <线路图> --scenario <场景>` 指定同版输入。

RAW 场景的第一次读数来自油温传感器的 GPIO39，使用 4096 触发真实校验和上报。缓存期第二读保持无效，上报增量为零。A2 两个场景从同样的 80 °C 与输入序号 3 起步，分别捕获第一、第二次无效刷新后的油温表画面。
