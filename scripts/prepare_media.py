"""Generate owned calibration content (testsrc2 + sine) or encode --source."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def binary(name):
    found=shutil.which(name)
    if found: return found
    local=ROOT/'.tools'/f'{name}.exe'
    if local.exists(): return str(local)
    if name=='ffmpeg':
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    candidates=list((ROOT/'.tools').rglob(f'{name}.exe'))
    if candidates: return str(candidates[0])
    raise RuntimeError(f'{name} missing. Install FFmpeg/FFprobe or put binaries in .tools')

def prepare(seconds=120,source=None,verify_only=False):
    out=ROOT/'media'; out.mkdir(exist_ok=True)
    ffmpeg=binary('ffmpeg')
    inputs=['-i',str(Path(source).resolve())] if source else ['-f','lavfi','-i','testsrc2=size=1280x720:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000']
    cmd=[ffmpeg,'-hide_banner','-y',*inputs,'-t',str(seconds),'-filter_complex','[0:v]split=4[a][b][c][d];[a]scale=426:240[v0];[b]scale=640:360[v1];[c]scale=854:480[v2];[d]scale=1280:720[v3]']
    for i in range(4): cmd+=['-map',f'[v{i}]']
    cmd+=['-map','0:a:0' if source else '1:a:0','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-r','24','-g','48','-keyint_min','48','-sc_threshold','0','-force_key_frames','expr:gte(t,n_forced*2)']
    for i,rate in enumerate([300,600,1200,2500]): cmd += [f'-b:v:{i}',f'{rate}k',f'-maxrate:v:{i}',f'{rate}k',f'-bufsize:v:{i}',f'{rate*2}k']
    cmd+=['-c:a','aac','-b:a','64k','-ac','1','-f','dash','-seg_duration','2','-use_template','1','-use_timeline','1','-init_seg_name','init-$RepresentationID$.mp4','-media_seg_name','chunk-$RepresentationID$-$Number%05d$.m4s','-adaptation_sets','id=0,streams=v id=1,streams=a','stream.mpd']
    if not verify_only:
        subprocess.run(cmd,cwd=out,check=True,stdout=subprocess.DEVNULL,stderr=(out/'encode.log').open('w'))
    ns={'m':'urn:mpeg:dash:schema:mpd:2011'}; tree=ET.parse(out/'stream.mpd'); reps=[]; segments=[]
    for adaptation in tree.findall('.//m:AdaptationSet',ns):
        for rep in adaptation.findall('m:Representation',ns):
            rid=rep.attrib['id']; template=rep.find('m:SegmentTemplate',ns)
            scale=int(template.attrib['timescale']); timeline=template.find('m:SegmentTimeline',ns)
            times=[]; cursor=0
            for s in timeline:
                cursor=int(s.get('t',cursor)); dur=int(s.get('d'))
                for _ in range(int(s.get('r','0'))+1): times.append((cursor/scale,dur/scale)); cursor+=dur
            reps.append({'id':rid,'bandwidth':int(rep.get('bandwidth')),'width':int(rep.get('width','0')),'height':int(rep.get('height','0')),'type':adaptation.get('contentType'),'segments':len(times),'duration':cursor/scale})
            assert (out/f'init-{rid}.mp4').exists()
            for number,(start,duration) in enumerate(times,1):
                path=out/f'chunk-{rid}-{number:05}.m4s'
                assert path.exists(),path
                segments.append({'asset':path.name,'representation':rid,'number':number,'start':start,'duration':duration,'bytes':path.stat().st_size})
    videos=[r for r in reps if r['type']=='video']; assert len(videos)==4
    timelines=[[ (s['start'],s['duration']) for s in segments if s['representation']==r['id']] for r in videos]
    assert all(t==timelines[0] for t in timelines)
    probe=binary('ffprobe'); probes=[]
    for r in reps:
        # FFprobe a genuine concatenated init + first media fragment.
        with tempfile.TemporaryDirectory(prefix='stallguard-probe-') as temporary:
            combined=Path(temporary)/'probe.mp4';combined.write_bytes((out/f"init-{r['id']}.mp4").read_bytes()+(out/f"chunk-{r['id']}-00001.m4s").read_bytes())
            info=json.loads(subprocess.check_output([probe,'-v','error','-show_streams','-of','json',str(combined)]))
        stream=info['streams'][0]; probes.append(stream)
        if r['type']=='video': assert (stream['width'],stream['height'])==(r['width'],r['height'])
    data={'asset_id':'calibration','title':'Generated motion calibration','license':'Locally generated FFmpeg testsrc2 and sine; no external source media' if not source else 'User-provided source; user responsible for rights','seconds':seconds,'segment_s':2,'representations':reps,'segments':segments,'ffprobe':probes,'encoding_command':cmd}
    if not verify_only:(out/'inventory.json').write_text(json.dumps(data,indent=2))
    print(json.dumps({'representations':reps,'aligned':True,'segment_count':len(segments)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--seconds',type=int,default=120); p.add_argument('--source'); p.add_argument('--verify-only',action='store_true'); a=p.parse_args(); prepare(a.seconds,a.source,a.verify_only)
