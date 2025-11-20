# 🏠 房地產阿宥 - 大數據分析系統

專業的台灣房地產實價登錄分析工具

## 功能特色

- 📊 自動抓取內政部實價登錄資料
- 🎯 智能計算屋齡、單價、總價
- 📈 互動式視覺化圖表
- 🤖 AI 自動解讀市場熱門價格帶
- 💾 CSV 資料匯出功能

## 快速部署到 Streamlit Cloud

### 方法一：使用 GitHub（推薦）

1. 在 GitHub 建立新的 repository
2. 上傳以下檔案：
   - app.py
   - requirements.txt
   - .streamlit/config.toml

3. 前往 [Streamlit Cloud](https://share.streamlit.io/)
4. 點擊 "New app"
5. 選擇你的 GitHub repository
6. 主檔案路徑填寫：`app.py`
7. 點擊 "Deploy"

### 方法二：本機測試

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 技術架構

- **前端框架**: Streamlit
- **資料處理**: Pandas, NumPy
- **視覺化**: Plotly
- **資料來源**: 內政部不動產交易實價查詢服務

## 聯絡資訊

- **服務**: 群義房屋雲科店
- **專業證照**: (111)登字第412217號
- **電話**: 0906-707-964
- **網站**: 房地產阿宥.com

## 授權

© 2024 房地產阿宥 版權所有
