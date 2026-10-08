"""Create a fair 720p atlas from the SAME encoded water loop, for measurement only."""
from pathlib import Path
import subprocess,tempfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'wallpaper/assets';banks=OUT/'benchmark-atlas';banks.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='resort-frames-') as td:
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(OUT/'water-720.mp4'),str(Path(td)/'%04d.png')],check=True)
    for bank in range(23):
        image=Image.new('RGB',(5120,2880))
        for cell in range(16):
            frame=bank*16+cell+1
            if frame>360:break
            with Image.open(Path(td)/f'{frame:04d}.png') as source:image.paste(source,(cell%4*1280,cell//4*720))
        image.save(banks/f'bank-{bank}.png')
print('Prepared 23 atlas banks, 360 frames at 1280x720. Decoded RGB cost: 1017.8 MiB, RGBA GPU textures: 1357.0 MiB before buffers.')
