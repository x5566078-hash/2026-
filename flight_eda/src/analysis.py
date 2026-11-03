"""題目 E：缺失值處理會不會改變 PCA 結構？

先封存 baseline/ai_output.txt，再執行本程式。原始 CSV 已隨專案提供，不需網路。
正式統計與 PCA 都使用完整分析母體；互動圖的抽樣只影響畫面顯示。
"""
from pathlib import Path
import os, json, hashlib, platform, sys, argparse
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplcache'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.linalg import subspace_angles
from scipy.optimize import linear_sum_assignment
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from baseline import load_data, FLIGHT, WEATHER, VARIABLES

SEED=20261026
TABLES=ROOT/'output/tables';FIG=ROOT/'output/figures'
COLORS={'CCA':'#237f8c','MEAN':'#da8c37','HOTDECK':'#7d63a8'}

def dump(path,obj):
    def clean(x):
        if isinstance(x,(np.bool_,)):return bool(x)
        if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
        if isinstance(x,(np.integer,)):return int(x)
        if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
        if isinstance(x,(pd.Timestamp,)):return x.isoformat()
        return x
    Path(path).write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2))

def table(name,data,index=False):
    data.to_csv(TABLES/(name+'.csv'),index=index)

def pca(x,reference=None,fixed_scale=None):
    """先中心化、標準化，再以共變異矩陣的特徵分解求主成分。"""
    x=np.asarray(x,dtype=float)
    mu=x.mean(axis=0);sd=x.std(axis=0) if fixed_scale is None else fixed_scale
    assert np.isfinite(x).all() and (sd>0).all()
    z=(x-mu)/sd
    cov=z.T@z/len(z)
    eig,v=np.linalg.eigh(cov);order=np.argsort(eig)[::-1];eig=eig[order];v=v[:,order]
    if reference is not None:
        signs=np.sign(np.sum(v*reference['vectors'],axis=0)); signs[signs==0]=1;v*=signs
    else:
        for k in range(v.shape[1]):
            # PCA 軸的正負號本來可任意翻轉；固定方向只為了讓表格與圖能重現。
            if v[np.argmax(abs(v[:,k])),k]<0:v[:,k]*=-1
    return {'n':len(x),'mean':mu,'scale':sd,'eigenvalues':eig,'evr':eig/eig.sum(),
            'vectors':v,'loadings':v*np.sqrt(eig)}

def scores(model,x):return (np.asarray(x)-model['mean'])/model['scale']@model['vectors']

def stability(ref,model,xcommon):
    """在相同的完整航班上比較分數，避免把樣本改變誤當成座標改變。"""
    a=scores(ref,xcommon); b=scores(model,xcommon)
    match=linear_sum_assignment(-abs(ref['vectors'][:,:3].T@model['vectors'][:,:3]))
    return {'pc1_cosine':abs(np.dot(ref['vectors'][:,0],model['vectors'][:,0])),
            'pc2_cosine':abs(np.dot(ref['vectors'][:,1],model['vectors'][:,1])),
            'pc1_score_r':abs(np.corrcoef(a[:,0],b[:,0])[0,1]),
            'pc2_score_r':abs(np.corrcoef(a[:,1],b[:,1])[0,1]),
            'top2_max_angle_deg':np.degrees(subspace_angles(ref['vectors'][:,:2],model['vectors'][:,:2])).max(),
            'top3_max_angle_deg':np.degrees(subspace_angles(ref['vectors'][:,:3],model['vectors'][:,:3])).max(),
            'top3_axis_matching':','.join(str(i+1) for i in match[1])}

