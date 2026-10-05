"""Decode shipped loops and compare the actual encoded boundary to adjacent steps."""
import json,subprocess,tempfile,hashlib
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
root=Path(__file__).resolve().parents[1]
report={}
for name in ('water-1080.mp4','water-720.mp4'):
    path=root/'wallpaper/assets'/name
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames,duration','-of','json',str(path)]))['streams'][0]
    assert int(probe['nb_read_frames'])==360 and probe['r_frame_rate']=='30/1' and abs(float(probe['duration'])-12)<.001,probe
    with tempfile.TemporaryDirectory(prefix='resort-seam-') as td:
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),'-vf',r'select=eq(n\,0)+eq(n\,1)+eq(n\,358)+eq(n\,359)','-vsync','0',str(Path(td)/'%02d.png')],check=True)
        frames=[Image.open(Path(td)/f'{i:02}.png').convert('RGB') for i in range(1,5)]
        def diff(a,b):return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
        first=diff(frames[0],frames[1]);last=diff(frames[2],frames[3]);seam=diff(frames[3],frames[0])
        assert seam<max(first,last)*1.5,(name,first,last,seam)
        report[name]={**probe,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'firstStepMAE':first,'lastStepMAE':last,'seamMAE':seam}
report['method']='Full FFprobe decode count and encoded RGB MAE (0-255), boundary versus adjacent 30fps steps. Numeric continuity is supplemented by the visible water review.'
(root/'docs/evidence/resort/encoded-water-v3.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
