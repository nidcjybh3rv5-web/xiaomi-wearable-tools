# Xiaomi Wearable Tools

小米穿戴裝置通用工具專案，目標支援多種 Xiaomi Watch、Xiaomi Band、Redmi Watch 與其他相關穿戴裝置。

## v0.1.0

目前第一階段提供 Windows 本機 BLE 診斷工具：

- 🔵 掃描附近 Xiaomi / Redmi BLE 裝置
- 🔎 顯示裝置名稱、位址與 RSSI
- 📋 讓使用者自行選擇要檢查的裝置
- 🔧 讀取標準 GATT Services / Characteristics metadata
- 💾 匯出 JSON 診斷結果
- 🧪 GitHub Actions 執行語法檢查與單元測試
- 📦 GitHub Actions 打包 ZIP

> 實際 BLE 掃描需要在自己的 Windows 電腦上執行。GitHub Actions 沒有你的電腦 Bluetooth 硬體，因此只負責測試與打包。

## 快速開始

Windows + Python 3.10+：

```powershell
cd tools/ble
py -m pip install -r requirements.txt
py xiaomi_scanner.py
```

掃描完成後會在 `tools/ble/scan_result.json` 保存結果。

## GitHub

- 專案：https://github.com/nidcjybh3rv5-web/xiaomi-wearable-tools
- Actions：https://github.com/nidcjybh3rv5-web/xiaomi-wearable-tools/actions

## 專案結構

```text
xiaomi-wearable-tools/
├─ tools/
│  └─ ble/
│     ├─ xiaomi_scanner.py
│     ├─ requirements.txt
│     └─ README.md
├─ devices/
│  ├─ band/
│  └─ watch/
├─ tests/
│  ├─ test_xiaomi_scanner.py
│  └─ README.md
├─ .github/
│  └─ workflows/
│     └─ build-ble-tool.yml
└─ README.md
```

## 後續規劃

1. 建立 Xiaomi / Redmi 型號資料庫
2. Band 9 / Band 11 型號辨識
3. Watch / Redmi Watch 型號辨識
4. GATT 結果標準化
5. 更完整的 Windows 診斷介面

## 安全範圍

本專案只用於使用者自己的穿戴裝置診斷與開發。

不提供或協助繞過配對、驗證、加密或其他存取控制，也不擷取其他使用者的認證資料。
