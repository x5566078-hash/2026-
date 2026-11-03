"""Render the 11-page Chinese report plus complete AI-baseline appendices."""
from pathlib import Path
import json,csv,sys,re,html
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/nycflights_missing_pca_report.pdf'
FONT_CANDIDATES=[ROOT/'assets/NotoSansTC-Regular.ttf',Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),Path('/usr/share/fonts/truetype/arphic/uming.ttc')]
font=next((p for p in FONT_CANDIDATES if p.exists()),None)
if font is None:raise RuntimeError('Chinese font required; set assets/NotoSansTC-Regular.ttf (see README).')
pdfmetrics.registerFont(TTFont('CJK',str(font)))
W,H=595.276,841.89; WIDTH=W-88
INK=colors.HexColor('#153c48');TEAL=colors.HexColor('#237f8c');MUTED=colors.HexColor('#5b7078');PALE=colors.HexColor('#edf5f5');ORANGE=colors.HexColor('#da8c37')
ST={
'title':ParagraphStyle('title',fontName='CJK',fontSize=23,leading=32,textColor=INK,spaceAfter=14,wordWrap='CJK'),
'h1':ParagraphStyle('h1',fontName='CJK',fontSize=16,leading=22,textColor=INK,spaceAfter=12,wordWrap='CJK'),
'h2':ParagraphStyle('h2',fontName='CJK',fontSize=12,leading=18,textColor=TEAL,spaceBefore=8,spaceAfter=5,wordWrap='CJK'),
'body':ParagraphStyle('body',fontName='CJK',fontSize=10,leading=16,spaceAfter=8,wordWrap='CJK'),
'small':ParagraphStyle('small',fontName='CJK',fontSize=8.5,leading=13,textColor=MUTED,spaceAfter=6,wordWrap='CJK'),
'cell':ParagraphStyle('cell',fontName='CJK',fontSize=8.2,leading=12,wordWrap='CJK'),
'tiny':ParagraphStyle('tiny',fontName='CJK',fontSize=6.4,leading=9,wordWrap='CJK'),
'code':ParagraphStyle('code',fontName='CJK',fontSize=8,leading=12,backColor=PALE,borderPadding=7,spaceAfter=8,wordWrap='CJK')}
story=[]
def p(text,kind='body'):return Paragraph(text,ST[kind])
def add(text,kind='body'):story.append(p(text,kind))
def title(text):add(text,'h1')
def image(name,width=WIDTH):
    path=ROOT/name
    from PIL import Image as PILImage
    with PILImage.open(path) as im:iw,ih=im.size
    story.append(Image(str(path),width=width,height=width*ih/iw));story.append(Spacer(1,5))
def table(headers,rows,widths=None,small=False):
    style='tiny' if small else 'cell'
    data=[[p(html.escape(str(v)),style) for v in headers]]+[[p(html.escape(str(v)),style) for v in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('TEXTCOLOR',(0,0),(-1,0),INK),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,TEAL),
        ('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#dce5e8')),('LEFTPADDING',(0,0),(-1,-1),6),
        ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(t);story.append(Spacer(1,8))
def page():story.append(PageBreak())
def read(name):
    with (ROOT/name).open() as f:return list(csv.DictReader(f))
def fmt(x,n=2):
    try:return f'{float(x):,.{n}f}'
    except:return str(x)
def foot(c,doc):
    c.saveState();n=doc.page
    c.setStrokeColor(colors.HexColor('#d8e5e8'));c.line(44,38,W-44,38)
    c.setFont('CJK',8);c.setFillColor(MUTED)
    c.drawString(44,25,'數據探索的統計思維  |  題目 E  |  2013 NYC flights')
    c.drawRightString(W-44,25,f'正文 {n} / 11' if n<=11 else f'附錄 {n-11}')
    c.restoreState()

R=json.loads((ROOT/'output/results.json').read_text())
ops=json.loads((ROOT/'output/screenshots/operations.json').read_text())
S={r['strategy']:r for r in R['strategies']}

