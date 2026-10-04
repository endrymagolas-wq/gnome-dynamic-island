import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'assistant'))
from process_observer import ProcessObserver,parse_stat,role,recommendation

def stat(pid,name,ppid,ticks,start,rss):
 v=['0']*22;v[0]='S';v[1]=str(ppid);v[11]=str(ticks);v[19]=str(start);v[21]=str(rss)
 return f"{pid} ({name}) "+' '.join(v)
with tempfile.TemporaryDirectory() as d:
 root=Path(d);(root/'stat').write_text('cpu 1000 0 0 1000 0 0 0 0\n')
 for pid,name,ppid,ticks,start,rss in [(100,'chrome',1,20,500,100),(101,'renderer',100,10,501,50),(102,'job',1,10,600,10)]:
  (root/str(pid)).mkdir();(root/str(pid)/'stat').write_text(stat(pid,name,ppid,ticks,start,rss))
 o=ProcessObserver(root);o.self_pid=999;s=o.sample(force=True)
 assert all(x['cpu_total_percent']==0 for x in s['top_cpu'])
 (root/'stat').write_text('cpu 1100 0 0 1100 0 0 0 0\n')
 (root/'100'/'stat').write_text(stat(100,'chrome',1,40,500,100))
 (root/'101'/'stat').write_text(stat(101,'renderer',100,30,501,50))
 # PID reuse must not inherit CPU delta from old process.
 (root/'102'/'stat').write_text(stat(102,'job',1,5000,700,10))
 s=o.sample(foreground_pid=100,force=True);g={x['name']:x for x in s['top_cpu']}
 assert g['chrome']['cpu_total_percent']==10 and g['renderer']['cpu_total_percent']==10
 assert g['job']['cpu_total_percent']==0 and g['job']['role']=='unknown'
 assert g['renderer']['role']=='browser' and g['chrome']['protected']
 r=recommendation('cpu',s);assert r['automatic_action'] is False and 'вкладки' in r['advice']
 p=parse_stat(stat(103,'odd (name)',1,3,9,10));assert p['name']=='odd name'
 assert s['pressure_avg10']=={'cpu':None,'memory':None,'io':None}
 assert s['actions_enabled'] is False
print('PASS: CPU normalization, first sample, PID reuse, browser children protection, unknown-process handling, malformed name, missing PSI, read-only advice')
print(json.dumps(s,ensure_ascii=False))