def candidate_donors(hourly,k=5):
    """熱卡候選：同機場、同當地月份中，找 5 個最相近的完整天氣時點。

    距離使用仍有觀測值的天氣欄、月內日期與循環小時；整筆天氣都未配對時，
    只能使用時間資訊。抽取整筆供體，但只複製缺失欄，原有觀測值不改動。
    這是條件式熱卡，並非 MICE／PMM，也不能把 20 次抽樣當信賴區間。
    """
    x=hourly[WEATHER].to_numpy(float)
    observed=np.isfinite(x);complete=observed.all(axis=1)
    local=hourly.time_hour.dt.tz_convert('America/New_York')
    h=local.dt.hour.to_numpy(); day=local.dt.day.to_numpy()
    aux=np.c_[day/7, np.sin(2*np.pi*h/24), np.cos(2*np.pi*h/24)]
    sd=np.nanstd(x,axis=0); mu=np.nanmean(x,axis=0)
    scaled=(x-mu)/sd
    candidates=np.full((len(x),k),-1,dtype=int)
    origins=hourly.origin.to_numpy();month=local.dt.month.to_numpy()
    audit=[]
    for origin in sorted(hourly.origin.unique()):
        for mo in range(1,13):
            grp=(origins==origin)&(month==mo)
            donors=np.flatnonzero(grp&complete);recipients=np.flatnonzero(grp&~complete)
            if not len(recipients):continue
            assert len(donors)>=k,(origin,mo,len(donors))
            patterns=np.unique(observed[recipients],axis=0)
            for pat in patterns:
                ids=recipients[(observed[recipients]==pat).all(axis=1)]
                features=np.c_[aux,scaled[:,pat]]
                tree=cKDTree(features[donors]);dist,idx=tree.query(features[ids],k=k)
                candidates[ids]=donors[idx]
                audit.append({'origin':origin,'month':mo,'missing_variables':','.join(np.array(WEATHER)[~pat]),
                              'recipients':len(ids),'donor_pool':len(donors),
                              'nearest_distance_median':float(np.median(dist[:,0]))})
    assert (candidates[~complete]>=0).all()
    return candidates, pd.DataFrame(audit)

def hotdeck(hourly,candidates,seed):
    """每個天氣時點只抽一次供體，之後再對應到同時點的所有航班。"""
    x=hourly[WEATHER].to_numpy(float).copy();miss=~np.isfinite(x);rows=np.flatnonzero(miss.any(axis=1))
    rng=np.random.default_rng(seed);chosen=candidates[rows,rng.integers(candidates.shape[1],size=len(rows))]
    x[rows]=np.where(miss[rows],x[chosen],x[rows])
    assert np.isfinite(x).all()
    return x,chosen

def prepare():
    """保留原始表，另建立品質檢查後的天氣表與左連接分析表。"""
    f,w,raw=load_data()
    # 風速 >100 mph 的可疑值只在分析副本標成缺失；原始 CSV 不修改。
    wclean=w.copy();wclean['wind_qc']=wclean.wind_speed.gt(100)
    wclean.loc[wclean.wind_qc,'wind_speed']=np.nan
    keys=pd.concat([w[['origin','time_hour']],f[['origin','time_hour']]]).drop_duplicates()
    hourly=keys.merge(wclean[['origin','time_hour','weather_id','wind_qc']+WEATHER],on=['origin','time_hour'],how='left',validate='one_to_one')
    hourly=hourly.sort_values(['origin','time_hour']).reset_index(drop=True)
    hourly['hour_id']=np.arange(len(hourly));hourly['unmatched']=hourly.weather_id.isna()
    hourly['wind_qc']=hourly.wind_qc.fillna(False).astype(bool)
    d=f.merge(hourly,on=['origin','time_hour'],how='left',validate='many_to_one')
    # 未出發與其他飛行測量不完整的航班不適合估計同一組 PCA 變數。
    # 不把取消代理航班的延誤補成 0，也不虛構其抵達延誤。
    d['eligible']=d[FLIGHT].notna().all(axis=1)
    d['status']=np.select([d.dep_time.isna(),~d.eligible],['no_departure','other_incomplete'],default='eligible')
    d['weather_missing']=d[WEATHER].isna().any(axis=1)
    d['pressure_missing']=d.pressure.isna()
    d['time_band']=pd.cut(d.hour,bins=[-1,5,11,17,23],labels=['night','morning','afternoon','evening']).astype(str)
    d['weekday']=pd.to_datetime(d[['year','month','day']]).dt.dayofweek
    d['season']=d.month.map({12:'winter',1:'winter',2:'winter',3:'spring',4:'spring',5:'spring',6:'summer',7:'summer',8:'summer',9:'autumn',10:'autumn',11:'autumn'})
    d['rain_group']=np.where(d.precip.isna(),'unknown',np.where(d.precip.gt(0),'rain','dry'))
    d['visibility_group']=np.where(d.visib.isna(),'unknown',np.where(d.visib.lt(5),'low','normal'))
    return f,w,raw,wclean,hourly,d

