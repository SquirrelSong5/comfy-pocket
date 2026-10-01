import gzip
from pathlib import Path
for p in (Path(__file__).resolve().parents[1]/'web/dist').rglob('*'):
    if p.suffix in ('.js','.css','.html'):
        p.with_suffix(p.suffix+'.gz').write_bytes(gzip.compress(p.read_bytes(),compresslevel=9,mtime=0))