# Main page 1
add('被刪掉的航班，會改變<br/>我們看到的準時表現嗎？','title')
add('缺失值處理對紐約航班 PCA 結構的影響','h1')
add('個人探索式資料分析作業  ·  題目 E  ·  資料年度 2013  ·  分析日期 2026-10-26','small')
add('核心回答：會改變資料描述，但在各策略自行標準化後，PC1／PC2 的主要方向大致保留。完整列刪除將平均抵達延誤由 6.90 分鐘降至 4.76 分鐘；前兩軸合計解釋變異約 41%，仍不足以代表整體結構。','h2')
title('1　AI 基準報表（完整內容見附錄 A）')
add('先由 Codex 對原始航班與天氣表產生初版 EDA，保存提示詞、全文、數值表、圖及 SHA-256 封存清單，再進行本報告的機制診斷。這是同一對話中的先後版本比較，AI 已知作業要求與投影片，並非獨立盲測。')
table(['初版做對的事','尚未完成的檢驗'],[
['正確辨識延誤右偏、距離與空中時間高度相關；用標準化數值欄做 PCA。','以完整列當基準，尚未比較被排除航班的天氣、延誤與組成。'],
['指出機場均值未調整，且沒有把取消航班填成零。','沒有診斷氣壓的共同缺失機制，也沒有比較處理策略或座標穩定性。'],
['提醒極端風速需查核、兩個主成分僅涵蓋約 41% 變異。','尚未確認該風速是否與任何航班相配，也未以分層或框選追查分群。']],[WIDTH/2]*2)
add('資料與問題範圍','h2')
add('使用 nycflights13：336,776 班航班與 26,115 筆逐時天氣紀錄。來源為套件原始資料的 Rdatasets CSV 鏡像，完整原檔隨作業提供，並以 Git blob SHA 及 SHA-256 驗證。官方欄位定義見 [1–2]；課堂方法對照見 [3–6]。')
add('PCA 的分析母體限定為四項飛行測量皆可觀測的 327,346 班。這個定義不等同所有排定航班，也不保證涵蓋所有實際飛行；取消或其他不完整紀錄另外描述。全程使用完整資料計算，互動散布圖只為顯示效率抽樣。','small')
page()

# Main page 2
title('2　缺失值診斷：先分清楚缺失從哪裡來')
add('以 origin 與 UTC time_hour 左連接，天氣鍵值唯一，合併後仍為 336,776 列。1,556 班對不到天氣（108 個機場時點），這些列予以保留。下表的「天氣原缺」以時點計；「合併後」以航班計，不能直接相加或比較為同一母體。')
missing=read('output/tables/missing_provenance.csv')
table(['變數','原表缺失數','原表單位','合併後缺失數','占全部航班'],[
 [r['variable'],fmt(r['source_missing_n'],0),'航班' if r['source_unit']=='flight' else '機場時點',fmt(r['joined_original_missing_n'],0),fmt(float(r['joined_original_missing_n'])/336776*100,3)+'%'] for r in missing],
 [88,89,85,125,WIDTH-387])
image('output/figures/missingness.png')
add('圖 1　左：依機場與時間排序後等距抽取 2,000 班的缺失矩陣。右：全部航班的二元缺失指標相關（phi）；distance 無缺失，故其相關未定義。共同缺失計數及所有缺失模式另存 CSV，避免只靠抽樣圖判斷。','small')
page()

# Main page 3
title('2.1　氣壓缺失與惡劣天氣相伴')
table(['逐時天氣群體','時點數','有降雨比例','平均濕度','平均能見度'],[
 ['氣壓有觀測','23,386','3.49%','59.77%','9.55 mi'],
 ['氣壓缺失','2,729','34.15%','86.22%','6.73 mi']], [116,76,100,100,WIDTH-392])
