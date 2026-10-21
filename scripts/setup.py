"""Initial online setup. Subsequent demo launch uses only local files."""
import io
import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(args,**kw):subprocess.run(args,cwd=ROOT,check=True,**kw)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--regenerate-media',action='store_true',help='Explicitly replace prepared media; invalidates prior bundle identity');args=parser.parse_args()
    npm=shutil.which('npm') or 'npm'
    run([sys.executable,'-m','pip','install','-r','requirements.txt'])
    run([npm,'--prefix','frontend','ci','--no-audit','--no-fund'])
    tools=ROOT/'.tools';tools.mkdir(exist_ok=True)
    if not shutil.which('ffprobe') and not (tools/('ffprobe.exe' if os.name=='nt' else 'ffprobe')).exists():
        run([npm,'pack','ffprobe-static@3.1.0','--pack-destination',str(tools)])
        system={'Windows':'win32','Linux':'linux','Darwin':'darwin'}[platform.system()]
        arch='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
        name='ffprobe.exe' if os.name=='nt' else 'ffprobe'
        with tarfile.open(tools/'ffprobe-static-3.1.0.tgz') as archive:
            member=archive.extractfile(f'package/bin/{system}/{arch}/{name}')
            (tools/name).write_bytes(member.read())
        (tools/name).chmod(0o755)
    if args.regenerate_media or not (ROOT/'media/stream.mpd').exists():run([sys.executable,'scripts/prepare_media.py'])
    else:run([sys.executable,'scripts/prepare_media.py','--verify-only'])
    run([npm,'--prefix','frontend','run','build'])
    print('Prepared. Run python scripts/run.py. To create an ML model, follow README collection/training commands.')
