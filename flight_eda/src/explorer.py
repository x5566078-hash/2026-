"""Shared full-data filter / rectangular brushing engine for notebook and snapshots."""
from pathlib import Path
import os,json
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplcache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analysis import pca,scores,VARIABLES,COLORS,dump,SEED

class Explorer:
    def __init__(self):
        self.meta=pd.read_csv(ROOT/'data/derived/eligible_metadata.csv')
        self.data=np.load(ROOT/'data/derived/pca_data.npz')
        raw=json.loads((ROOT/'output/models.json').read_text())
        self.models={k:{a:np.array(b) if isinstance(b,list) else b for a,b in v.items()} for k,v in raw.items()}
        self.arrays={'CCA':self.data['raw'],'MEAN':self.data['mean'],'HOTDECK':self.data['hotdeck']}
        self.score_cache={k:scores(self.models[k],v) for k,v in self.arrays.items()}
        self.log=[]

    def select(self,strategy='HOTDECK',origin='all',carrier='all',month='all',time_band='all',
               rain='all',pressure='all',brush=None,refit=False,record=True):
        m=self.meta;mask=np.ones(len(m),dtype=bool)
        if strategy=='CCA':mask &= self.data['complete']
        for key,value in [('origin',origin),('carrier',carrier),('month',month),('time_band',time_band),('rain_group',rain)]:
            if value!='all':mask &= m[key].astype(str).eq(str(value)).to_numpy()
        if pressure!='all':mask &= m.pressure_missing.eq(pressure=='missing').to_numpy()
        ids=np.flatnonzero(mask);mod=self.models[strategy];sc=self.score_cache[strategy]
        can_refit=len(ids)>=100 and np.all(self.arrays[strategy][ids].std(axis=0)>1e-9)
        did_refit=bool(refit and can_refit)
        refit_note=''
        if refit and not can_refit:
            refit_note='子群少於 100 班或包含常數欄，保留全體模型；沒有悄悄刪除變數。'
        if did_refit:
            mod=pca(self.arrays[strategy][ids],self.models[strategy]);sc=scores(mod,self.arrays[strategy])
        prebrush=ids.copy()
        if brush:
            x0,x1,y0,y1=brush
            keep=(sc[ids,0]>=x0)&(sc[ids,0]<=x1)&(sc[ids,1]>=y0)&(sc[ids,1]<=y1)
            ids=ids[keep]
        x=self.arrays[strategy][ids]
        row={'strategy':strategy,'origin':origin,'carrier':carrier,'month':month,'time_band':time_band,
             'rain':rain,'pressure':pressure,'brush':brush,'refit':did_refit,'refit_requested':refit,'refit_note':refit_note,'n':len(ids),'n_before_brush':len(prebrush),
             'arr_delay_mean':float(np.mean(x[:,1])) if len(x) else None,
             'distance_mean':float(np.mean(x[:,3])) if len(x) else None,
             'air_time_mean':float(np.mean(x[:,2])) if len(x) else None,
             'original_pressure_missing_pct':float(100*m.loc[ids,'pressure_missing'].mean()) if len(ids) else None,
             'airport_counts':m.loc[ids,'origin'].value_counts().to_dict()}
        if record:self.log.append(row)
        airports=[]
        for o in ['EWR','JFK','LGA']:
            q=ids[m.loc[ids,'origin'].to_numpy()==o]
            airports.append({'origin':o,'n':len(q),'arr_delay_mean':float(self.arrays[strategy][q,1].mean()) if len(q) else None})
        return {'ids':ids,'prebrush':prebrush,'scores':sc,'model':mod,'summary':row,'airports':pd.DataFrame(airports)}

    def snapshot(self,result,path,title,caption):
        """Scientific output snapshot, not a fabricated browser screenshot."""
        r=result;s=r['summary'];ids=r['ids'];sc=r['scores'];meta=self.meta
        rng=np.random.default_rng(SEED);show=r['prebrush']
        if len(show)>10000:show=np.sort(rng.choice(show,10000,replace=False))
        fig=plt.figure(figsize=(11.8,7),facecolor='#fafcfc')
        gs=fig.add_gridspec(2,2,left=.07,right=.97,bottom=.10,top=.78,width_ratios=[1.5,1],height_ratios=[1,.58],hspace=.42,wspace=.3)
        ax=fig.add_subplot(gs[0,0]);load=fig.add_subplot(gs[0,1]);bars=fig.add_subplot(gs[1,0]);info=fig.add_subplot(gs[1,1]);info.axis('off')
        fig.text(.055,.955,title,fontsize=18,fontweight='bold',color='#163944')
        filt='  /  '.join(f'{k}={s[k]}' for k in ['strategy','origin','carrier','month','time_band','rain','pressure'] if s[k]!='all')
        fig.text(.055,.913,filt,fontsize=10,color='#4e626a')
        avg='NA' if s['arr_delay_mean'] is None else f"{s['arr_delay_mean']:.2f} min"
        fig.text(.055,.854,f"Matched flights: {s['n']:,}     Mean arrival delay: {avg}     Pressure missing: {s['original_pressure_missing_pct'] or 0:.1f}%",fontsize=12,color='#163944')
        selected=np.isin(show,ids)
        if s['brush']:
            ax.scatter(sc[show[~selected],0],sc[show[~selected],1],s=3,color='#d3dadd',alpha=.2)
            x0,x1,y0,y1=s['brush'];ax.add_patch(matplotlib.patches.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,color='#da8c37',lw=1.6))
        for o,c in zip(['EWR','JFK','LGA'],['#237f8c','#da8c37','#7d63a8']):
            ii=show[selected & meta.loc[show,'origin'].eq(o).to_numpy()]
            ax.scatter(sc[ii,0],sc[ii,1],s=4,alpha=.35,color=c,label=o)
        ax.set(xlabel='PC1 score',ylabel='PC2 score',title='Fixed full-population PCA axes' if not s['refit'] else 'Refitted subgroup PCA axes')
        ax.legend(markerscale=2.5,fontsize=8,loc='upper left');ax.set_xlim(-5,12);ax.set_ylim(-5,9)
        v=r['model']['vectors'];yy=np.arange(len(VARIABLES))
        load.barh(yy-.18,v[:,0],height=.34,color='#237f8c',label='PC1')
        load.barh(yy+.18,v[:,1],height=.34,color='#da8c37',label='PC2')
        load.axvline(0,color='#d7e0e3',lw=.6)
        load.set(yticks=yy,yticklabels=VARIABLES,xlabel='Unit eigenvector coefficient',title='Loadings: PC1 and PC2',xlim=(-.55,.85))
        load.invert_yaxis();load.tick_params(axis='y',labelsize=8);load.legend(fontsize=8,loc='lower right')
        a=r['airports'];means=a.arr_delay_mean.fillna(0)
        bars.bar(a.origin,means,color=['#237f8c','#da8c37','#7d63a8'],width=.55)
        bars.axhline(0,color='gray',lw=.6);bars.set(ylabel='Mean arrival delay (min)',title='Airport summary (all selected flights)')
        lo=min(0,float(means.min()));hi=max(0,float(means.max()));span=max(hi-lo,1)
        bars.set_ylim(lo-.28*span,hi+.32*span)
        for j,row in a.iterrows():
            txt='n=0' if row['n']==0 else f"{row.arr_delay_mean:.2f}\nn={row['n']:,}"
            val=row.arr_delay_mean if pd.notna(row.arr_delay_mean) else 0
            bars.text(j,val,txt,ha='center',va='bottom' if val>=0 else 'top',fontsize=8)
        details=[f"Score points drawn: {len(show):,}",f"Full-data selected n: {len(ids):,}",f"PC1: {100*r['model']['evr'][0]:.2f}%",f"PC2: {100*r['model']['evr'][1]:.2f}%"]
        if s['brush']:details+=['Rectangular brush:',str(s['brush'])]
        info.text(.02,.88,'\n'.join(details),fontsize=11,va='top',linespacing=1.7,color='#425c65')
        fig.text(.055,.035,'Executed filter snapshot | fixed display range; off-frame points retained in full-data statistics',fontsize=9,color='#5d737a')
        for a in [ax,load,bars]:a.spines[['top','right']].set_visible(False)
        fig.savefig(path,dpi=170);plt.close(fig)
        return {'image':str(Path(path).relative_to(ROOT)),'title':title,'caption':caption,**s}

    def widget(self):
        """Live notebook: hover both charts, filter groups, box-select score points.

        Plot displays <=8,000 deterministic sampled points. Box-selection uses its
        geometric boundaries on ALL filtered flights, not just plotted points.
        """
        import ipywidgets as W
        import plotly.graph_objects as go
        from IPython.display import display,clear_output
        controls={
          'strategy':W.Dropdown(options=['HOTDECK','MEAN','CCA'],description='策略'),
          'origin':W.Dropdown(options=['all','EWR','JFK','LGA'],description='機場'),
          'carrier':W.Dropdown(options=['all']+sorted(self.meta.carrier.unique()),description='航空公司'),
          'month':W.Dropdown(options=['all']+list(range(1,13)),description='月份'),
          'time_band':W.Dropdown(options=['all','morning','afternoon','evening','night'],description='時段'),
          'rain':W.Dropdown(options=['all','rain','dry','unknown'],description='原始降雨'),
          'pressure':W.Dropdown(options=['all','missing','observed'],description='原始氣壓'),
          'refit':W.Checkbox(value=False,description='依篩選子群重新估計 PCA')}
        summary=W.HTML();details=W.Output();scatter=go.FigureWidget();loading=go.FigureWidget();current={}
        scatter.add_scattergl(mode='markers',marker={'size':4,'opacity':.5},name='Flights')
        loading.add_scatter(mode='markers+text',textposition='top center',marker={'size':10,'color':'#237f8c'})
        scatter.update_layout(height=420,dragmode='select',template='plotly_white',xaxis_title='PC1',yaxis_title='PC2',margin=dict(t=45,l=45,r=10,b=40))
        loading.update_layout(height=420,template='plotly_white',title='負荷量（單位特徵向量係數）',xaxis_title='PC1',yaxis_title='PC2',margin=dict(t=45,l=45,r=10,b=40))
        def show_result(r):
            s=r['summary'];summary.value=f"<b>全資料篩選後 n={s['n']:,}</b>　平均抵達延誤={s['arr_delay_mean']:.2f} 分鐘" if s['n'] else '<b>這組條件沒有航班</b>'
            if s['refit_note']:summary.value+='<br/>'+s['refit_note']
            with details:
                clear_output(wait=True);display(r['airports'])
        def update(change=None):
            params={k:w.value for k,w in controls.items()};r=self.select(**params);current.update(r)
            ids=r['ids'];rng=np.random.default_rng(SEED)
            if len(ids)>8000:ids=np.sort(rng.choice(ids,8000,replace=False))
            x=self.arrays[params['strategy']][ids];m=self.meta.loc[ids]
            custom=np.c_[m.flight_id,m.origin,m.carrier,m.month,m.day,x[:,1],x[:,3],m.pressure_missing]
            with scatter.batch_update():
                scatter.data[0].x=r['scores'][ids,0];scatter.data[0].y=r['scores'][ids,1];scatter.data[0].customdata=custom
                scatter.data[0].marker.color=m.origin.map({'EWR':'#237f8c','JFK':'#da8c37','LGA':'#7d63a8'}).tolist()
                scatter.data[0].hovertemplate='ID %{customdata[0]} | %{customdata[1]} %{customdata[2]}<br>%{customdata[3]}/%{customdata[4]}<br>抵達延誤 %{customdata[5]:.1f} 分<br>距離 %{customdata[6]:.0f} mi<br>原始氣壓缺失 %{customdata[7]}<extra></extra>'
                scatter.layout.title=f"{'子群重新擬合' if r['summary']['refit'] else '固定全體座標'} | 繪圖 {len(ids):,} 點"
            with loading.batch_update():
                loading.data[0].x=r['model']['vectors'][:,0];loading.data[0].y=r['model']['vectors'][:,1]
                loading.data[0].text=VARIABLES;loading.data[0].customdata=r['model']['loadings'][:,:2]
                loading.data[0].hovertemplate='%{text}<br>係數 PC1=%{x:.3f}, PC2=%{y:.3f}<br>相關負荷量 PC1=%{customdata[0]:.3f}, PC2=%{customdata[1]:.3f}<extra></extra>'
            show_result(r)
        def selected(trace,points,selector):
            if hasattr(selector,'xrange') and selector.xrange is not None:
                params={k:w.value for k,w in controls.items()}
                params['brush']=[min(selector.xrange),max(selector.xrange),min(selector.yrange),max(selector.yrange)]
                show_result(self.select(**params))
        scatter.data[0].on_selection(selected)
        for w in controls.values():w.observe(update,names='value')
        update()
        return W.VBox([W.HTML('<h3>缺失處理 × PCA 互動探索</h3><p>Hover 檢視航班及負荷量；拖曳矩形框選。摘要使用全部符合條件的航班。原始降雨 unknown 保留為 unknown。</p>'),
                       W.HBox(list(controls.values())[:3]),W.HBox(list(controls.values())[3:6]),W.HBox(list(controls.values())[6:]),summary,W.HBox([scatter,loading]),details])