def diagnostics(f,w,raw,wclean,hourly,d):
    """分開記錄原表缺失、合併未配對及品質標記造成的缺失。"""
    rows=[]
    for c in VARIABLES:
        original=int(f[c].isna().sum()) if c in FLIGHT else int(w[c].isna().sum())
        rows.append({'variable':c,'source_unit':'flight' if c in FLIGHT else 'station_hour',
          'source_missing_n':original,'source_n':len(f) if c in FLIGHT else len(w),
          'joined_original_missing_n':int(raw[c].isna().sum()),
          'unmatched_contribution_n':0 if c in FLIGHT else int(d.unmatched.sum()),
          'qc_added_missing_n':int(d.wind_qc.sum()) if c=='wind_speed' else 0,
          'analysis_missing_n':int(d[c].isna().sum()),'analysis_missing_pct':100*d[c].isna().mean()})
    table('missing_provenance',pd.DataFrame(rows))
    m=d[VARIABLES].isna().astype(int)
    com=m.T@m;table('comissing_counts',com,True);table('comissing_phi',m.corr(),True)
    table('missing_patterns',m.value_counts().rename('n').reset_index())
    table('flight_status',d.groupby('status').size().rename('n').reset_index())
    table('unmatched_by_month',d.groupby(['origin','month']).agg(n=('flight_id','size'),unmatched_n=('unmatched','sum')).reset_index())
    table('unmatched_hours',hourly.loc[hourly.unmatched,['origin','time_hour']])
    table('quality_flags',w.loc[w.wind_speed.gt(100),['origin','time_hour','wind_speed']])
    groups=[]
    for name,mask,unit,data,cols in [
        ('pressure',wclean.pressure.isna(),'station_hour',wclean,['temp','dewp','humid','wind_speed','precip','visib']),
        ('no_departure',d.dep_time.isna(),'flight',d,['distance','hour']),
        ('other_incomplete',d.status.eq('other_incomplete'),'departed_flight',d.loc[d.dep_time.notna()],['distance','hour','dep_delay']),
        ('any_weather',d.weather_missing,'eligible_flight',d.loc[d.eligible],['distance','hour','dep_delay','arr_delay']),
        ('unmatched',d.unmatched,'flight',d,['distance','hour','dep_delay','arr_delay'])]:
        mask=mask.reindex(data.index)
        for c in cols:
            a=data.loc[mask,c].dropna();b=data.loc[~mask,c].dropna()
            denom=np.sqrt((a.var()+b.var())/2)
            groups.append({'missing_indicator':name,'unit':unit,'variable':c,
                          'missing_group_n':len(a),'observed_group_n':len(b),
                          'missing_mean':a.mean(),'observed_mean':b.mean(),
                          'missing_median':a.median(),'observed_median':b.median(),
                          'SMD':(a.mean()-b.mean())/denom if denom>0 else np.nan})
    table('missing_vs_observed',pd.DataFrame(groups))
    wp=wclean.assign(R=wclean.pressure.isna(),rain=wclean.precip.gt(0))
    table('pressure_groups',wp.groupby('R').agg(n=('weather_id','size'),rain_pct=('rain',lambda x:100*x.mean()),
          humid_mean=('humid','mean'),visib_mean=('visib','mean'),precip_mean=('precip','mean')).reset_index())
    table('pressure_by_airport_month',wp.groupby(['origin','month']).agg(n=('weather_id','size'),missing_pct=('R',lambda x:100*x.mean())).reset_index())
    table('status_by_airport',d.groupby('origin').agg(n=('flight_id','size'),no_departure_n=('status',lambda x:x.eq('no_departure').sum()),
          other_incomplete_n=('status',lambda x:x.eq('other_incomplete').sum()),eligible_n=('eligible','sum'),weather_missing_n=('weather_missing','sum')).reset_index())
    # 在逐時天氣表預測氣壓是否缺失，並按日期分組交叉驗證。
    # AUC 只能說明缺失與可觀測變數有關，不能證明 MAR 或排除 MNAR。
    local=wclean.time_hour.dt.tz_convert('America/New_York')
    X=pd.get_dummies(wclean[['origin','month']].astype(str),dtype=float)
    X['hour_sin']=np.sin(2*np.pi*local.dt.hour/24);X['hour_cos']=np.cos(2*np.pi*local.dt.hour/24)
    for c in ['temp','dewp','humid','wind_speed','precip','visib']:X[c]=wclean[c]
    y=wclean.pressure.isna().astype(int).to_numpy();groups=local.dt.date.astype(str)
    auc=[]
    for fold,(tr,te) in enumerate(GroupKFold(5).split(X,y,groups),1):
        clf=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=1500))
        clf.fit(X.iloc[tr],y[tr]);pred=clf.predict_proba(X.iloc[te])[:,1]
        auc.append({'fold':fold,'auc':roc_auc_score(y[te],pred),'test_hours':len(te)})
    table('missingness_logistic_cv',pd.DataFrame(auc))
    return {'auc_mean':float(np.mean([x['auc'] for x in auc])),
       'wind_qc_hours':int(wclean.wind_qc.sum()),'wind_qc_flights':int(d.wind_qc.sum()),
       'unmatched_flights':int(d.unmatched.sum()),'unmatched_hour_keys':int(hourly.unmatched.sum())}