add('氣壓缺失群的濕度標準化差異 SMD=1.77，能見度 SMD=-1.04，露點 SMD=0.58；溫度則僅 0.02。缺失並非對所有變數都同樣有關，不能只寫「資料不隨機」而不指出關聯方向。')
image('output/figures/missing_group_ecdf.png')
add('圖 2　以適用航班為單位的經驗累積分布；延誤圖僅縮放顯示範圍，統計仍保留所有值。天氣重複對應多班航班，因此這裡是航班加權的描述，並非獨立天氣樣本的檢定。','small')
add('缺失可預測，仍不能證明 MAR','h2')
add('另在原始逐時天氣表建立「氣壓是否缺失」的邏輯斯模型，使用機場、月份、時刻、溫度、露點、濕度、風速、降水及能見度。按曆日分組的五折驗證 AUC 平均 0.925（各折 0.921–0.929）。這提供反對簡單 MCAR 解釋的證據，但不能區分 MAR 與依賴未觀測氣壓的 MNAR。')
add('被排除的航班有哪些差異？','h2')
add('在 327,346 班適用航班中，天氣有缺值的 36,206 班平均抵達延誤 24.07 分鐘，天氣完整群為 4.76 分鐘。出發紀錄缺失群的平均距離 695 英里，已有出發紀錄群為 1,049 英里；前者的平均預定出發時刻也較晚。這些資料差異使直接刪除需要額外理由。')
page()

# Main page 4
title('2.2　逐項機制判斷與分析母體')
table(['變數／缺失來源','證據','判斷與處理'],[
 ['dep_delay：8,255 班無出發時間','缺失與 dep_time 同現；短程、較晚時段及機場比例不同。','以「無出發紀錄／取消代理」記錄；對未實際出發的延誤屬結構性不適用。沒有正式取消旗標，故不把所有案例斷言為已確認取消。'],
 ['arr_delay、air_time：各 9,430','含前述 8,255 班，另有 1,175 班已有出發但飛行資訊不完整；後者平均出發延誤 36.02 分鐘。','可能含轉降、未完成或未回報；資料不足以辨識，保留「其他不完整」而不武斷標成 MAR。主 PCA 不插補，結論限定於適用母體。'],
 ['pressure：原表 2,729 時點','缺失群降雨 34.15%、濕度高、能見度低；分組驗證 AUC 0.925。','條件式 MAR 作工作假設；給定可觀測天氣及時間找供體。MNAR 仍可能，不能將插補後資料視為已找回真值。'],
 ['temp/dewp/humid 各 1；wind_speed 4 時點','前三者同時缺；樣本太少，無法可靠辨認原因。另有 1 筆 >100 mph 的品質旗標。','測量／紀錄遺漏原因未明，不足以確認 MCAR。採相同條件供體；異常原值保留在原檔，分析副本設缺。'],
 ['weather 合併未配對：1,556 班','對應 108 個缺少天氣的時點；12 月占 932 班，且鍵值及時區已核對。','是資料覆蓋缺口，非「天氣不適用」。可依機場、月份、時刻作近似插補，但實際天氣不可辨識；另做排除未配對時點的敏感度。'],
 ['distance；precip、visib 原始表','distance 完整；precip、visib 原始逐時表沒有 NA。','後兩欄合併後的 1,556 個 NA 全來自未配對，不應另宣稱雨量感測器遺漏。']],[102,169,WIDTH-271])
add('母體流程：336,776 → 排除 8,255 無出發紀錄與 1,175 其他不完整 → 327,346 適用航班。三種策略都以這個母體為出發點；CCA 再保留 291,140 個完整個案。排除前兩類是因分析變數的適用性與可辨識性，不是直接刪除所有含 NA 的列。','small')
add('品質查核：1,048.36 mph 出現在 EWR 2013-02-12 03:00 當地時間，沒有任何航班用此時點合併。保留原值的完整個案 PCA 與主分析 CCA 相同；熱卡法仍將此時點排除出完整供體，不能將 CCA 的查核擴大為所有插補流程都完全不受影響。','small')
page()

# Main page 5
title('3　缺失處理的敏感度分析')
table(['策略','如何執行／假設'],[
 ['CCA 完整個案','在適用母體內刪除 11 個分析變數仍有缺失的列。作為常見基準，並檢查被排除群體。'],
 ['MEAN 平均數','在「逐時天氣」層級用各欄觀測均值補缺，再合併航班。同一時點使用同一補值；刻意作簡單對照，並非推薦最終方法。'],
 ['HOTDECK 條件式熱卡','在同機場、同當地月份內，按觀測天氣的標準化距離、日序／7、循環時刻找最近 5 個天氣完整供體，隨機抽 1 個，僅複製缺失欄。全時點缺失時只有時間特徵可用。重複 20 次，seed=20261026…20261045。']],[105,WIDTH-105])
add('三種策略使用同一組 11 個連續變數，同樣不替取消或不適用的飛行紀錄創造延誤。HOTDECK 是條件供體法，不冒稱 MICE／PMM，也不將其重複抽樣當成正式多重插補後驗分布。')
table(['策略','樣本數','抵達延誤均值','延誤 SD','氣壓均值','氣壓 SD'],[
 [k,fmt(S[k]['n'],0),fmt(S[k]['arr_delay_mean']),fmt(S[k]['arr_delay_sd']),fmt(S[k]['pressure_mean']),fmt(S[k]['pressure_sd'])] for k in ['CCA','MEAN','HOTDECK']],
 [73,80,100,78,91,WIDTH-422])
table(['策略','平均濕度','平均能見度','補值後降雨>0 比例'],[
 [k,fmt(S[k]['humid_mean'])+'%',fmt(S[k]['visib_mean'])+' mi',fmt(S[k]['rain_pct'])+'%'] for k in ['CCA','MEAN','HOTDECK']], [85,110,120,WIDTH-315])
add('CCA 的平均抵達延誤低 2.14 分鐘（約 31%），這是刪除後樣本組成改變；MEAN 與 HOTDECK 延誤相同，因本研究只插補天氣。平均數補值壓縮氣壓變異，也會把整筆未配對時點的雨量補成小正值，因此「補值後有雨比例」不可當成觀測到的降雨事實。')
add('插補檢核與限制','h2')
add('在原本天氣完整的 1,500 個時點隨機遮蔽氣壓，條件熱卡 RMSE=5.04 hPa、MAE=2.96，平均數法分別為 7.27、5.85。這只驗證可觀測群中的壓力補值表現，不能驗證真正缺失群的 MAR，也不能代表整段未配對天氣的重建能力。')
page()

# Main page 6
title('4　PCA：尺度、成分數與詮釋')
add('PCA 僅使用 dep_delay、arr_delay、air_time、distance、temp、dewp、humid、wind_speed、precip、visib、pressure。機場、航空公司、目的地、月份、時段、星期、季節與原始降雨類別共八項類別資訊，用於分群及互動，沒有把代碼當連續變數。')
add('主分析在每個策略的分析資料中逐欄中心化，並除以該策略標準差。分鐘、英里、華氏度、百分比及氣壓量綱不同，因此使用相當於相關矩陣的 PCA。此選擇也會重新放大補值後縮小的變異；第 4.1 節另固定尺度檢查其影響。')
image('output/figures/scree.png')
add('圖 3　三策略的碎石圖與累積解釋變異。事先以「累積至少 80%」作主要保留準則，均需要 5 個成分；碎石圖沒有強到足以只保留兩個的單一轉折。PC1／PC2 用來互動顯示，並非宣稱二維足夠。','small')
table(['主成分','HOTDECK 的主要係數','審慎命名'],[
 ['PC1（22.87%）','露點 +0.493、濕度 +0.420、溫度 +0.354；兩種延誤約 +0.33、能見度 -0.301。','暖濕／低能見度與延誤的混合軸；不可視為純天氣因子。'],
 ['PC2（18.32%）','距離 +0.679、空中時間 +0.673；兩種延誤為小幅負向。','航程軸；需用框選後原始距離與機場組成驗證。'],
 ['PC3','抵達延誤 +0.507、出發延誤 +0.496，溫度 -0.427、露點 -0.397。','延誤相對於暖濕程度的對比軸，不等於單一延誤指數。']],[82,235,WIDTH-317])
