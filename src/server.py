#!/usr/bin/env python3
"""Local-only setup and renderer. API keys stay in private local settings."""
import os,json,secrets,threading,time,io
from pathlib import Path
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from provider import WeatherClient
from model import normalize
from render import png
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('WEATHER_GLASS_DATA') or Path.home()/'.zectrix/weather-glass')
DATA.mkdir(parents=True,exist_ok=True)
CONFIG=DATA/'settings.json';PORT=int(os.getenv('PORT','8765'))
TOKEN=secrets.token_urlsafe(32);lock=threading.RLock();render_lock=threading.Lock();wake=threading.Event()
try:config=json.loads(CONFIG.read_text())
except (OSError,ValueError):config={}
config={'query':'San Francisco','lang':'zh','city_zh':'旧金山','city_en':'San Francisco','interval':900,**config}
client=WeatherClient(DATA/'cache')
state={'ready':False,'busy':False,'sample':True,'error':None};current_png=None

def key():return os.getenv('WEATHERAPI_KEY') or config.get('api_key','')
def public_config():return {k:config[k] for k in ('query','lang','city_zh','city_en','interval')} | {'has_key':bool(key())}
def refresh():
 global current_png
 if not render_lock.acquire(blocking=False):return
 state['busy']=True
 try:
  with lock:c=dict(config);api_key=key()
  if api_key:
   payload,cached,error=client.fetch(api_key,c['query'],c['interval']);now=None
  else:
   payload=json.loads((ROOT/'examples/forecast.json').read_text());cached=False;error=None
   now=datetime.fromtimestamp(payload['current']['last_updated_epoch'],timezone.utc)
  m=normalize(payload,c['lang'],c.get('city_'+c['lang']) or None,now)
  if cached:
   m['stale']=True;m['updated']=('离线 · ' if c['lang']=='zh' else 'Offline · ')+m['updated']
  current_png=png(m)
  state.update(ready=True,sample=not bool(api_key),error=error,model=m)
  (DATA/'screen.png').write_bytes(current_png)
 except Exception:
  # Provider errors are already credential-safe; do not expose arbitrary exception URLs.
  import sys
  from provider import WeatherError
  e=sys.exc_info()[1];state['error']=str(e) if isinstance(e,WeatherError) else '更新失败，请检查配置 / update failed; check configuration'
 finally:state['busy']=False;render_lock.release()
def loop():
 while True:
  refresh();wake.wait(60);wake.clear()
def save():
 tmp=CONFIG.with_suffix('.tmp');tmp.write_text(json.dumps(config,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(CONFIG)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def allowed(self,write=False):
  hosts=[f'127.0.0.1:{PORT}',f'localhost:{PORT}'];origin=self.headers.get('Origin')
  return self.headers.get('Host') in hosts and (not origin or origin in ['http://'+h for h in hosts]) and (not write or self.headers.get('X-Preview-Token')==TOKEN)
 def reply(self,data,code=200,mime='application/json'):
  raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
  self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if not self.allowed():return self.reply({'error':'Local access only'},403)
  path=urlsplit(self.path).path
  if path=='/api/boot':return self.reply({'token':TOKEN})
  if path=='/api/status':return self.reply({**state,'config':public_config()})
  if path=='/screen.png':return self.reply(current_png,200,'image/png') if current_png else self.reply({'error':'Rendering'},503)
  if path=='/':return self.reply((ROOT/'index.html').read_bytes(),mime='text/html; charset=utf-8')
  if path.startswith(('/preview/','/assets/icons/','/data/gallery.json')):
   f=(ROOT/path.lstrip('/')).resolve()
   if f.is_relative_to(ROOT) and f.is_file():
    mime='image/png' if f.suffix=='.png' else 'image/svg+xml' if f.suffix=='.svg' else 'application/json'
    return self.reply(f.read_bytes(),mime=mime)
  return self.reply({'error':'Not found'},404)
 def do_POST(self):
  if not self.allowed(True):return self.reply({'error':'Refresh local page'},403)
  path=urlsplit(self.path).path
  try:
   n=int(self.headers.get('Content-Length',0))
   if not 0<n<8192:raise ValueError('Invalid request size')
   body=json.loads(self.rfile.read(n))
   if path=='/api/settings':
    with lock:
     new=dict(config)
     for k in ('query','city_zh','city_en'):
      if k in body:
       if not isinstance(body[k],str) or len(body[k])>200:raise ValueError('Invalid location')
       new[k]=body[k].strip()
     if not new['query']:raise ValueError('Location is required')
     if 'lang' in body:
      if body['lang'] not in ('zh','en'):raise ValueError('Invalid language')
      new['lang']=body['lang']
     if 'interval' in body:new['interval']=max(300,min(21600,int(body['interval'])))
     if body.get('api_key'):
      if not isinstance(body['api_key'],str) or len(body['api_key'])>256:raise ValueError('Invalid key')
      new['api_key']=body['api_key'].strip()
     config.clear();config.update(new);save()
    wake.set();return self.reply({'ok':True})
   if path=='/api/refresh':wake.set();return self.reply({'ok':True})
   return self.reply({'error':'Not found'},404)
  except (ValueError,TypeError):return self.reply({'error':'请检查输入 / check input'},400)
if __name__=='__main__':
 threading.Thread(target=loop,daemon=True).start()
 print(f'Liquid Glass Weather: http://127.0.0.1:{PORT}/',flush=True)
 ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
