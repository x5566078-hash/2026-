"""Meaningful data, PCA and artifact consistency checks (no browser required)."""
from pathlib import Path
import json,hashlib,re
import numpy as np
import pandas as pd
import nbformat
from baseline import load_data,VARIABLES,FLIGHT
from download_data import verify_or_download
from analysis import ROOT,dump
from explorer import Explorer

def run():
    verify_or_download();f,w,d=load_data();ex=Explorer();r=json.loads((ROOT/'output/results.json').read_text())
    checks={}
    checks['source_and_join']=len(d)==336776 and not w.duplicated(['origin','time_hour']).any()
    checks['population_reconciles']=r['n_no_departure']+r['n_other_incomplete']+r['n_eligible']==r['n_total']
    checks['complete_count']=int(ex.data['complete'].sum())==r['n_complete']==291140
    checks['no_synthetic_flight_measurements']=all(np.array_equal(ex.arrays[s][:,:4],ex.arrays['CCA'][:,:4]) for s in ['MEAN','HOTDECK'])
    observed=np.isfinite(ex.arrays['CCA'])
    checks['preserve_observed_cells']=all(np.array_equal(ex.arrays[s][observed],ex.arrays['CCA'][observed]) for s in ['MEAN','HOTDECK'])
    checks['all_imputed_values_finite']=all(np.isfinite(ex.arrays[s]).all() for s in ['MEAN','HOTDECK'])
    checks['orthonormal_components']=all(np.allclose(m['vectors'].T@m['vectors'],np.eye(11),atol=1e-10) for m in ex.models.values())
    checks['variance_sums_to_one']=all(np.isclose(m['evr'].sum(),1) for m in ex.models.values())
    checks['descending_eigenvalues']=all(np.all(np.diff(m['eigenvalues'])<=0) for m in ex.models.values())
    # Flight summaries can be independently checked directly from untouched raw data.
    eligible=d[FLIGHT].notna().all(axis=1)
    rawmean=d.loc[eligible,'arr_delay'].mean()
    checks['delay_statistics_from_raw']=abs(rawmean-6.89537675731489)<1e-10
    operations=json.loads((ROOT/'output/screenshots/operations.json').read_text())
    for i,o in enumerate(operations):
        kwargs={k:o[k] for k in ['strategy','origin','carrier','month','time_band','rain','pressure','brush','refit']}
        got=ex.select(**kwargs,record=False)['summary']
        checks[f'operation_{i+1}_replays']=got['n']==o['n'] and np.isclose(got['arr_delay_mean'],o['arr_delay_mean'])
    frozen=json.loads((ROOT/'baseline/frozen_manifest.json').read_text())
    checks['baseline_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in frozen['files'].items())
    nb=nbformat.read(ROOT/'analysis.ipynb',as_version=4);nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=='code']
    checks['notebook_executed_without_errors']=all(c.execution_count is not None and all(o.output_type!='error' for o in c.outputs) for c in cells)
    checks['notebook_has_six_png_steps']=sum('image/png' in o.get('data',{}) for c in cells for o in c.outputs)>=6
    text=(ROOT/'docs/reflection.txt').read_text();checks['reflection_600_to_900_chinese_chars']=600<=len(re.findall(r'[\u4e00-\u9fff]',text))<=900
    expected=['src/build_report.py','src/build_interactive.py','src/build_notebook.py','output/interactive/flight_explorer.html','output/pdf/nycflights_missing_pca_report.pdf']
    checks['deliverable_files_present']=all((ROOT/p).exists() for p in expected)
    checks={k:bool(v) for k,v in checks.items()}
    result={'checks':checks,'passed':all(checks.values()),'executed_notebook_cells':len(cells),
            'limits':['Browser UI / real screen capture unavailable in this environment; output PNGs are executed analysis snapshots.']}
    dump(ROOT/'output/validation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert result['passed'],'Validation failed'
if __name__=='__main__':run()