add('表中「係數」定義為單位長度的特徵向量。相關負荷量另以係數 × √特徵值計算，完整 11 個成分兩種定義都保存在 pca_loadings.csv；避免將係數與變數-PC相關混為一談。','small')
page()

# Main page 7
title('4.1　PC1／PC2 穩定嗎？答案取決於比較條件')
table(['策略','PC1／PC2 變異%','方向餘弦 PC1／PC2','共同航班分數 r','前兩軸最大角度'],[
 ['CCA','22.38 / 18.32','1.000 / 1.000','1.000 / 1.000','0°'],
 ['MEAN','22.55 / 18.32','0.992 / 0.999','0.996 / 0.999','6.96°'],
 ['HOTDECK','22.87 / 18.32','0.991 / 0.999','0.996 / 0.999','7.70°']], [66,109,120,113,WIDTH-408])
add('相對 CCA，比較前先對齊正負號。分數相關只在同一批 291,140 班共同完整航班上計算，避免把樣本改變誤判為分數改變。另比較子空間主角度，並檢查前三軸配對；本次沒有前三軸順序互換。')
image('output/figures/loading_comparison.png')
add('圖 4　整體係數方向相近，但 PC1 的延誤、雨量權重提高，溫度／露點權重下降。HOTDECK 的 20 次抽取中，PC1 解釋變異範圍 22.827–22.886%，PC2 18.322–18.325%，前兩軸最大角度 7.49–7.70°；這是供體隨機性的範圍，不是信賴區間。','small')
add('固定尺度檢查：不能把「大致穩定」說成完全不受影響','h2')
add('若各策略都固定使用第一份 HOTDECK 的標準差，再各自中心化做 PCA，HOTDECK 與 CCA 的 PC1 餘弦降至 0.917、前兩軸最大角度增至 23.74°。因此主分析的相似性，部分依賴每個策略重新標準化。穩健的說法是：航程結構較穩定，PC1 的混合權重與尺度選擇較敏感。')
add('另排除未配對天氣的 1,527 班適用航班，與 HOTDECK 全體相比的前兩軸角度僅 0.22°。這顯示本資料的主要選擇差異來自氣壓缺失相關時段，並不表示其他年份的合併缺口一定可忽略。','small')
page()

def op_panel(i,caption):
    image(ops[i]['image'],width=460)
    add(caption,'small')

# Main page 8
title('4.2　互動探索紀錄：切換處理策略')
add('下列為實際執行篩選／矩形框選程式後保存的輸出快照，並非偽造的瀏覽器螢幕截圖。完整條件與結果已寫入 notebook 及 operations.json；可在 live widget 或離線 HTML 重做。','small')
op_panel(0,'操作 1：選 HOTDECK、全體機場及月份。發現：327,346 班的平均抵達延誤 6.90 分鐘；三座機場在 PCA 上大量重疊，不能把機場標籤當成自然分群。')
op_panel(1,'操作 2：只將策略切到 CCA。發現：樣本少了 36,206 班、平均延誤降到 4.76 分鐘，散布圖卻仍相似。PCA 結構的穩定不能取代樣本選擇診斷。')
page()

# Main page 9
title('4.3　互動探索紀錄：追查被刪除的群體')
op_panel(2,'操作 3：HOTDECK → 原始降雨 rain → 原始氣壓 missing。發現：11,915 班平均抵達延誤 39.18 分鐘，這整群會被 CCA 排除。這是本次透過交叉篩選定位的關鍵群體；它的延誤為原始觀測值，並非插補製造。')
op_panel(3,'操作 4：將航空公司固定為 UA。發現：剩下 57,782 班，平均距離升到 1,531 英里，EWR 占 45,501 班，JFK 只有 4,478 班。航空公司分布明顯不平衡，機場總均值不能直接當作公平比較。')
page()

