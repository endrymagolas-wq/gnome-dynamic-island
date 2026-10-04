"""Disposable offline Laya process. Only structured local classification, no tools."""
import os,sys,json,contextlib
os.environ.setdefault('USE_TF','0');os.environ.setdefault('HF_HUB_OFFLINE','1')
from pathlib import Path

def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)
try:
    with contextlib.redirect_stdout(sys.stderr):
        import torch,laya
        torch.set_num_threads(2);torch.set_num_interop_threads(1)
        root=Path(os.environ.get('ISLAND_LAYA_MODEL', str(Path(__file__).resolve().parent/'model'/'multilingual')))
        agent=laya.load(str(root),device='cpu')
    emit({'ready':True})
    for line in sys.stdin:
        if len(line)>65536:continue
        try:
            job=json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):answer=agent.predict(job['state'],job['questions'])['answers']['category']
            emit({'id':job['id'],'answer':answer})
        except Exception as error:emit({'id':job.get('id') if isinstance(locals().get('job'),dict) else None,'error':type(error).__name__})
except Exception as error:
    emit({'error':type(error).__name__});sys.exit(1)