def airport_comparisons(d):
    """機場比較先看原均值，再限制到三機場都有足夠樣本的共同分層。"""
    rows=[]
    for name,mask in [('available_arr_delay',d.arr_delay.notna()),('eligible',d.eligible),('CCA',d.eligible&~d.weather_missing)]:
        t=d.loc[mask].groupby('origin').arr_delay.agg(['size','mean','median','std']).reset_index()
        t['strategy']=name;rows.append(t)
    table('airport_delay',pd.concat(rows,ignore_index=True))
    sub=d.loc[d.eligible].copy(); keys=['carrier','month','time_band']
    agg=sub.groupby(keys+['origin']).arr_delay.agg(['size','sum']).reset_index()
    good=agg.pivot_table(index=keys,columns='origin',values='size',fill_value=0).ge(20).all(axis=1)
    goodkeys=good[good].reset_index()[keys]
    common=sub.merge(goodkeys,on=keys,how='inner',validate='many_to_one')
    cells=common.groupby(keys+['origin']).arr_delay.agg(['size','mean']).reset_index()
    weights=common.groupby(keys).size().rename('cell_n').reset_index();weights['weight']=weights.cell_n/weights.cell_n.sum()
    cells=cells.merge(weights,on=keys)
    out=common.groupby('origin').arr_delay.agg(['size','mean']).reset_index().rename(columns={'mean':'common_unadjusted'})
    std=cells.assign(wmean=cells['mean']*cells.weight).groupby('origin').wmean.sum().rename('standardized_mean')
    out=out.merge(std,on='origin');out['common_cells']=len(goodkeys)
    out['eligible_coverage_pct']=100*out['size']/sub.groupby('origin').size().reindex(out.origin).to_numpy()
    table('airport_standardized',out);table('airport_common_cells',cells)
    table('airport_carrier',sub.groupby(['origin','carrier']).agg(n=('flight_id','size'),arr_mean=('arr_delay','mean')).reset_index())
    table('airport_time_band',sub.groupby(['origin','time_band']).agg(n=('flight_id','size'),arr_mean=('arr_delay','mean')).reset_index())

