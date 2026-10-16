"""Rebuild the review gallery and all code/day/night/language examples offline."""
from pathlib import Path
import sys,json,copy
from datetime import datetime
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import icons
from model import normalize
from render import render,font
NOW=datetime.fromisoformat('2026-10-16T10:30:00-07:00')
BASE=json.loads((ROOT/'examples/forecast.json').read_text())
FEATURED=[1003,1000,1009,1183,1195,1276,1213,1117,1204,1198,1237,1135,1012,1024]
gallery=[];mapping={}
for code in [*icons.CONDITIONS,None]:
 k=icons.kind(code);mapping[str(code) if code else 'unknown']={'family':k,'zh':icons.label(code,True,'zh'),'en':icons.label(code,True,'en'),'day':f'{code or "unknown"}-day.svg','night':f'{code or "unknown"}-night.svg'}
 for day in (True,False):
  phase='day' if day else 'night';name=f'{code or "unknown"}-{phase}'
  (ROOT/'assets/icons'/f'{name}.svg').write_text(icons.svg(k,day))
  for size in (32,48,96):
   directory=ROOT/'assets/icons'/str(size);directory.mkdir(exist_ok=True)
   im=Image.new('RGBA',(size,size),(0,0,0,0));im.putalpha(icons.mask(k,day,size));im.save(directory/f'{name}.png')
  row={'id':name,'code':code,'phase':phase,'featured':code in FEATURED,'zh':icons.label(code,day,'zh'),'en':icons.label(code,day,'en'),'images':{}}
  data=copy.deepcopy(BASE);cur=data['current'];cur['condition']['code']=code;cur['is_day']=int(day)
  temp=18
  if any(v in k for v in ['snow','blizzard']):temp=-6
  elif any(v in k for v in ['freezing','sleet','ice']):temp=-1
  elif any(v in k for v in ['rain','drizzle','thunder']):temp=14
  elif k=='clear':temp=24
  if not day:temp-=3
  cur.update(temp_c=temp,feelslike_c=temp-2,uv=3.5 if day else 0)
  data['forecast']['forecastday'][0]['day'].update(maxtemp_c=temp+2,mintemp_c=temp-5,condition={'code':code},daily_chance_of_snow=85 if 'snow' in k or 'blizzard' in k else 0)
  data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']=85 if 'rain' in k else 40
  for j in (1,2):
   future=data['forecast']['forecastday'][j]['day'];future.update(maxtemp_c=temp+j,mintemp_c=temp-5-j)
   if temp<0:future['condition']['code']=1213 if j==1 else 1003;future['daily_chance_of_snow']=65 if j==1 else 20
  if not day:cur['last_updated_epoch']=int(NOW.replace(hour=21,minute=30).timestamp())
  if code==1003 and day:data=copy.deepcopy(BASE)
  for lang in ('zh','en'):
   now=NOW if day else NOW.replace(hour=21,minute=30)
   m=normalize(data,lang,'旧金山' if lang=='zh' else 'San Francisco',now)
   file=f'{name}-{lang}.png';render(m).save(ROOT/'preview'/file);row['images'][lang]='preview/'+file
  gallery.append(row)
 print('Rendered',code,flush=True)
(ROOT/'data/gallery.json').write_text(json.dumps(gallery,ensure_ascii=False,indent=2))
(ROOT/'assets/icons/mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
# 14 representative weather states in each language, plus a day/night comparison.
for lang in ('zh','en'):
 sheet=Image.new('RGB',(1200,5*340),'#eeeeeb');d=ImageDraw.Draw(sheet)
 for i,code in enumerate(FEATURED):
  x=(i%3)*400;y=(i//3)*340
  sheet.paste(Image.open(ROOT/'preview'/f'{code}-day-{lang}.png'),(x,y+28))
  d.text((x+12,y+7),icons.label(code,True,lang),font=font(4,True,lang=='zh'),fill='#222')
 sheet.save(ROOT/'preview'/f'overview-{lang}.jpg',quality=94)
compare=Image.new('RGB',(800,4*300))
for i,(code,phase) in enumerate([(1003,'day'),(1276,'day'),(1213,'day'),(1000,'night')]):
 for j,lang in enumerate(('zh','en')):compare.paste(Image.open(ROOT/'preview'/f'{code}-{phase}-{lang}.png'),(j*400,i*300))
compare.save(ROOT/'preview/bilingual-review.png')
print('Built',len(gallery)*2,'cards; all 60 codes, unknown fallback, day/night and two languages')