# Main page 10
title('4.4　互動探索紀錄：驗證軸的意義')
op_panel(4,'操作 5：固定全體 PCA，矩形框選 PC1∈[-4,4]、PC2∈[2,8]。發現：47,477 班平均距離 2,479 英里、平均抵達延誤 -5.04 分鐘；JFK 30,262 班、EWR 17,215 班，沒有 LGA。高 PC2 的分群主要是航程，不是延誤。框選摘要由全資料計算。')
op_panel(5,'操作 6：選 LGA，開啟子群 PCA 重估。發現：PC2 的抵達延誤係數由 -0.185 變為 +0.176，溫度由 +0.050 變為 -0.274，而距離仍正向。這不是整軸符號翻轉，子群的混合意義確實改變；不能把不同座標系的點位直接比較。')
page()

# Main page 11
title('5　反思')
reflection=(ROOT/'docs/reflection.txt').read_text().strip()
count=len(re.findall(r'[\u4e00-\u9fff]',reflection))
assert 600<=count<=900,('Reflection Chinese characters',count)
add(f'約 {count} 個中文字；本段為 AI 協助起草，應由繳交者依本人理解審閱。','small')
for para in reflection.split('\n\n'):add(html.escape(para),'body')
add('參考資料與重現入口','h2')
add('[1] nycflights13 flights：<link href="https://nycflights13.tidyverse.org/reference/flights.html" color="#237f8c">官方欄位說明</link>。 [2] weather：<link href="https://nycflights13.tidyverse.org/reference/weather.html" color="#237f8c">官方欄位說明</link>。<br/>[3] 課堂 w06，p.18–23、27–31、37：缺失機制、熱卡與插補模型。 [4] w05，p.7–9、16–20：標準化與 PCA。 [5] w02，p.3–4：互動探索。 [6] w03，p.4–6：合併；w08，p.16–20：條件比較。<br/>原始資料、程式、完整數值與操作紀錄見隨附 flight_eda 資料夾。先讀 README，再開 analysis.ipynb 或離線互動檔。','small')
page()

# Appendices, excluded from the 11-page body.
title('附錄 A　AI 初版提示詞、完整輸出及封存說明')
add('以下原樣保留本次初版任務提示與 AI 輸出。只做排版，不事後修改初版結論；數值表按閱讀精度顯示，完整精度的 CSV／JSON 同包提供。封存清單為 baseline/frozen_manifest.json。','small')
add('完整提示詞','h2')
for para in (ROOT/'baseline/prompt.txt').read_text().split('\n\n'):add(html.escape(para).replace('\n','<br/>'))
add('完整 AI 文字輸出','h2')
for para in (ROOT/'baseline/ai_output.txt').read_text().split('\n\n'):add(html.escape(para).replace('\n','<br/>'))
page()
title('附錄 A.1　AI 初版完整描述統計')
desc=read('baseline/descriptive.csv');first=list(desc[0])[0]
table(['變數','n','mean','sd','min','1%'],[[r[first]]+[fmt(r[c],0 if c=='count' else 3) for c in ['count','mean','std','min','1%']] for r in desc], [84,75,88,88,86,WIDTH-421])
table(['變數','25%','50%','75%','99%','max'],[[r[first]]+[fmt(r[c],3) for c in ['25%','50%','75%','99%','max']] for r in desc],[84]+[(WIDTH-84)/5]*5)
table(['機場','航班總數','平均抵達延誤','中位數抵達延誤','平均出發延誤'],[[r['origin'],fmt(r['n'],0),fmt(r['arr_delay_mean'],4),fmt(r['arr_delay_median'],1),fmt(r['dep_delay_mean'],4)] for r in read('baseline/airports.csv')],[65,85,120,120,WIDTH-390])
add('注意：機場表的航班總數包含缺失；平均數僅使用該欄可用觀測。文字初版已另外提供抵達延誤的有效樣本數。','small')
page()
title('附錄 A.2　AI 初版缺失與圖形')
bmiss=read('baseline/missing.csv');first=list(bmiss[0])[0]
table(['變數','缺失數','缺失比例%'],[[r[first],fmt(r['missing_n'],0),fmt(r['missing_pct'],4)] for r in bmiss],[WIDTH/3]*3)
image('baseline/baseline_distributions.png')
image('baseline/baseline_pca.png')
page()
title('附錄 A.3　AI 初版完整相關矩陣與 PCA')
for filename,label in [('correlations.csv','Pearson 成對可用觀測相關'),('pca_vectors.csv','11 個主成分的單位特徵向量係數')]:
    add(label,'h2');data=read('baseline/'+filename);cols=list(data[0]);first=cols[0]
    short={'dep_delay':'dep_dly','arr_delay':'arr_dly','air_time':'air_tm','wind_speed':'wind','pressure':'press'}
    headers=['變數']+[short.get(c,c) for c in cols[1:]]
    table(headers,[[r[first]]+[fmt(r[c],3) for c in cols[1:]] for r in data], [78]+[(WIDTH-78)/11]*11,small=True)
    if filename=='correlations.csv':add('欄名縮寫：dep_dly=dep_delay，arr_dly=arr_delay，air_tm=air_time，wind=wind_speed，press=pressure；橫列保留完整名稱。','small')
