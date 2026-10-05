"""Check the shipped atlas against independent rays from the Blender geometry."""
import json
from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parents[1]
evidence=json.loads((p/'docs/evidence/resort/cabana-depth-v3-probes.json').read_text())
meta=json.loads((p/'wallpaper/assets/scene.json').read_text());b=meta['construction']
image=Image.open(p/'wallpaper/assets'/b['depthAtlas']).convert('RGBA')
assert image.size==(b['width']*5,b['height'])
for sample in evidence['samples']:
    x,y=sample['pixel'];pixel=image.getpixel((sample['stage']*b['width']+x,y));assert pixel[3]>250
    v=pixel[0]/255;linear=v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    assert abs(linear*b['depthScale']-b['depthBias']-sample['meshOffset'])<.055,sample
print(f"PASS {len(evidence['samples'])} shipped cabana depth samples against original 3D geometry")