def figures(d,models,values,summary):
    """圖像可抽樣以保持可讀；模型與表格仍使用全資料。"""
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})
    rng=np.random.default_rng(SEED)
    # 缺失矩陣按機場與日期排序後等距抽樣，圖上明示只有 2,000 班。
    order=d.sort_values(['origin','month','day','hour']).index.to_numpy()
    idx=order[np.linspace(0,len(order)-1,2000,dtype=int)]
    fig,axs=plt.subplots(1,2,figsize=(10.6,4.3),layout='constrained')
    axs[0].imshow(d.loc[idx,VARIABLES].isna(),aspect='auto',interpolation='nearest',cmap=matplotlib.colors.ListedColormap(['#e4eeee','#cc674c']))
    axs[0].set(xticks=range(11),xticklabels=VARIABLES,ylabel='2,000 ordered flights',title='Missingness matrix (red = missing)');axs[0].tick_params(axis='x',rotation=70)
    phi=d[VARIABLES].isna().astype(float).corr()
    im=axs[1].imshow(phi,vmin=-1,vmax=1,cmap='RdBu_r')
    axs[1].set(xticks=range(11),xticklabels=VARIABLES,yticks=range(11),yticklabels=VARIABLES,title='Co-missingness: binary phi correlation');axs[1].tick_params(axis='x',rotation=70)
    fig.colorbar(im,ax=axs[1],shrink=.7);fig.savefig(FIG/'missingness.png',dpi=190);plt.close(fig)
    # 同一筆逐時天氣會對應多班航班，這裡只做分布描述，不做獨立樣本檢定。
    fig,axs=plt.subplots(1,3,figsize=(10.6,3.2),layout='constrained')
    for ax,col in zip(axs,['humid','visib','arr_delay']):
        dat=d.loc[d.eligible]
        for flag,label,color in [(False,'Pressure observed','#237f8c'),(True,'Pressure missing','#da8c37')]:
            x=np.sort(dat.loc[dat.pressure_missing.eq(flag),col].dropna().to_numpy())
            ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label,color=color)
        ax.set(xlabel=col,ylabel='Empirical cumulative probability')
        if col=='arr_delay':ax.set_xlim(-70,180)
    axs[0].legend(fontsize=8,loc='lower right');fig.savefig(FIG/'missing_group_ecdf.png',dpi=190);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10.6,3.5),layout='constrained')
    for name,mod in models.items():
        axs[0].plot(range(1,12),100*mod['evr'],'o-',label=name,color=COLORS[name],markersize=3)
        axs[1].plot(range(1,12),100*np.cumsum(mod['evr']),'o-',color=COLORS[name],markersize=3)
    axs[0].set(xlabel='Principal component',ylabel='Explained variance (%)',title='Scree plot');axs[0].legend()
    axs[1].axhline(80,ls=':',color='gray');axs[1].set(xlabel='Number retained',ylabel='Cumulative explained variance (%)',title='80% criterion uses 5 components')
    fig.savefig(FIG/'scree.png',dpi=190);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10.6,4.2),layout='constrained')
    for k,ax in enumerate(axs):
        for name,mod in models.items():ax.plot(mod['vectors'][:,k],range(11),'o-',label=name,color=COLORS[name],markersize=3)
        ax.axvline(0,color='gray',lw=.6);ax.set(yticks=range(11),yticklabels=VARIABLES,xlabel='Unit eigenvector coefficient',title=f'PC{k+1}: sign-aligned coefficients');ax.invert_yaxis()
    axs[0].legend(fontsize=8);fig.savefig(FIG/'loading_comparison.png',dpi=190);plt.close(fig)
    # 三個面板使用同一批完整航班，避免樣本組成變化冒充 PCA 位移。
    e=d.loc[d.eligible].reset_index(drop=True);cc=~e.weather_missing.to_numpy();ids=np.flatnonzero(cc)
    shown=np.sort(rng.choice(ids,min(8000,len(ids)),replace=False));origin=e.origin.to_numpy()
    fig,axs=plt.subplots(1,3,figsize=(10.6,3.4),layout='constrained')
    for ax,(name,mod) in zip(axs,models.items()):
        sc=scores(mod,values[name if name!='CCA' else 'HOTDECK'][shown])
        for o,c in zip(['EWR','JFK','LGA'],['#227f8b','#da8c37','#7d63a8']):
            z=origin[shown]==o;ax.scatter(sc[z,0],sc[z,1],s=3,alpha=.3,color=c,label=o,rasterized=True)
        ax.set(title=name,xlabel='PC1',ylabel='PC2',xlim=(-5,10),ylim=(-4,8))
    axs[0].legend(markerscale=3,fontsize=7);fig.savefig(FIG/'common_scores.png',dpi=190);plt.close(fig)

