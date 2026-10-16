"""One forecast call per cache window. No credentials in logs, browser or URLs returned."""
import json,time,threading,hashlib,os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError,URLError
class WeatherError(Exception):pass
class WeatherClient:
 def __init__(self,directory,opener=urlopen):
  self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
  self.lock=threading.Lock();self.opener=opener;self.retry={}
 def fetch(self,key,query,ttl=900):
  if not key or not query:raise WeatherError('请填写 API Key 和城市 / API key and location required')
  ttl=max(300,int(ttl))
  cache=self.directory/(hashlib.sha256((query+'\0'+key).encode()).hexdigest()+'.json')
  with self.lock:
   old=None
   try:old=json.loads(cache.read_text())
   except (OSError,ValueError):pass
   if old and 0<=time.time()-old['fetched_at']<ttl:return old['payload'],False,None
   backoff=self.retry.get(str(cache))
   if backoff and time.time()<backoff[0]:
    if old:return old['payload'],True,backoff[1]
    raise WeatherError(backoff[1])
   url='https://api.weatherapi.com/v1/forecast.json?'+urlencode({'key':key,'q':query,'days':3,'aqi':'no','alerts':'no'})
   try:
    with self.opener(url,timeout=20) as r:payload=json.load(r)
    if payload.get('error'):raise WeatherError('WeatherAPI 返回错误 / provider error')
    if not payload.get('location') or not payload.get('current'):raise WeatherError('天气响应不完整 / invalid weather response')
    raw=json.dumps({'fetched_at':time.time(),'payload':payload});tmp=cache.with_suffix('.tmp')
    tmp.write_text(raw);tmp.chmod(0o600);tmp.replace(cache)
    self.retry.pop(str(cache),None)
    return payload,False,None
   except HTTPError as e:
    try:code=json.load(e).get('error',{}).get('code')
    except Exception:code=None
    messages={1002:'缺少 Key / API key missing',1006:'城市未找到 / location not found',2006:'Key 无效 / invalid API key',2007:'调用额度已用完 / quota exceeded',2008:'Key 已停用 / key disabled',2009:'套餐不支持此请求 / plan does not allow request'}
    message=messages.get(code,f'天气服务错误 / Weather service error ({e.code})')
   except (URLError,TimeoutError,OSError,ValueError,WeatherError):message='天气服务暂不可用 / weather service unavailable'
   self.retry[str(cache)]=(time.time()+300,message)
   if old:return old['payload'],True,message
   raise WeatherError(message)
