"""WeatherAPI forecast JSON -> bilingual model; units stay Celsius / km/h."""
import math
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from decimal import Decimal,ROUND_HALF_UP
import icons

def number(x):
 if isinstance(x,bool):return None
 try:x=float(x)
 except (TypeError,ValueError):return None
 return x if math.isfinite(x) else None

def rounded(x):
 n=number(x)
 if n is None:return '—'
 v=Decimal(str(n)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
 return str(abs(v) if v==0 else v)
def bounded(x,lo,hi):
 n=number(x);return n if n is not None and lo<=n<=hi else None

def normalize(payload,lang='zh',city=None,now=None):
 if lang not in ('zh','en'):raise ValueError('lang must be zh or en')
 if 'error' in payload:raise ValueError('WeatherAPI returned an error response')
 loc=payload.get('location') or {};cur=payload.get('current') or {}
 tz=ZoneInfo(loc.get('tz_id') or 'UTC');now=now or datetime.now(timezone.utc)
 if now.tzinfo is None:raise ValueError('now must include a timezone')
 local=now.astimezone(tz);epoch=number(cur.get('last_updated_epoch'));updated=None
 if epoch is not None:
  try:updated=datetime.fromtimestamp(epoch,tz)
  except (ValueError,OverflowError,OSError):pass
 if updated and updated>local+timedelta(minutes=5):updated=None
 stale=updated is None or (local-updated).total_seconds()>3600
 rawcode=(cur.get('condition') or {}).get('code');code=int(rawcode) if number(rawcode) is not None else None
 day=cur.get('is_day')!=0;zh=lang=='zh'
 wd=['周一','周二','周三','周四','周五','周六','周日'] if zh else ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
 date=f'{local.month}月{local.day}日 {wd[local.weekday()]}' if zh else f'{local:%b} {local.day} · {wd[local.weekday()]}'
 stamp=updated.strftime('%H:%M') if updated else '—'
 if updated and updated.date()!=local.date():stamp=updated.strftime('%m/%d %H:%M')
 stamp+=(' '+str(updated.tzname())) if updated else ''
 stamp=('数据旧 ' if zh else 'Stale ') + stamp if stale else ('更新 ' if zh else 'Updated ')+stamp
 rows=(payload.get('forecast') or {}).get('forecastday') or []
 dated={r.get('date'):r.get('day') or {} for r in rows if isinstance(r,dict)};days=[]
 for i in range(3):
  dt=local.date()+timedelta(days=i);d=dated.get(dt.isoformat(),{});dc=(d.get('condition') or {}).get('code');k=icons.kind(dc)
  snow=bounded(d.get('daily_chance_of_snow'),0,100);rain=bounded(d.get('daily_chance_of_rain'),0,100)
  snow_type=('snow' in k or 'blizzard' in k) and snow is not None
  p=snow if snow_type else rain
  days.append({'date':dt.isoformat(),'label':('今天' if zh else 'Today') if i==0 else wd[dt.weekday()], 'code':dc,'high':rounded(d.get('maxtemp_c')),'low':rounded(d.get('mintemp_c')),'precip':(('降雪 ' if zh else 'Snow ') if snow_type else ('降雨 ' if zh else 'Rain '))+('—' if p is None else rounded(p)+'%'),'available':bool(d)})
 wind=bounded(cur.get('wind_kph'),0,500);direction=cur.get('wind_dir','')
 dirs={'N':'北','NNE':'北东北','NE':'东北','ENE':'东东北','E':'东','ESE':'东东南','SE':'东南','SSE':'南东南','S':'南','SSW':'南西南','SW':'西南','WSW':'西西南','W':'西','WNW':'西西北','NW':'西北','NNW':'北西北'}
 direction=dirs.get(direction,'')+'风' if zh and direction in dirs else direction if direction in dirs else ''
 humidity=bounded(cur.get('humidity'),0,100);uv=bounded(cur.get('uv'),0,50)
 return {'lang':lang,'city':city or loc.get('name') or ('未知地点' if zh else 'Unknown location'),'date':date,'updated':stamp,'timezone':str(tz),'code':code,'day':day,'condition':icons.label(code,day,lang),'temp':rounded(cur.get('temp_c')),'feels':('体感 ' if zh else 'Feels ')+rounded(cur.get('feelslike_c'))+'°','high':days[0]['high'],'low':days[0]['low'],'wind':f'{direction} {rounded(wind)} km/h'.strip(),'humidity':('湿度 ' if zh else 'RH ')+('—' if humidity is None else rounded(humidity)+'%'),'uv':'UV '+('—' if uv is None else f'{uv:g}'),'days':days,'stale':stale,'observed_epoch':epoch,'rendered_epoch':int(now.timestamp())}