def validate_masking(hourly):
    """遮蔽原本有值的氣壓來比較補值誤差；這不能證明真實缺失群符合 MAR。"""
    eligible=hourly[WEATHER].notna().all(axis=1)
    rng=np.random.default_rng(SEED+991)
    ids=rng.choice(np.flatnonzero(eligible),1500,replace=False)
    trial=hourly.copy();truth=trial.loc[ids,'pressure'].to_numpy();trial.loc[ids,'pressure']=np.nan
    candidates,_=candidate_donors(trial);x,_=hotdeck(trial,candidates,SEED+992)
    pred=x[ids,WEATHER.index('pressure')];mean=np.nanmean(trial.pressure)
    return pd.DataFrame([{'method':'global_mean','n':len(ids),'RMSE':np.sqrt(np.mean((truth-mean)**2)),'MAE':np.mean(abs(truth-mean))},
                         {'method':'conditional_hotdeck','n':len(ids),'RMSE':np.sqrt(np.mean((truth-pred)**2)),'MAE':np.mean(abs(truth-pred))}])

def run(draws=20):
    """依序完成缺失診斷、三策略、PCA、穩定性及圖表輸出。"""
    for p in [TABLES,FIG,ROOT/'data/derived']:p.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((ROOT/'baseline/frozen_manifest.json').read_text())
    for file,sha in frozen['files'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==sha,file
    f,w,raw,wclean,hourly,d=prepare();print('Prepared data',len(d),'flights',flush=True)
    diag=diagnostics(f,w,raw,wclean,hourly,d);airport_comparisons(d)
    e=d.loc[d.eligible].reset_index(drop=True);cc=~e.weather_missing.to_numpy()
    xraw=e[VARIABLES].to_numpy(float);xcommon=xraw[cc]
    reference=pca(xcommon);models={'CCA':reference};values={}
    # 平均數法先在逐時天氣表估計均值，不讓忙碌時段因航班多而重複加權。
    # CCA 刪完整列；MEAN 與 HOTDECK 只補天氣，不補航班的飛行結果。
    hmean=hourly[WEATHER].fillna(hourly[WEATHER].mean()).to_numpy()
    meanvalues=xraw.copy();meanvalues[:,4:]=hmean[e.hour_id.to_numpy()]
    models['MEAN']=pca(meanvalues,reference);values['MEAN']=meanvalues
    candidates,audit=candidate_donors(hourly);table('donor_audit',audit)
    rows=[];vectors=[];variances=[];hfirst=None
    for j in range(draws):
        filled,chosen=hotdeck(hourly,candidates,SEED+j)
        x=xraw.copy();x[:,4:]=filled[e.hour_id.to_numpy()]
        mod=pca(x,reference)
        row={'draw':j+1,'seed':SEED+j,'pc1_pct':100*mod['evr'][0],'pc2_pct':100*mod['evr'][1],
             'pressure_mean':x[:,-1].mean(),'pressure_sd':x[:,-1].std(ddof=1),**stability(reference,mod,xcommon)}
        rows.append(row);vectors.append(mod['vectors']);variances.append(mod['evr'])
        if j==0:models['HOTDECK']=mod;values['HOTDECK']=x;hfirst=filled
        if (j+1)%5==0:print('Donor draw',j+1,'/',draws,flush=True)
    values['CCA']=xraw
    table('hotdeck_draws',pd.DataFrame(rows))
    vec=np.array(vectors);ev=np.array(variances)
    vr=[]
    for j,c in enumerate(VARIABLES):
        for k in range(3):vr.append({'variable':c,'PC':k+1,'mean':vec[:,j,k].mean(),'min':vec[:,j,k].min(),'max':vec[:,j,k].max()})
    table('hotdeck_vector_ranges',pd.DataFrame(vr))
    summaries=[];stats=[];stable=[];load=[]
    for name,mod in models.items():
        x=xcommon if name=='CCA' else values[name]
        summaries.append({'strategy':name,'n':len(x),'retained_pct_eligible':100*len(x)/len(e),
             'arr_delay_mean':x[:,1].mean(),'arr_delay_sd':x[:,1].std(ddof=1),
             'pressure_mean':x[:,-1].mean(),'pressure_sd':x[:,-1].std(ddof=1),
             'humid_mean':x[:,6].mean(),'rain_pct':100*np.mean(x[:,8]>0),
             'visib_mean':x[:,9].mean(),'pc1_pct':100*mod['evr'][0],'pc2_pct':100*mod['evr'][1],
             'pc12_pct':100*sum(mod['evr'][:2]),'k80':int(np.searchsorted(np.cumsum(mod['evr']),.8)+1),
             'pc1_pc2_gap':mod['eigenvalues'][0]-mod['eigenvalues'][1],
             'pc2_pc3_gap':mod['eigenvalues'][1]-mod['eigenvalues'][2]})
        stable.append({'strategy':name,**stability(reference,mod,xcommon)})
        for j,c in enumerate(VARIABLES):
            stats.append({'strategy':name,'variable':c,'n':len(x),'mean':x[:,j].mean(),'sd':x[:,j].std(ddof=1),
                          'median':np.median(x[:,j]),'p05':np.quantile(x[:,j],.05),'p95':np.quantile(x[:,j],.95)})
            for k in range(11):load.append({'strategy':name,'variable':c,'PC':k+1,'coefficient':mod['vectors'][j,k],
                                           'correlation_loading':mod['loadings'][j,k],'evr':mod['evr'][k]})
    table('strategy_summary',pd.DataFrame(summaries));table('descriptive_strategies',pd.DataFrame(stats))
    table('pca_stability',pd.DataFrame(stable));table('pca_loadings',pd.DataFrame(load))
    # 額外固定 HOTDECK 的尺度做 PCA，檢查「結構穩定」是否依賴重新標準化。
    # 另排除未配對天氣時點，分辨合併缺口與原始欄位缺失的影響。
    extras=[]
    fixed=models['HOTDECK']['scale'];fixedref=pca(xcommon,fixed_scale=fixed)
    for name,x in [('CCA',xcommon),('MEAN',values['MEAN']),('HOTDECK',values['HOTDECK'])]:
        mod=pca(x,fixedref,fixed_scale=fixed)
        extras.append({'check':'fixed_HOTDECK_scale','strategy':name,'n':len(x),**stability(fixedref,mod,xcommon)})
    matched=~e.unmatched.to_numpy();mod=pca(values['HOTDECK'][matched],models['HOTDECK'])
    extras.append({'check':'exclude_unmatched_hours','strategy':'HOTDECK','n':int(matched.sum()),**stability(models['HOTDECK'],mod,xcommon)})
    original=raw.loc[raw[VARIABLES].notna().all(axis=1),VARIABLES].to_numpy()
    mod=pca(original,reference);extras.append({'check':'retain_raw_wind','strategy':'CCA','n':len(original),**stability(reference,mod,xcommon)})
    table('additional_sensitivity',pd.DataFrame(extras))
    table('mask_validation',validate_masking(hourly))
    # 保存第一份熱卡資料與全部抽樣 seed；其餘 19 次可依 seed 重現。
    metadata=['flight_id','origin','carrier','dest','month','day','hour','time_band','weekday','season','status',
              'rain_group','visibility_group','weather_missing','pressure_missing','unmatched','wind_qc']
    e[metadata].to_csv(ROOT/'data/derived/eligible_metadata.csv',index=False)
    np.savez_compressed(ROOT/'data/derived/pca_data.npz',raw=xraw,mean=meanvalues,hotdeck=values['HOTDECK'],complete=cc,
                        hourly_first_draw=hfirst,draw_vectors=vec,draw_evr=ev)
    dump(ROOT/'output/models.json',models)
    results={'seed':SEED,'draws':draws,'n_total':len(f),'n_weather':len(w),'n_eligible':len(e),
             'n_complete':int(cc.sum()),'n_no_departure':int(d.dep_time.isna().sum()),
             'n_other_incomplete':int((d.status=='other_incomplete').sum()),'diagnostics':diag,
             'strategies':summaries,'stability':stable,'hotdeck_draw_summary':pd.DataFrame(rows).describe().to_dict(),
             'note':'Hot-deck variation ranges are algorithmic sensitivity ranges, not confidence intervals or Rubin pooling.'}
    dump(ROOT/'output/results.json',results)
    hourly.to_csv(ROOT/'data/derived/hourly_with_missingness.csv',index=False)
    figures(d,models,values,results)
    dump(ROOT/'output/environment.json',{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,
       'pandas':pd.__version__,'matplotlib':matplotlib.__version__,'seed':SEED,'draws':draws})
    print(pd.DataFrame(summaries).round(4).to_string(index=False),flush=True)
    print(pd.DataFrame(stable).round(4).to_string(index=False),flush=True)
    print('Complete: tables, figures, models and full derived data.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--draws',type=int,default=20)
    run(parser.parse_args().draws)
