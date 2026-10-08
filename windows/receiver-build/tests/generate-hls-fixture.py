from pathlib import Path
import argparse,subprocess
parser=argparse.ArgumentParser(description='Generate silent synthetic video for the isolated AirPlay HLS regression.')
parser.add_argument('--ffmpeg',default='ffmpeg')
args=parser.parse_args()
directory=Path(__file__).resolve().parent/'hls-fixture'
directory.mkdir(exist_ok=True)
subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y',
    '-f','lavfi','-i','testsrc2=size=640x360:rate=30',
    '-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','30',
    '-c:v','libx264','-preset','ultrafast','-g','60','-c:a','aac',
    '-f','hls','-hls_time','2','-hls_playlist_type','vod',str(directory/'video.m3u8')],check=True)
print('Created 30 seconds of synthetic video with silent audio.')
