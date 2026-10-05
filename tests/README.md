# Tests

目前包含 Xiaomi Wearable BLE 工具的基本單元測試。

執行：

```powershell
py -m unittest discover -s tests -p "test_*.py" -v
```

測試不需要實際 Bluetooth 硬體；實機 BLE 掃描仍需在 Windows 本機執行。
