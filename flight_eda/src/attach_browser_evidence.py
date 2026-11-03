"""Attach verified browser captures to an executed notebook, without rerunning analysis."""
from pathlib import Path
import json,base64,nbformat
ROOT=Path(__file__).resolve().parents[1]
TAG='real_browser_evidence'
def attach(path=None):
    path=Path(path or ROOT/'analysis.ipynb')
    manifest=ROOT/'output/browser_screenshots/capture_manifest.json'
    if not manifest.exists():
        print('尚無成功的瀏覽器截圖紀錄；保留既有分析輸出。');return False
    m=json.loads(manifest.read_text())
    assert m.get('passed') and len(m['records'])>=5
    nb=nbformat.read(path,as_version=4)
    nb.cells=[c for c in nb.cells if TAG not in c.metadata.get('tags',[])]
    cells=[]
    def md(s):
        c=nbformat.v4.new_markdown_cell(s);c.metadata['tags']=[TAG];cells.append(c)
    md('## 真實瀏覽器互動紀錄\n以下截圖由 capture_browser.cjs 對本地互動 HTML 實際點選、框選與顯示 hover 後擷取。\n\n擷取時間：'+m['captured_at']+'；瀏覽器：'+m['browser'])
    for r in m['records']:
        p=ROOT/r['image'];assert p.exists()
        c=nbformat.v4.new_markdown_cell('### 操作 '+str(r['step'])+'\n\n**這個操作讓我發現了什麼：** '+r['caption']+'\n\n![真實瀏覽器操作](attachment:browser.png)')
        c.metadata['tags']=[TAG];c.attachments={'browser.png':{'image/png':base64.b64encode(p.read_bytes()).decode()}};cells.append(c)
    nb.cells.extend(cells);nbformat.validate(nb);nbformat.write(nb,path)
    print('已將',len(m['records']),'張截圖放入',path);return True
if __name__=='__main__':attach()