def make_snapshots():
    ex=Explorer();out=ROOT/'output/screenshots';out.mkdir(exist_ok=True)
    specs=[
      ('01_overview',dict(strategy='HOTDECK'),'01 | Mechanism-aware analysis: all eligible flights','選 HOTDECK、所有機場與月份，建立完整適用母體的參考；平均抵達延誤約 6.90 分鐘。PC2 高分方向由航程變數主導。'),
      ('02_complete_cases',dict(strategy='CCA'),'02 | Switch to complete-case analysis','只切換為 CCA，平均延誤降至約 4.76 分鐘，樣本減少 36,206 班；圖形大致相似，卻不能據此認定刪除無影響。'),
      ('03_rain_missing',dict(strategy='HOTDECK',rain='rain',pressure='missing'),'03 | Rainy flights with missing pressure','同時篩選原始降雨大於零及氣壓缺失，檢查完整列刪除會排除的惡劣天氣航班；數值與機場差異由此操作的完整資料輸出記錄。'),
      ('04_carrier_ua',dict(strategy='HOTDECK',carrier='UA'),'04 | Hold carrier fixed: United Airlines','將航空公司固定為 UA，重新比較三座機場。這是條件式描述，不能視為機場效果；航線與出發時段仍可能不同。'),
      ('05_brush_longhaul',dict(strategy='HOTDECK',brush=[-4,4,2,8]),'05 | Brush the high-PC2 region','框選 PC1 在 -4 至 4、PC2 在 2 至 8 的區域，連動查看距離及機場組成，以驗證這群主要反映長程航班，而非直接命名為延誤群。'),
      ('06_subgroup_pca',dict(strategy='HOTDECK',origin='LGA',refit=True),'06 | Refit PCA within LGA','只保留 LGA 並重估 PCA，PC2 的抵達延誤係數由全體的 -0.185 變為 +0.176，溫度由 +0.050 變為 -0.274；距離仍為正向。子群內的軸含義確實改變，不能把不同座標系的點位直接比較。')]
    records=[]
    for key,params,title,caption in specs:
        r=ex.select(**params);records.append(ex.snapshot(r,out/(key+'.png'),title,caption))
        print(key,r['summary'],flush=True)
    dump(out/'operations.json',records);dump(out/'operation_log.json',ex.log)
    return records

if __name__=='__main__':make_snapshots()
