"""Validate actual baked water pixels and protected scenery without image libraries."""
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]/'extensions/cartoon-island@avalon.local/assets'

def read_png(path):
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8;compressed=[];palette=b'';alpha=b''
    while offset<len(data):
        length=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+length];offset+=12+length
        if kind==b'IHDR':width,height,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',payload)
        elif kind==b'PLTE':palette=payload
        elif kind==b'tRNS':alpha=payload
        elif kind==b'IDAT':compressed.append(payload)
    assert (width,height,depth,color,interlace)==(3072,1536,8,3,0)
    raw=zlib.decompress(b''.join(compressed));pixels=bytearray(width*height);previous=bytearray(width)
    for y in range(height):
        start=y*(width+1);filter_type=raw[start];row=bytearray(raw[start+1:start+1+width])
        if filter_type:
            for x in range(width):
                a=row[x-1] if x else 0;b=previous[x];c=previous[x-1] if x else 0
                if filter_type==1:predict=a
                elif filter_type==2:predict=b
                elif filter_type==3:predict=(a+b)//2
                elif filter_type==4:
                    p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c);predict=a if pa<=pb and pa<=pc else b if pb<=pc else c
                else:raise AssertionError(filter_type)
                row[x]=(row[x]+predict)&255
        pixels[y*width:(y+1)*width]=row;previous=row
    def rgba(x,y):
        index=pixels[y*width+x];return tuple(palette[index*3:index*3+3])+(alpha[index] if index<len(alpha) else 255,)
    return palette,alpha,rgba

banks=[read_png(ROOT/f'water-{i}.png') for i in range(2)]
assert banks[0][:2]==banks[1][:2], 'banks must share their palette and alpha entries'
def pixel(frame,x,y):
    cell=frame%12
    return banks[frame//12][2](cell%4*768+x//2,cell//4*512+y//2)

protected=[(700,520),(1000,350),(560,130),(900,620),(744,450),(900,730),(1267,850),(161,614),(1040,225)]
water=[(100,100),(100,900),(1400,100),(1300,200),(750,970),(1050,970),(600,870),(500,930),(1430,300),(100,700)]
for frame in range(24):
    for x,y in protected:assert pixel(frame,x,y)[3]==0,(frame,x,y,'animated land')
    for x,y in water:assert pixel(frame,x,y)[3]>=250,(frame,x,y,'missing water')
assert any(pixel(0,x,y)!=pixel(7,x,y) for x,y in water),'water frames are identical'
# The end-to-start step should be comparable to other steps, not a visible reset.
def difference(a,b):return sum(sum(abs(u-v) for u,v in zip(pixel(a,x,y)[:3],pixel(b,x,y)[:3])) for x,y in water)
steps=[difference(i,i+1) for i in range(23)]
assert difference(23,0)<=max(steps)*1.5+10,(difference(23,0),steps)
print('PASS actual water banks: shared palette, transparent fixed scenery, opaque moving sea, changing frames and bounded loop seam')
