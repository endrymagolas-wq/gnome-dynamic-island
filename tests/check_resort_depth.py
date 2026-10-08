"""Check exported depth against clear, known beach points, including exposure."""
import json, math, sys, os
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
assets=Path(os.environ.get('RESORT_TEST_ASSETS',root/'wallpaper/assets'))
meta=json.loads((assets/('scene-v2.json' if '--v3' in sys.argv else 'scene.json')).read_text())
image=Image.open(assets/('depth-v3.png' if '--v3' in sys.argv else 'depth.png')).convert('RGB')
camera=meta['camera'];matrix=camera['matrixWorld'];f=meta['width']*camera['lens']/camera['sensor']
for point in [(0,-3,.43),(-1,-2.8,.43),(1,-3,.43)]:
    delta=[point[i]-camera['location'][i] for i in range(3)]
    x=sum(delta[i]*matrix[i][0] for i in range(3));y=sum(delta[i]*matrix[i][1] for i in range(3));z=-sum(delta[i]*matrix[i][2] for i in range(3))
    pixel=(round(meta['width']/2+f*x/z),round(meta['height']/2-f*y/z))
    value=image.getpixel(pixel)[0]/255
    linear=value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4
    measured=linear*50
    assert abs(measured-z)<.3, (point,pixel,z,measured,'Depth must bypass beauty-render exposure')
print('PASS rendered beach depth registration and neutral matte exposure')
