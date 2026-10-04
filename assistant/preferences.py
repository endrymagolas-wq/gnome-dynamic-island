"""Private assistant settings shared by worker and explicit local controls."""
import json,os,tempfile
from pathlib import Path
KINDS={'connection','download','cpu','ram','task','service','disk','network'}
BASE=Path(os.environ.get('ISLAND_ASSISTANT_DATA_DIR',Path(__file__).resolve().parent))

def read(path=None):
    defaults={'enabled':True,'economy':True,'muted_kinds':[]}
    try:
        p=Path(path or BASE/'preferences.json')
        if p.stat().st_size>4096:return defaults
        value=json.loads(p.read_text())
        if not isinstance(value,dict):return defaults
        return {'enabled':value.get('enabled',True) is not False,'economy':value.get('economy',True) is not False,'muted_kinds':sorted(set(x for x in value.get('muted_kinds',[]) if isinstance(x,str) and x in KINDS)) if isinstance(value.get('muted_kinds',[]),list) else []}
    except (OSError,ValueError,TypeError):return defaults

def write(value,path=None):
    p=Path(path or BASE/'preferences.json');p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.preferences-',dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False);os.fchmod(f.fileno(),0o600)
        os.replace(name,p)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass
