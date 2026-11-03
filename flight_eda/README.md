# 紐約航班：缺失值處理與 PCA 敏感度分析

這是題目 E 的可重現作業專案。GitHub 版本包含程式、Notebook、AI 初版、正式 PDF 與六張操作快照；**大型原始 CSV 和衍生資料未放在此 GitHub 版本中**，可使用 `src/download_data.py` 下載並檢查雜湊。

**核心問題：缺失值的處理方式會不會改變 PCA 看到的結構？** 正文依老師要求依序為：
1. AI 基準報表（完整提示詞與原始輸出在附錄 A）；
2. 缺失值診斷；
3. 三種缺失處理策略的敏感度分析；
4. PCA 分析與 PC1／PC2 穩定性；
5. 600–900 字反思。

可直接執行且附中文方法註解的核心程式為 `src/analysis.py`；`analysis.ipynb` 的 17 個程式格也加入中文註解並保留執行結果。在 Google Colab，將 notebook 和完整繳交包 ZIP 一同上傳至左側檔案區後按「全部執行」，首格會自動辨識並解壓 ZIP。本機 Jupyter 則先解壓繳交包，使用 Python 3.11 安裝 `requirements.txt`，開啟 notebook 按「Run All」。分析會從原始 CSV 重算 PCA 與六個操作圖，不需先執行其他程式。單獨一個 `.ipynb` 不含原始資料。從本資料夾執行 `python src/analysis.py` 也可重建分析表與圖；完整重建含 Notebook、PDF 與驗證可執行 `bash reproduce_local.sh`。

### R 版本（不需額外 R 套件）

從 `flight_eda` 資料夾執行 `Rscript analysis.R`。程式以中文註解說明原始缺失與合併未配對、CCA／逐時均值／條件熱卡、標準化 PCA、共同航班分數比較與固定尺度檢查；表格及三張圖寫入 `output/r/`，不覆蓋 Python 產物。R 程式負責報告第 2–4 部分的核心計算；第 1 部分封存 AI 初版及第 5 部分反思仍在現有 PDF 與 `baseline/`、`docs/reflection.txt`。R 與 Python 的隨機數產生器不同，因此熱卡抽樣及其 PCA 數值會略有差異，CCA 與均值法可直接對照。


## GitHub 版本的檔案範圍與驗證界線

- 這份 GitHub 版本未包含 `data/raw/flights.csv`、`data/raw/weather.csv` 及大型 `data/derived/`、`output/interactive/`，請以 `bash reproduce_local.sh` 重建；請勿將下載腳本視為已通過全新環境的實測。
- GitHub 目前有 `output/pdf/`、`output/screenshots/`、`output/submission/`，並已補入重現必要的 `docs/reflection.txt` 與 `docs/dashboard_publication.json`；但**沒有** `output/presentation/`、`assets/`、`完成互動截圖.command` 以及 README 所提的其他 `docs/` 指南。那些文件屬於本機完整作業包，不能當作已上傳的 GitHub 檔案。簡報可另外作為繳交附件。
- `output/screenshots/` 是分析程式輸出的篩選／框選快照，不是已人工操作的瀏覽器畫面；已發布 Dashboard 的首頁可開啟，但 hover、brushing 等視覺互動仍需實際檢查。
- **重現起點**：`python3 -m venv .venv` → `source .venv/bin/activate` → `python -m pip install -r requirements.txt` → `bash reproduce_local.sh`。PDF 建置可能需要本機可用的中文字型；若因字型失敗，數值結果與 Notebook 可分開核對。

## 先開哪個檔案

- **7 分鐘口頭報告**：`output/presentation/題目E_7分鐘口頭報告.pptx`，10 張，目標 7 分 38 秒；每張附講者備註。逐頁「這一步在做什麼」、可直接講的文字與名詞速查見 `output/presentation/題目E_7分鐘逐頁講稿與理解指南.txt`。
- **完整簡報**：`output/presentation/被刪掉的航班_缺失值與PCA_完整版.pptx`，14 張，保留更多細節，附逐頁講者備註。圖表與表格可編輯；舊版講稿另存 `output/presentation/逐頁講稿.txt`。
- **報告**：`output/pdf/nycflights_missing_pca_report.pdf`，正文 **11 頁**，附錄 7 頁。反思為 670 個中文字，完整提示詞與 AI 初版輸出在附錄 A。
- **Notebook**：`analysis.ipynb`。17 個程式儲存格已實際執行，保留數值與六個操作的圖像輸出。Jupyter 中可以重新執行 live widget。
- **免安裝互動成果**：用瀏覽器開啟 `output/interactive/flight_explorer.html`。所有資料與 Plotly 函式庫都在檔案內，不需伺服器或網路。可 hover 航班與負荷量、篩選機場／航空公司／月份／時段／原始天氣、框選分數圖，以及切換所選機場的 PCA 模型。
- **操作圖與文字**：`output/screenshots/` 有 6 張圖，`operations.json` 附完整條件、樣本數、均值及發現，notebook 和 PDF 也逐張說明。

