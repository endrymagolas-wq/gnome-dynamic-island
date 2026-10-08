#!/usr/bin/env python3
"""Bake water banks through a local Chromium DevTools endpoint. No runtime shader."""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import urllib.request
import websockets

async def bake(args):
    pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{args.debug_port}/json'))
    async with websockets.connect(pages[0]['webSocketDebuggerUrl'],max_size=32000000) as ws:
        counter=0
        async def call(method,params=None):
            nonlocal counter
            counter+=1
            await ws.send(json.dumps({'id':counter,'method':method,'params':params or {}}))
            while True:
                reply=json.loads(await ws.recv())
                if reply.get('id')==counter:return reply
        async def evaluate(expression):
            reply=await call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
            if 'exceptionDetails' in reply.get('result',{}):raise RuntimeError(reply['result']['exceptionDetails'])
            return reply['result']['result'].get('value')
        await call('Page.navigate',{'url':args.url})
        for _ in range(100):
            if await evaluate('window.waterReady===true'):break
            await asyncio.sleep(.1)
        else:raise RuntimeError('water baker did not initialize')
        args.output.mkdir(parents=True,exist_ok=True)
        for bank in range(2):
            data=await evaluate(f'window.bakeWaterBank({bank})')
            path=args.output/f'water-{bank}.png'
            path.write_bytes(base64.b64decode(data.split(',')[1]))
            print(f'Baked {path}: {path.stat().st_size} bytes')
        if not args.true_colour:
            # One palette across both banks avoids a colour jump at their seam.
            from PIL import Image
            images=[Image.open(args.output/f'water-{i}.png').convert('RGBA') for i in range(2)]
            combined=Image.new('RGBA',(3072,3072))
            for i,image in enumerate(images):combined.paste(image,(0,i*1536))
            indexed=combined.quantize(colors=256,method=Image.Quantize.FASTOCTREE)
            for i in range(2):
                path=args.output/f'water-{i}.png'
                indexed.crop((0,i*1536,3072,(i+1)*1536)).save(path,optimize=True)
                print(f'Optimized {path}: {path.stat().st_size} bytes')
        if args.frames:
            args.frames.mkdir(parents=True,exist_ok=True)
            for frame in range(24):
                data=await evaluate(f'window.waterFrame({frame})')
                (args.frames/f'frame-{frame:02}.png').write_bytes(base64.b64decode(data.split(',')[1]))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug-port',type=int,default=9222)
    parser.add_argument('--url',default='http://127.0.0.1:8000/preview/bake-water.html')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'extensions/cartoon-island@avalon.local/assets')
    parser.add_argument('--frames',type=Path)
    parser.add_argument('--true-colour',action='store_true',help='Keep RGBA PNGs instead of sharing an indexed palette')
    asyncio.run(bake(parser.parse_args()))
