"""Build a clean, hash-indexed submission archive without caches or credentials."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT.parent/'題目E_紐約航班_EDA與PPT繳交包.zip'
OMIT={'tmp','presentation_build','site','__pycache__','.mplcache','node_modules','.git','.venv'}
def run():
    files=[]
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or p.is_symlink() or any(part in OMIT or part.startswith('.') for part in rel.parts):continue
        if p.suffix in {'.log','.pyc','.gz'} or p.name=='deliverables_manifest.json':continue
        files.append(p)
    capture=ROOT/'output/browser_screenshots/capture_manifest.json'
    cm=json.loads(capture.read_text()) if capture.exists() else {}
    screen_count=len(cm.get('records',[])) if cm.get('passed') else 0
    publication_path=ROOT/'docs/dashboard_publication.json'
    publication=json.loads(publication_path.read_text()) if publication_path.exists() else {}
    dashboard_url=publication.get('url') if publication.get('published') else None
    manifest={'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
        'report_body_pages':11,'report_appendix_pages':7,'reflection_chinese_characters':670,
        'presentation_slides':14,'short_presentation_slides':10,
        'short_presentation_duration_seconds':458,
        'executed_notebook_cells':17,'analysis_operation_snapshots':6,
        'browser_screen_captures':screen_count,'dashboard_published':bool(dashboard_url),
        'dashboard_url':dashboard_url,
        'dashboard_verification_scope':publication.get('verified_scope') if dashboard_url else None,
        'strict_interactive_submission_satisfied':screen_count>=5 or bool(dashboard_url),
        'remaining_requirement':None if screen_count>=5 or dashboard_url else 'Real browser screenshots (at least 5), or a successfully published dashboard link.',
        'limitations':['PCA population excludes missing flight measurements.','Conditional MAR is an assumption, not identified from observed data.']}
    mp=ROOT/'deliverables_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2));files.append(mp)
    temp=ARCHIVE.with_suffix('.tmp.zip')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,'flight_eda/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(temp) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
    temp.replace(ARCHIVE)
    print(json.dumps({'archive':str(ARCHIVE),'files':len(files),'bytes':ARCHIVE.stat().st_size,'real_browser_captures':screen_count},ensure_ascii=False))
if __name__=='__main__':run()
