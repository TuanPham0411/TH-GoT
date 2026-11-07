import wave,math,struct,subprocess,json,hashlib
from pathlib import Path
root=Path('/tmp/got-realm-films');rate=44100;length=8
for name,base in [('environment',261.63),('animals',293.66),('transport',329.63)]:
 with wave.open(str(root/(name+'.wav')),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
  data=bytearray()
  for i in range(rate*length):
   t=i/rate;beat=int(t/.65);local=t%.65;note=[0,4,7,12,7,4,2,9,7,4,2,0][beat%12];freq=base*2**(note/12)
   envelope=min(1,local/.025)*math.exp(-local*5);fade=min(1,t/.4,(length-t)/.7)
   sample=(.10*math.sin(2*math.pi*freq*t)*envelope+.035*math.sin(2*math.pi*base/2*t)+.014*math.sin(2*math.pi*base*.75*t))*max(0,fade)
   data.extend(struct.pack('<h',int(sample*32767)))
  w.writeframes(data)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','0.3','-i',str(root/(name+'.webm')),'-i',str(root/(name+'.wav')),'-t','8','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart',str(root/(name+'.mp4'))],check=True)
p=Path(__file__).resolve().parents[1]/'game/realm-assets.json';manifest=json.loads(p.read_text());local=json.loads(Path('/tmp/got-realm-local.json').read_text())
for name in ['environment','animals','transport']:
 file=root/(name+'.mp4');body=file.read_bytes();sha=hashlib.sha256(body).hexdigest();id='film-'+name
 manifest[id]={'path':f'videos/realm-v13/{sha[:16]}-{name}.mp4','sha256':sha,'bytes':len(body),'mime':'video/mp4','width':1280,'height':720,'seconds':8};local[id]=str(file)
p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');Path('/tmp/got-realm-local.json').write_text(json.dumps(local))
print('Three original 8-second 2D motion films encoded')
