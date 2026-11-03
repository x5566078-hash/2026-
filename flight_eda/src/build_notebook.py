"""Build and execute the notebook in-process, preserving real rich outputs.

Uses IPython InteractiveShell rather than opening a network kernel in restricted
environments. Each saved code output was actually executed, not fabricated.
"""
from pathlib import Path
import os,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplcache'))
import nbformat as nbf
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output

def build(execute=True):
    nb=nbf.v4.new_notebook();cells=[]
    def md(s):cells.append(nbf.v4.new_markdown_cell(s))
    def code(s):cells.append(nbf.v4.new_code_cell(s))
    md('''# 被刪掉的航班，會改變我們看到的準時表現嗎？

題目 E｜2013 nycflights13｜缺失值處理 × PCA 敏感度分析

**主要結論**：完整列刪除將平均抵達延誤由 6.90 降到 4.76 分鐘；各策略自行標準化時，PC1／PC2 大致穩定，但固定尺度後差異變大。

本 notebook 包含實際執行的數值、六個篩選／矩形框選輸出快照及其完整條件。圖像是程式操作的輸出快照，非聲稱由滑鼠操作擷取的瀏覽器螢幕截圖。若老師嚴格要求 UI 截圖，請按下面六步在互動工具操作後補拍。

資料、程式、圖像與草稿由 Codex 協助。AI 基準為同一對話的初版，非獨立盲測；反思請依本人理解審閱。
''')
    md('''## 0. 一鍵重現：從上到下執行所有儲存格

1. **Google Colab**：將完整繳交包 ZIP 與本 notebook 都上傳到 Colab 左側「檔案」。按 **全部執行**；首格會辨識 ZIP 內容並自動解壓出 `flight_eda/`。左側只有 ZIP、尚未解壓時也可以開始執行。Colab 重新連線後，檔案可能消失，需重新上傳 ZIP。
2. **本機 Jupyter**：先解壓 ZIP，保留 `analysis.ipynb`、`src/`、`baseline/`、`data/raw/` 在同一個 `flight_eda` 資料夾。建議 Python 3.11，在 `flight_eda` 執行 `python -m pip install -r requirements.txt`，然後按 **Run All／執行所有儲存格**。
3. 單獨下載 `.ipynb` 不含約 35 MB 的原始 CSV，無法重現。分析會從原始 CSV 重新計算，不依賴隨包附上的舊 `output/`。整體計算包含 20 次固定種子的熱卡抽樣，可能需要數分鐘。末格會核對樣本數、三種策略與六個操作結果，顯示「重現成功」。

如果第一格顯示缺少套件，請在**目前 notebook 的 Python 環境**安裝 `requirements.txt` 後重新啟動 kernel 再執行。''')
    code('''# Colab 可直接從左側已上傳的完整 ZIP 解壓；本機則定位已解壓的專案。
from pathlib import Path
import sys, os, json, importlib.util
from zipfile import ZipFile, BadZipFile

def find_project(start):
    candidates = []
    for parent in [start, *start.parents]:
        candidates.extend((parent, parent / 'flight_eda'))
    for candidate in candidates:
        if (candidate / 'src/analysis.py').is_file() and (candidate / 'requirements.txt').is_file():
            return candidate.resolve()
    raise FileNotFoundError('找不到 flight_eda 專案。請解壓完整繳交包，並從該資料夾或其上層開啟 notebook。')

def unpack_uploaded_project(start):
    # 只辨識本作業的完整繳交包，不解壓無關的 ZIP。
    directories = [start, *list(start.parents)[:2]]
    if Path('/content').is_dir() and Path('/content') not in directories:
        directories.append(Path('/content'))
    needed = {'flight_eda/src/analysis.py', 'flight_eda/requirements.txt',
              'flight_eda/data/raw/flights.csv', 'flight_eda/data/raw/weather.csv'}
    for directory in directories:
        for archive in sorted(directory.glob('*.zip')):
            try:
                with ZipFile(archive) as bundle:
                    names = set(bundle.namelist())
                    if not needed.issubset(names):
                        continue
                    target_root = directory.resolve()
                    for member in bundle.infolist():
                        target = (target_root / member.filename).resolve()
                        if not target.is_relative_to(target_root):
                            raise ValueError(f'ZIP 含不安全路徑：{member.filename}')
                    bundle.extractall(target_root)
                print(f'已解壓完整繳交包：{archive.name}')
                return
            except BadZipFile:
                continue
    raise FileNotFoundError('找不到完整繳交包 ZIP。請將最新的「題目E_期中口頭報告_繳交包.zip」上傳至 Colab 左側檔案區，再按全部執行。')

try:
    ROOT = find_project(Path.cwd().resolve())
except FileNotFoundError:
    unpack_uploaded_project(Path.cwd().resolve())
    ROOT = find_project(Path.cwd().resolve())
required = {'numpy':'numpy', 'pandas':'pandas', 'scipy':'scipy', 'sklearn':'scikit-learn',
            'matplotlib':'matplotlib', 'plotly':'plotly', 'ipywidgets':'ipywidgets', 'IPython':'ipython'}
missing = [pip_name for module, pip_name in required.items() if importlib.util.find_spec(module) is None]
if missing:
    raise ModuleNotFoundError(f'缺少 {missing}；請在目前 notebook 的 Python 環境執行：{sys.executable} -m pip install -r "{ROOT / "requirements.txt"}"，重啟 kernel 後再 Run All。')
raw_files = [ROOT / 'data/raw/flights.csv', ROOT / 'data/raw/weather.csv']
absent = [str(path) for path in raw_files if not path.is_file()]
if absent:
    raise FileNotFoundError(f'缺少原始 CSV：{absent}。請解壓完整繳交包；只上傳 ipynb 不足以重現。')
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.mplcache'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
from IPython.display import display, Image, Markdown
from download_data import verify_or_download
verify_or_download()
print(f'專案：{ROOT}\\nPython：{sys.version.split()[0]} ({sys.executable})')
''')
    md('## 1. AI 基準報表\n先保存初版提示詞與原始輸出，再做缺失機制診斷。封存檔不在正式分析中改寫。完整文字與機器可讀輸出在 baseline/，PDF 附錄 A 也保留全文。')
    code("# 第一部分：展示事先封存的 AI 初版，避免看過正式結果後改寫基準。\ndisplay(Markdown('### 完整提示詞\\n'+(ROOT/'baseline/prompt.txt').read_text()))\ndisplay(Markdown('### 完整初版輸出\\n'+(ROOT/'baseline/ai_output.txt').read_text()))\ndisplay(Image(filename=str(ROOT/'baseline/baseline_distributions.png')))")
    md('## 2. 缺失診斷與三策略分析\n主程式從兩個原始 CSV 讀入，核對左連接鍵、保留缺失來源，執行所有診斷、三種策略、PCA、補值遮蔽檢查與圖表。固定 seed=20261026，HOTDECK 重複 20 次；不是把熱卡重抽冒稱正式 MI。')
    code("# 第二至四部分的計算入口：每次 Run All 都從原始 CSV 重新計算，不讀舊的分析結果。\nfrom analysis import run\nrun(draws=20)")
    code("# 分清楚原始欄位缺失與合併後缺失，再看共同缺失及有／無缺失群差異。\ndisplay(pd.read_csv(ROOT/'output/tables/missing_provenance.csv'))\ndisplay(Image(filename=str(ROOT/'output/figures/missingness.png')))\ndisplay(pd.read_csv(ROOT/'output/tables/pressure_groups.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/missing_vs_observed.csv'))")
    md('### 機制判斷\n- 無出發紀錄：取消代理；對未出發班次，實際延誤不適用。資料沒有正式取消旗標，不把每一筆都當已確認取消。\n- 另 1,175 班已出發但飛行測量不完整，可能轉降或未回報；原因未辨識，主 PCA 不創造其抵達延誤。\n- 氣壓缺失與高濕度、降雨及低能見度相伴。條件 MAR 僅作工作假設，不能由預測 AUC 證明；MNAR 仍可能。\n- 零星溫度／露點／濕度／風速缺值原因未知；不能因少就斷言 MCAR。\n- 合併未配對是天氣覆蓋缺口，和欄位本來為 NA 分開。降水與能見度的原始表無缺值。\n- 距離完整。極端風速另標記；該時點沒有航班相配，保留原值的完整個案 PCA 相同；熱卡法仍排除其供體資格，不能將此結論擴大到所有插補流程。')
    code("# 缺失可被觀測變數預測，不等於已證明 MAR；同時核對不適用航班與未配對時點。\ndisplay(pd.read_csv(ROOT/'output/tables/missingness_logistic_cv.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/flight_status.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/unmatched_by_month.csv'))")
    md('## 3. 缺失處理的敏感度\nCCA 僅保留適用母體中的完整列。MEAN 在逐時天氣表填均值；HOTDECK 在同機場及同月份，按觀測天氣與時間找 5 位近鄰供體抽一位。每一時點只補一次，再合併至所有航班。三者使用同樣 11 欄，均不替取消或不適用班次填延誤。')
    code("# 第三部分：CCA、逐時均值與條件熱卡的樣本數、描述統計及遮蔽驗證。\ndisplay(pd.read_csv(ROOT/'output/tables/strategy_summary.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/descriptive_strategies.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/mask_validation.csv'))")
    md('## 4. PCA 與穩定性\n不同單位先逐策略標準化。碎石圖及累積至少 80% 準則均支持保留 5 個成分，前兩個只為視覺化。係數與相關負荷量都保留。先對齊符號，再在共同完整航班比較分數，另比較子空間角度。')
    code("# 第四部分：檢查保留成分數、PC1／PC2 方向與固定尺度後的敏感度。\ndisplay(Image(filename=str(ROOT/'output/figures/scree.png')))\ndisplay(pd.read_csv(ROOT/'output/tables/pca_stability.csv'))\ndisplay(Image(filename=str(ROOT/'output/figures/loading_comparison.png')))\ndisplay(pd.read_csv(ROOT/'output/tables/additional_sensitivity.csv'))")
    md('### 4.1 Live 互動工具\n執行下一格後，可 hover 航班與負荷量、用下拉選單篩選、拖曳矩形框選，或勾選子群重新估計 PCA。繪圖最多 8,000 點，矩形幾何邊界會套用到全部篩選後航班計算摘要。若 widget 前端未安裝，直接以瀏覽器開啟 output/interactive/flight_explorer.html。\n\n注意：重新擬合會換座標系；不要把換座標系後的點位移當成同一軸上的改變。')
    code("# 互動探索：可篩選、框選與重估子群 PCA；摘要仍由全資料計算。\nfrom explorer import Explorer, make_snapshots\nex = Explorer()\npanel = ex.widget()\ndisplay(panel)")
    md('### 4.2 保留的六個操作與發現\n下面各格真的重新執行篩選／幾何框選，並顯示該操作產生的圖。PNG 也獨立儲存在 output/screenshots。用互動介面重做時，可對照此處的條件、全資料 n 與平均值。')
    code("# 依相同參數重建六次操作，保存圖像與可核對的完整樣本數。\noperations = make_snapshots()\nprint('已重建', len(operations), '個操作紀錄與圖像')")
    ops=json.loads((ROOT/'output/screenshots/operations.json').read_text())
    params=[dict(strategy='HOTDECK'),dict(strategy='CCA'),dict(strategy='HOTDECK',rain='rain',pressure='missing'),dict(strategy='HOTDECK',carrier='UA'),dict(strategy='HOTDECK',brush=[-4,4,2,8]),dict(strategy='HOTDECK',origin='LGA',refit=True)]
    findings=[
      '全適用母體共有 327,346 班，平均抵達延誤 6.90 分鐘。先確認參考群體與模型，再解讀分群。',
      '只換成 CCA，少了 36,206 班、平均延誤降至 4.76 分鐘；散布圖相似並不表示樣本選擇無影響。',
      '11,915 班有雨且氣壓缺失，平均延誤 39.18 分鐘；整群會被 CCA 排除，這是從交叉篩選定位的關鍵群體。',
      'UA 的 57,782 班在機場分布不均：EWR 45,501、JFK 4,478、LGA 7,803；機場均值比較受航空公司與航程組成影響。',
      '本機參考結果為矩形內約 4.7 萬班、平均距離約 2,480 英里、平均延誤約 -5 分鐘，沒有 LGA。重跑時請以本格實際輸出為準；高 PC2 主要是航程，而不是延誤程度。',
      'LGA 子群 101,140 班平均航程 785 英里。重估後 PC2 的抵達延誤係數由 -0.185 變成 +0.176，溫度由 +0.050 變成 -0.274，而距離仍為正向。這不是單純整軸正負號翻轉，子群中的混合意義確實不同；不能與原固定座標直接比較。']
    for i,(op,par,find) in enumerate(zip(ops,params,findings),1):
        md(f'#### 操作 {i}：{op["title"].split(" | ")[-1]}\n\n**這個操作讓我發現了什麼：** {find}')
        args=', '.join(f'{k}={v!r}' for k,v in par.items())
        code(f"# 操作 {i}：依下列篩選條件重算摘要，並展示相應的分析圖。\nresult = ex.select({args})\ndisplay(pd.Series(result['summary'], name='完整資料操作結果'))\ndisplay(result['airports'])\ndisplay(Image(filename=str(ROOT/{op['image']!r})))")
    md('### 機場分層延伸\n先限定三機場皆有足夠樣本的共同航空公司×月份×時段格子，再比較共同組成加權的機場均值。此處仍沒有調整航線及所有天氣，不能視為因果效果。')
    code("# 額外按航空公司、月份與時段限制共同組成，檢查機場均值差異。\ndisplay(pd.read_csv(ROOT/'output/tables/airport_delay.csv'))\ndisplay(pd.read_csv(ROOT/'output/tables/airport_standardized.csv'))")
    md('## 5. 反思（AI 協助草稿，請依本人理解審閱）\n\n'+(ROOT/'docs/reflection.txt').read_text())
    md('## 可重現性與限制\n- 原始 CSV、固定 Git blob 與 SHA-256：data/raw 與 src/download_data.py。\n- AI 基準全文及其封存清單：baseline/。\n- 所有表格：output/tables；20 次抽取的差異是演算法敏感度，不是信賴區間。\n- output/screenshots/operation_log.json 保留全部篩選、框選界線與結果。\n- 資料來源與課堂參考見 README 與 PDF。\n- 這份 notebook 的預存輸出以 IPython 同一行程實際執行產生；live widget 前端視覺 QA 因環境限制未完成。')
    code("""# 最後核對本次新算的核心結果、六個互動操作與原始檔雜湊。
from math import isclose
summary = pd.read_csv(ROOT/'output/tables/strategy_summary.csv').set_index('strategy')
results = json.loads((ROOT/'output/results.json').read_text())
records = json.loads((ROOT/'output/screenshots/operations.json').read_text())
assert results['draws'] == 20 and results['n_total'] == 336776 and results['n_eligible'] == 327346
assert int(summary.loc['CCA','n']) == 291140
assert int(summary.loc['HOTDECK','n']) == 327346
assert isclose(summary.loc['HOTDECK','arr_delay_mean'], 6.89537675731489, abs_tol=1e-8)
assert len(records) == 6 and all((ROOT / row['image']).is_file() for row in records)
counts = [row['n'] for row in records]
print('六個操作的本次樣本數：', counts)
# 非框選操作是資料篩選，樣本數必須一致；矩形邊界上的 PCA 分數會受數值套件版本影響。
assert [counts[i] for i in (0,1,2,3,5)] == [327346, 291140, 11915, 57782, 101140]
brush = records[4]
assert 45000 <= brush['n'] <= 50000, f'框選樣本數異常：{brush["n"]}'
assert 2300 <= brush['distance_mean'] <= 2600, '框選平均航程與長程群的發現不符'
assert -8 <= brush['arr_delay_mean'] <= -2, '框選平均延誤與原發現不符'
assert brush['airport_counts'].get('LGA', 0) == 0, '框選出現 LGA；請檢查 PCA 座標方向'
print('原始檔案核對：')
verify_or_download()
display(json.loads((ROOT/'output/environment.json').read_text()))
print('重現成功：原始資料、三種策略、20 次熱卡、PCA 與六個互動操作均已重新產生並通過核對。')""")
    nb.cells=cells
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
    if execute:
        os.chdir(ROOT);shell=InteractiveShell.instance();counter=0
        for idx,cell in enumerate(nb.cells):
            if cell.cell_type!='code':continue
            counter+=1;print('Execute cell',counter,'/',sum(c.cell_type=='code' for c in nb.cells),flush=True)
            with capture_output(stdout=True,stderr=True,display=True) as cap:
                result=shell.run_cell(cell.source,store_history=False)
            if result.error_before_exec or result.error_in_exec:raise RuntimeError(f'Notebook cell {counter} failed: {result.error_before_exec or result.error_in_exec}\n{cap.stdout}\n{cap.stderr}')
            outputs=[]
            if cap.stdout:outputs.append(nbf.v4.new_output('stream',name='stdout',text=cap.stdout))
            if cap.stderr:outputs.append(nbf.v4.new_output('stream',name='stderr',text=cap.stderr))
            for rich in cap.outputs:outputs.append(nbf.v4.new_output('display_data',data=rich.data,metadata=rich.metadata))
            cell.outputs=outputs;cell.execution_count=counter
        try:
            from ipywidgets.embed import embed_data
            state=embed_data(views=[shell.user_ns['panel']])
            nb.metadata['widgets']={'application/vnd.jupyter.widget-state+json':state['manager_state']}
        except Exception as e:print('Widget embedding note:',str(e),flush=True)
    md('''## 互動成果的繳交方式

已發布的 dashboard：<https://snazzy-beijinho-a8153e.netlify.app/>。老師公告接受「已發布的 dashboard 連結」**或**「至少五張操作截圖並逐張說明」。可在繳交欄貼上這個連結。

上方六個操作圖是此 notebook 實際執行篩選與矩形框選後產生的分析圖，逐張附有條件和發現；它們不是瀏覽器操作截圖。若老師另外指定必須交真實瀏覽器截圖，再從 dashboard 親自操作與擷取。''')
    nb.cells=cells
    nbf.validate(nb);nbf.write(nb,ROOT/'analysis.ipynb')
    from attach_browser_evidence import attach
    attach()
    print(ROOT/'analysis.ipynb',flush=True)
if __name__=='__main__':build()
