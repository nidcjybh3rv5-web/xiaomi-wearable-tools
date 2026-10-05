# Xiaomi Wearable BLE Tool

Windows 本機工具，用來掃描與診斷使用者自己的 Xiaomi / Redmi 穿戴裝置。

## 執行

需要 Python 3.10+：

```powershell
py -m pip install -r requirements.txt
py xiaomi_scanner.py
```

工具會：
- 掃描附近 BLE 裝置
- 篩選可能的 Xiaomi / Redmi / Band / Watch 裝置
- 顯示名稱、位址與 RSSI
- 讓使用者選擇要檢查的裝置
- 進行正常的 GATT 服務與特徵探索
- 將結果寫入 `scan_result.json`

實際 BLE 掃描必須在有 Bluetooth 硬體的 Windows 電腦本機執行；GitHub Actions 只負責驗證與打包。

## 安全範圍

此工具只做一般 BLE 掃描、正常連線與 GATT metadata 探索。
不繞過配對、驗證或加密，不讀取其他使用者的認證資料。
