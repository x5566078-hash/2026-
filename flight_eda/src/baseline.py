"""Initial, frozen AI EDA: run before mechanism-oriented diagnostics."""
from pathlib import Path
import os, json, hashlib
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.mplcache'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

FLIGHT = ['dep_delay','arr_delay','air_time','distance']
WEATHER = ['temp','dewp','humid','wind_speed','precip','visib','pressure']
VARIABLES = FLIGHT + WEATHER

def load_data():
    f = pd.read_csv(ROOT/'data/raw/flights.csv').rename(columns={'rownames':'flight_id'})
    w = pd.read_csv(ROOT/'data/raw/weather.csv').rename(columns={'rownames':'weather_id'})
    for d in (f,w):
        d['time_hour'] = pd.to_datetime(d['time_hour'], utc=True)
    assert not w.duplicated(['origin','time_hour']).any(), 'Weather join key is not unique'
    d = f.merge(w[['origin','time_hour','weather_id']+WEATHER], how='left',
                on=['origin','time_hour'], validate='many_to_one', indicator=True)
    assert len(d)==len(f)==336776
    return f,w,d

def run():
    out=ROOT/'baseline';out.mkdir(exist_ok=True)
    f,w,d=load_data()
    missing=d[VARIABLES].isna().sum().rename('missing_n').to_frame()
    missing['missing_pct']=100*missing.missing_n/len(d)
    missing.to_csv(out/'missing.csv')
    d[VARIABLES].describe(percentiles=[.01,.25,.5,.75,.99]).T.to_csv(out/'descriptive.csv')
    d.groupby('origin').agg(n=('flight_id','size'),arr_delay_mean=('arr_delay','mean'),
                           arr_delay_median=('arr_delay','median'),dep_delay_mean=('dep_delay','mean')).to_csv(out/'airports.csv')
    corr=d[VARIABLES].corr();corr.to_csv(out/'correlations.csv')
    cc=d.dropna(subset=VARIABLES)
    z=StandardScaler().fit_transform(cc[VARIABLES]);p=PCA(svd_solver='full').fit(z)
    pd.DataFrame(p.components_.T,index=VARIABLES,columns=[f'PC{i+1}' for i in range(11)]).to_csv(out/'pca_vectors.csv')
    stats={'n_flights':len(f),'n_weather':len(w),'n_complete':len(cc),
           'n_unmatched':int((d._merge=='left_only').sum()),
           'explained_variance':p.explained_variance_ratio_.tolist(),
           'max_wind_speed':float(w.wind_speed.max()),
           'max_arr_delay':float(f.arr_delay.max()),
           'min_arr_delay':float(f.arr_delay.min())}
    (out/'statistics.json').write_text(json.dumps(stats,indent=2))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(10.4,3.8),layout='constrained')
    axs[0].hist(d.arr_delay.dropna(),bins=np.arange(-100,601,10),color='#227c9d')
    axs[0].set(title='Arrival delay (range shown: -100 to 600 min)',xlabel='Minutes',ylabel='Flights')
    axs[1].bar(missing.index,missing.missing_pct,color='#d18b42')
    axs[1].tick_params(axis='x',rotation=60);axs[1].set(ylabel='Missing (%)',title='Missingness after left join')
    fig.savefig(out/'baseline_distributions.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10.4,4.2),layout='constrained')
    im=axs[0].imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r')
    axs[0].set(xticks=np.arange(11),xticklabels=VARIABLES,yticks=np.arange(11),yticklabels=VARIABLES,title='Pairwise correlations')
    axs[0].tick_params(axis='x',rotation=90);fig.colorbar(im,ax=axs[0],shrink=.75)
    axs[1].plot(np.arange(1,12),p.explained_variance_ratio_*100,'o-',color='#227c9d')
    axs[1].set(xlabel='Component',ylabel='Explained variance (%)',title='Complete-case, standardized PCA')
    fig.savefig(out/'baseline_pca.png',dpi=180);plt.close(fig)
    print(json.dumps(stats,indent=2))
    print(d.groupby('origin').arr_delay.agg(['count','mean','median']).to_string())
    print(missing.to_string())
    print(corr.round(3).to_string())
    print(pd.DataFrame(p.components_[:3].T,index=VARIABLES).round(3).to_string())

if __name__=='__main__':run()
