"""Create a self-contained offline Plotly explorer, no CDN or server needed."""
from pathlib import Path
import json,os
ROOT=Path(__file__).resolve().parents[1]
import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs
from explorer import Explorer
from analysis import pca,VARIABLES,SEED,dump

def build():
    ex=Explorer();meta=ex.meta;rng=np.random.default_rng(SEED)
    ids=np.sort(rng.choice(len(meta),18000,replace=False))
    models={}
    for strategy in ['CCA','MEAN','HOTDECK']:
        models[strategy]={'all':ex.models[strategy]}
        for o in ['EWR','JFK','LGA']:
            valid=meta.origin.eq(o).to_numpy()
            if strategy=='CCA':valid &= ex.data['complete']
            models[strategy][o]=pca(ex.arrays[strategy][valid],ex.models[strategy])
    cube=[]
    dims=['origin','carrier','month','time_band','rain_group','pressure_missing']
    for s in ['CCA','MEAN','HOTDECK']:
        mask=ex.data['complete'] if s=='CCA' else np.ones(len(meta),dtype=bool)
        t=meta.loc[mask,dims].copy();t['arr_sum']=ex.arrays[s][mask,1];t['dist_sum']=ex.arrays[s][mask,3]
        t['n']=1;g=t.groupby(dims,observed=True)[['n','arr_sum','dist_sum']].sum().reset_index()
        cube.extend([[s]+list(row) for row in g.itertuples(index=False,name=None)])
    points=[]
    for i in ids:
        m=meta.iloc[i]
        def vals(x):return [None if not np.isfinite(v) else round(float(v),5) for v in x]
        points.append({'id':int(m.flight_id),'o':m.origin,'c':m.carrier,'m':int(m.month),'d':int(m.day),'h':int(m.hour),
            'b':m.time_band,'r':m.rain_group,'p':bool(m.pressure_missing),'ok':bool(ex.data['complete'][i]),
            'raw':vals(ex.arrays['CCA'][i]),'mean':vals(ex.arrays['MEAN'][i,4:]),'hot':vals(ex.arrays['HOTDECK'][i,4:])})
    payload={'variables':VARIABLES,'models':models,'cube':cube,'points':points,
             'operations':json.loads((ROOT/'output/screenshots/operations.json').read_text())}
    out=ROOT/'output/interactive';out.mkdir(exist_ok=True)
    dump(out/'explorer_data.json',payload)
    data=json.loads((out/'explorer_data.json').read_text())
    js=(ROOT/'src/explorer_app.js').read_text()
    html=(ROOT/'src/explorer_template.html').read_text()
    html=html.replace('/*PLOTLY_LIBRARY*/',get_plotlyjs()).replace('/*DATA_PAYLOAD*/',json.dumps(data,ensure_ascii=False,separators=(',',':'))).replace('/*APPLICATION*/',js)
    (out/'flight_explorer.html').write_text(html)
    dump(ROOT/'output/subgroup_models.json',models)
    print('Offline HTML:',out/'flight_explorer.html','bytes:',len(html.encode()))

if __name__=='__main__':build()