stats=json.loads((ROOT/'baseline/statistics.json').read_text())
add('完整解釋變異比例：'+', '.join(f'PC{i+1}={v:.9f}' for i,v in enumerate(stats['explained_variance'])),'small')
add('初版 PC2 方向與正文顯示相反，因 PCA 正負號任意；正式比較已對齊。這不是結果翻轉。','small')
page()
title('附錄 B　補充敏感度與機場分層')
add('同時固定航空公司、月份與時段的共同組成','h2')
add('保留三機場各至少 20 班的 carrier×month×time_band 格子，共 266 格。使用共同母體的合併格子比例作權重，各機場加權平均。這是描述性直接標準化，不包含航線、目的地及所有天氣，不能作因果推論。')
std=read('output/tables/airport_standardized.csv')
table(['機場','共同母體 n','涵蓋適用航班%','未調整均值','標準化均值'],[[r['origin'],fmt(r['size'],0),fmt(r['eligible_coverage_pct']),fmt(r['common_unadjusted']),fmt(r['standardized_mean'])] for r in std],[63,98,118,112,WIDTH-391])
add('共同母體的未調整排名是 LGA 略優於 JFK；按共同格子權重標準化後，JFK 優於 LGA。這和全部航班的排名不是同一母體，不能稱為「機場真實排名翻轉」。EWR 在此比較仍有較高平均延誤。')
add('直接刪除對三機場的方向','h2')
table(['機場','適用母體平均延誤','CCA 平均延誤','變化（分）'],[
['EWR','9.107','7.033','-2.075'],['JFK','5.551','3.288','-2.263'],['LGA','5.783','3.744','-2.040']],[70,155,145,WIDTH-370])
add('三座機場都被描繪得更準時；本資料直接刪除沒有改變 JFK、LGA、EWR 的總均值排序，JFK 的平均數改善幅度略大。無出發紀錄率則 EWR=2.68%、JFK=1.67%、LGA=3.01%；不把它混進平均延誤，但應在旅行可靠度評價中另報。')
add('其他檢核','h2')
extra=read('output/tables/additional_sensitivity.csv')
table(['檢核','策略','PC1 餘弦','PC2 餘弦','前兩軸角度'],[[r['check'],r['strategy'],fmt(r['pc1_cosine'],4),fmt(r['pc2_cosine'],4),fmt(r['top2_max_angle_deg'])+'°'] for r in extra],[170,66,89,89,WIDTH-414])
page()
title('附錄 C　可重現性、操作紀錄與限制')
add('原始來源與固定版本','h2')
add('Rdatasets / nycflights13（公開 CSV 鏡像）：<br/>flights Git blob: d72630cde3a70916b6f8ed76c18725722a110c3d<br/>weather Git blob: a0d79ac1a1739826c7c36b8937f0ccec49d6476f<br/>原檔 data/raw/*.csv 隨包提供；download_data.py 可按固定 blob 重新取得並驗證 SHA-256。未覆寫原始測量。','small')
add('重跑順序','h2')
add('python src/analysis.py<br/>python src/explorer.py<br/>python src/build_interactive.py<br/>python src/build_notebook.py<br/>python src/build_report.py','code')
add('Notebook 收錄從原始資料讀入到表、圖、PCA 與六個操作紀錄的程式入口。互動 widget 提供 hover、機場／航空公司／月份／時段／原始天氣篩選、矩形框選與子群 PCA；離線 HTML 提供不需 Python 的探索入口。資料來源、單位與環境版本另存 manifest 及 environment.json。')
add('六張圖的證據形式','h2')
capture_path=ROOT/'output/browser_screenshots/capture_manifest.json'
capture=json.loads(capture_path.read_text()) if capture_path.exists() else {}
publication_path=ROOT/'docs/dashboard_publication.json'
publication=json.loads(publication_path.read_text()) if publication_path.exists() else {}
if capture.get('passed'):
    add('正文六張 PNG 是篩選與幾何框選後的分析輸出快照。另已實際操作瀏覽器，保存六步篩選／框選及兩個 hover 畫面，原始截圖與條件見 output/browser_screenshots，並附入 notebook。兩種證據形式分開標示。')