**互動儀表板已發布：** https://snazzy-beijinho-a8153e.netlify.app/ 。2026-11-01 使用者以 Safari 私密瀏覽視窗開啟首頁，畫面顯示全體 327,346 班、平均抵達延誤 6.90 分與前兩軸解釋變異 41.20%；證據存於 `output/publication/`。這確認公開首頁載入，尚未對 hover 與手動框選做瀏覽器視覺驗證。現有 6 張 PNG 是實際執行篩選與矩形幾何框選後的分析輸出，不是瀏覽器畫面；依題目要求，已發布連結可作為互動成果繳交。

已新增 **`完成互動截圖.command`**。在這台 Mac 的一般桌面環境雙擊執行，會實際點選六個步驟、拖曳框選及顯示分數／負荷量 hover，保存 **8 張瀏覽器截圖**，再自動附入 `analysis.ipynb`。這個流程尚未在本環境成功執行，只有實際成功後才會出現 `output/browser_screenshots/capture_manifest.json`。詳細步驟見 `docs/交付狀態與操作說明.txt`。

跨平台可執行 `node src/capture_browser.cjs`，成功後執行 `python src/attach_browser_evidence.py`。需要 Playwright 與 Chrome；若沒有，先安裝 Node.js，再執行 `npm install --no-save playwright` 和 `npx playwright install chromium`。可用 `EDA_CHROME_PATH` 指定 Chrome 路徑。

## 主要結果

1. 原始 336,776 班；8,255 班無出發紀錄、1,175 班其他飛行測量不完整，PCA 適用母體為 **327,346 班**。
2. 完整列刪除保留 291,140 班，平均抵達延誤從 **6.895 分鐘降到 4.760 分鐘**。
3. 原始逐時天氣中，氣壓缺失群的降雨比例 **34.15%**，有氣壓群 **3.49%**。缺失群濕度較高、能見度較低。
4. 篩出「原始有雨＋氣壓缺失」得到 **11,915 班、平均抵達延誤 39.18 分鐘**；CCA 會排除這整群。
5. 各策略重新標準化時，HOTDECK 與 CCA 的 PC1／PC2 方向餘弦約 **0.991／0.999**，前兩軸最大角度 **7.70°**；固定 HOTDECK 尺度後角度為 **23.74°**。「穩定」依賴尺度選擇。
6. 前兩個主成分約解釋 41% 變異；三策略都需 **5 個成分**才達累積 80%。

## 方法與分析範圍

- 11 個 PCA 變數：`dep_delay, arr_delay, air_time, distance, temp, dewp, humid, wind_speed, precip, visib, pressure`。
- 類別／分層資訊：`origin, carrier, dest, month, time_band, weekday, season, rain_group`，不將類別代碼投入 PCA。
- 以 `origin` 與 UTC `time_hour` 左連接；核對右表鍵值唯一、航班列數不變。
- 區分原始欄位 NA、合併未配對及品質旗標。1,556 班未配對天氣；氣壓原表缺 2,729 個時點，合併後缺 38,788 班。
- `CCA`：適用母體中保留完整列。
- `MEAN`：在逐時天氣表層級填欄均值，再合併至航班。
- `HOTDECK`：在同機場、同當地月份內，按可觀測天氣與時間找最近 5 個完整天氣供體，抽取一個、只複製缺失欄。每個時點只補一次。20 次 seed 為 20261026–20261045，報表主圖使用第一份。
- 這是**條件式熱卡**，不是 MICE／PMM，20 次的變化範圍不是正式多重插補後驗或信賴區間。
- 缺失邏輯斯模型在逐時天氣表上按曆日分組交叉驗證，避免將重複航班天氣當成獨立驗證觀測。AUC 不能證明 MAR。
- 未替取消／不適用航班創造延誤，結論不外推到全部排定航班。

## 一般環境重跑

建議 **Python 3.11**。本 GitHub 版本未附大型原始 CSV，首次重建需要連網下載固定版本資料；下載完成且檢查通過後，後續統計運算可離線執行。

```bash
cd flight_eda
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash reproduce_local.sh
# 可選：如果安裝 Node.js，另可執行 node src/check_interactive.cjs
```

