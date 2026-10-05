"""Package decoded sprites, source-frame video encodes and honest loop evidence."""
import argparse,json,subprocess,tempfile,os
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('RESORT_RENDER_OUT',ROOT/'wallpaper/assets'))
def atlas():
    im=Image.new('RGBA',(2048,2880))
    for row in range(17):
        for f in range(16):im.paste(Image.open(OUT/'character-frames'/f'{row:02}_{f:02}.png'),(f*128,row*160))
    for stage in range(5):
        p=OUT/f'construction-{stage}.png'
        if p.exists():im.paste(Image.open(p),(stage*160,2720))
    im.save(OUT/'character.png')
    if (OUT/'smoke-frames').exists():
        smoke=Image.new('RGBA',(1536,1024))
        for f in range(24):smoke.paste(Image.open(OUT/'smoke-frames'/f'{f:02}.png'),(f%6*256,f//6*256))
        smoke.save(OUT/'smoke.png')
def encode(folder,name,width):
    # A cyclic seven-frame temporal average softens Monte Carlo render grain.
    # Padding with the end of the same cycle avoids a denoiser reset at the seam.
    with tempfile.TemporaryDirectory(prefix='resort-encode-') as td:
        for i,frame in enumerate(list(range(355,361))+list(range(1,361)),1):
            os.link(OUT/folder/f'{frame:04d}.png',Path(td)/f'{i:04d}.png')
        # Intra-only encoding avoids a quality jump between the final predicted
        # frame and the first keyframe. Verify the encoded seam, not only PNGs.
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','30','-start_number','1','-i',str(Path(td)/'%04d.png'),'-frames:v','360','-vf',f'tmix=frames=7,trim=start_frame=6,setpts=PTS-STARTPTS,scale={width}:-2:flags=lanczos','-c:v','libx264','-preset','slow','-crf','18','-g','1','-bf','0','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(OUT/name)],check=True)
def loop(folder,report_name='loop-check.json'):
    images=[Image.open(OUT/folder/f'{f:04}.png').convert('RGB') for f in [1,2,359,360,361] if (OUT/folder/f'{f:04}.png').exists()]
    dif=lambda a,b:sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
    report={'first_to_second_MAE':dif(images[0],images[1]),'penultimate_to_last_MAE':dif(images[2],images[3]),'last_to_first_MAE':dif(images[3],images[0]),'endpoint_361_to_first_MAE':dif(images[4],images[0]) if len(images)==5 else None,'method':'Raw RGB mean absolute difference, 0-255. Last frame to first is one normal 1/30-second step, not a duplicated endpoint.'}
    (OUT/report_name).write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['draft','final','atlas','loop','v3-draft']);a=p.parse_args()
    if a.mode=='atlas':atlas()
    elif a.mode=='draft':encode('draft-water','draft-water.mp4',960)
    elif a.mode=='v3-draft':encode('v3-water-draft','v3-water-draft.mp4',480);loop('v3-water-draft','v3-draft-loop-check.json')
    elif a.mode=='final':encode('water-frames','water-1080.mp4',1920);encode('water-frames','water-720.mp4',1280);loop('water-frames')
    else:loop('water-frames')
