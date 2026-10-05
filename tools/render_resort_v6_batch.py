"""Sequential offline lighting render; resumable per complete stage."""
import argparse,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'wallpaper/assets/v6-stage'
p=argparse.ArgumentParser();p.add_argument('--blender',required=True);p.add_argument('--source',default=str(ROOT/'art/island/resort-v6.blend'));args=p.parse_args()
for phase in ('day','morning','evening','night'):
 out=STAGE if phase=='day' else STAGE/'phases'/phase;out.mkdir(parents=True,exist_ok=True)
 for mode in ('sprites','layers','water'):
  report=out/(mode+'-progress.json')
  if report.exists() and json.loads(report.read_text()).get('stage')=='complete':continue
  with (out/(mode+'-worker.log')).open('w') as log:
   command=[args.blender,'--background',str(Path(args.source).resolve()),'--python',str(ROOT/'tools/render_resort_v6.py'),'--',mode,phase]
   (STAGE/'batch-progress.json').write_text(json.dumps({'phase':phase,'mode':mode,'stage':'rendering'}))
   subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
(STAGE/'batch-progress.json').write_text(json.dumps({'stage':'complete','phases':['day','morning','evening','night']}))
