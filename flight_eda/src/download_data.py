"""Download exact public Git blobs; skip verified included files by default."""
from pathlib import Path
import base64,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'flights':{'git_blob':'d72630cde3a70916b6f8ed76c18725722a110c3d','sha256':'b791a2590c9167aa0bd3cb45af3f64101180878cf088c183eae4011e3a654f42'},
 'weather':{'git_blob':'a0d79ac1a1739826c7c36b8937f0ccec49d6476f','sha256':'e69580cc3c18070692b6bf2f52e890803a313507c23283b15f06dbbae86451cf'}}
def verify_or_download():
    for name,meta in SOURCES.items():
        dest=ROOT/'data/raw'/f'{name}.csv'
        if not dest.exists():
            url='https://api.github.com/repos/vincentarelbundock/Rdatasets/git/blobs/'+meta['git_blob']
            request=urllib.request.Request(url,headers={'User-Agent':'reproducible-course-eda','Accept':'application/vnd.github+json'})
            with urllib.request.urlopen(request,timeout=180) as response:obj=json.load(response)
            data=base64.b64decode(obj['content'])
            assert hashlib.sha256(data).hexdigest()==meta['sha256'],'Download checksum mismatch'
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        data=dest.read_bytes()
        assert hashlib.sha256(data).hexdigest()==meta['sha256'],f'Modified raw file: {dest}'
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==meta['git_blob']
        print(name,len(data),'bytes: SHA-256 and Git blob verified')
if __name__=='__main__':verify_or_download()