`node` 僅用於最後的互動邏輯檢查，不是計算 PCA 的必要依賴。`reproduce_local.sh` 會依序下載／核對資料、重建分析結果、操作圖、互動 HTML、Notebook、PDF，並執行驗證。Notebook 重現也會再跑分析，因此全包重建會重複部分工作，以確保 notebook 的輸出真的執行過。

PDF 需要中文 TrueType 字型。macOS 自動使用 `/System/Library/Fonts/Supplemental/Arial Unicode.ttf`。其他系統可將具繁體中文字形的 TrueType 字型放到 `assets/NotoSansTC-Regular.ttf`。程式不會下載或散布系統專有字型；環境不同時排版可能略有差異，應再次檢查頁數。

### 這台電腦的既有環境

原始作者使用過 `/opt/anaconda3/bin/python` 及特定 PDF 執行環境；**這些路徑並非其他電腦的必要條件**。新版腳本優先使用目前啟用的虛擬環境 Python，也可用 `EDA_PYTHON` 指定：

```bash
cd flight_eda
bash reproduce_local.sh
```

## 程式與產物

| 路徑 | 用途 |
|---|---|
| `src/download_data.py` | 驗證原始檔；若缺檔，按固定 Git blob 下載並核對 SHA-256 |
| `src/baseline.py` | 初版 EDA 的數值與圖形程式；不要在要保留封存版時覆寫 baseline |
| `baseline/prompt.txt`、`ai_output.txt` | 完整初版提示詞與文字輸出 |
| `baseline/frozen_manifest.json` | 初版封存時間與每個檔案雜湊 |
| `src/analysis.py` | 原始資料到診斷、三策略、20 次熱卡、PCA 與靜態圖表 |
| `src/explorer.py` | 全資料篩選／框選、live notebook widget 及六個操作輸出圖 |
| `src/build_interactive.py`、`explorer_app.js` | 自含式離線 HTML；群體模型以全資料擬合 |
| `src/build_notebook.py` | 在 IPython 同一行程實際執行儲存格並保存豐富輸出，不需開網路 kernel |
| `src/build_report.py` | 產生 11 頁正文及完整附錄 PDF |
| `output/tables/` | 完整數值表、共同缺失計數、缺失群比較、20 次結果、機場分層 |
| `output/validation.json` | 原始資料、母體、觀測值保存、PCA、操作重現、notebook 與反思字數核對 |
| `output/interactive_logic_validation.json` | 真實前端篩選邏輯的數值檢查；不冒稱瀏覽器視覺測試 |

## 六步互動操作清單

1. **全體 HOTDECK**：核對 n=327,346、平均抵達延誤=6.90。
2. **改成 CCA**：核對 n=291,140、平均=4.76；觀察圖形相似但母體改變。
3. **HOTDECK＋有雨＋氣壓缺失**：核對 n=11,915、平均=39.18；定位被刪掉的高延誤群。
4. **固定 UA**：核對 n=57,782，查看三機場樣本數不平衡。
5. **框選 PC1∈[-4,4]、PC2∈[2,8]**：全資料 n=47,477、平均距離=2,479 英里、平均延誤=-5.04，沒有 LGA。HTML 手動框選只使用展示樣本；其預設第 5 步另列已在 Python 計算的全資料摘要。Notebook 的矩形回呼直接套用全資料。
6. **LGA 子群重估 PCA**：核對 n=101,140，檢查負荷量，註明座標系已重新估計。

散布圖為了流暢度抽樣；所有正式模型與主要表格均使用全資料。HTML 保留固定隨機 18,000 班；notebook live 最多顯示 8,000 點；操作 PNG 最多顯示 10,000 點。固定展示範圍外的點仍在完整統計中。

## 資料來源與課堂連結

- [nycflights13 flights 官方定義](https://nycflights13.tidyverse.org/reference/flights.html)
- [nycflights13 weather 官方定義](https://nycflights13.tidyverse.org/reference/weather.html)
- [Rdatasets 公開 CSV 鏡像](https://github.com/vincentarelbundock/Rdatasets/tree/master/csv/nycflights13)
- 固定來源與 SHA-256 見 `data/source_manifest.json`；分析沒有直接引用會更新的 master 版本而不做檢查。
- 老師 w06 p.18–23、27–31、37–42：缺失機制、熱卡、插補模型；w05 p.7–9、16–20：尺度、PCA 與成分數；w02 p.3–4：互動探索；w03 p.4–6：合併；w08 p.16–20：分層比較。

## AI 揭露與最後確認

這份草稿由 Codex 協助完成。AI 基準是同一對話內的初版，不是無前文的新對話；已如實揭露。反思所寫的發現來自實際程式操作，不宣稱繳交者本人已完成操作。繳交前請自行重跑、確認反思符合自己的理解，並按課堂規定填寫姓名／學號及補拍需要的 UI 截圖。
