# Xiaomi Wearable Tools

小米穿戴裝置通用工具專案，目標支援多種 Xiaomi Watch、Xiaomi Band、Redmi Watch 與其他相關穿戴裝置。

## 目前規劃

- 🔵 BLE 裝置掃描
- 🔎 Xiaomi / Redmi 穿戴裝置辨識
- 🔧 GATT 服務與特徵檢查
- 💻 Windows 本機診斷工具
- 📦 GitHub Actions 自動建置
- ⌚ 逐步加入不同 Xiaomi Watch / Band 型號支援

## 安全範圍

本專案用於使用者自己的穿戴裝置診斷與開發。

不提供或協助繞過配對、驗證、加密或其他存取控制，也不擷取其他使用者的認證資料。

## 專案結構

```text
xiaomi-wearable-tools/
├─ tools/
│  └─ ble/
├─ devices/
│  ├─ band/
│  └─ watch/
├─ tests/
├─ .github/
│  └─ workflows/
└─ README.md
```

## 開發方向

第一階段先建立通用 BLE 基礎工具，再依裝置型號加入專用診斷與資料解析。

目前版本：**v0.1.0**