elif publication.get('published'):
    add('正文六張 PNG 是篩選及幾何框選後的分析輸出快照，不是瀏覽器螢幕截圖。互動儀表板已發布：<link href="'+html.escape(publication['url'],quote=True)+'">'+html.escape(publication['url'])+'</link>。2026-11-01 使用者提供 Safari 私密瀏覽畫面，顯示公開首頁及全體樣本數 327,346、平均抵達延誤 6.90 分；截圖保存在 output/publication。此證據確認首頁可開啟，尚未對 hover 與手動框選做瀏覽器視覺驗證。')
else:
    add('正文六張 PNG 是篩選及幾何框選後的分析輸出快照。瀏覽器程序受環境限制，尚無真實 UI 截圖；網站原始碼推送也受 DNS 限制，尚未發佈。已提供「完成互動截圖.command」：在一般桌面環境執行，實際切換六步、拖曳框選及顯示 hover，成功後自動把八張截圖與發現附入 notebook。成功前不把現有分析圖當作螢幕截圖。')
add('推論界線','h2')
add('本研究為 2013 年紐約出發航班的描述性探索；沒有對機場、天氣與延誤做因果推論。沒有對重複天氣時點套用獨立樣本 p 值。條件熱卡的遮蔽驗證僅針對原本可觀測的氣壓；20 次供體抽取不代表正式後驗或抽樣信賴區間。PCA 的結果不外推到取消或其他不完整飛行紀錄。')
add('AI 使用揭露','h2')
add('資料取得、程式、初版與正式報告草稿由 Codex 協助；AI 基準不是另一個獨立對話。六個操作紀錄由程式實際執行，未聲稱繳交者本人已完成操作。繳交者應重跑並核對內容、確認反思符合自己的理解。')

OUT.parent.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(OUT),pagesize=(W,H),leftMargin=44,rightMargin=44,topMargin=39,bottomMargin=51,
                      title='被刪掉的航班，會改變我們看到的準時表現嗎？',author='個人作業；Codex 協助草擬')
doc.build(story,onFirstPage=foot,onLaterPages=foot)
print(OUT)
print('Reflection Chinese characters:',count)
