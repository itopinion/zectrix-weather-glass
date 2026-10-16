import sys,unittest,json,copy,tempfile,io,time,threading
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from urllib.error import URLError,HTTPError
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import icons
from model import normalize,rounded
from render import render
from provider import WeatherClient,WeatherError
BASE=json.loads((ROOT/'examples/forecast.json').read_text());NOW=datetime.fromisoformat('2026-10-16T10:30:00-07:00')
class WeatherTests(unittest.TestCase):
 def test_all_codes_have_both_languages_assets_and_geometry(self):
  self.assertEqual(set(icons.CONDITIONS),set(icons.CODE_KIND));self.assertEqual(set(icons.CONDITIONS),set(icons.ZH))
  for code in icons.CONDITIONS:
   for day in [True,False]:
    self.assertIsNotNone(icons.mask(icons.kind(code),day,32).getbbox())
    self.assertNotIn('Unknown',icons.label(code,day,'en'))
 def test_unknown_is_not_sunny(self):
  self.assertEqual(icons.kind(9999),'unknown');self.assertEqual(icons.label(9999,True,'zh'),'天气未知')
 def test_city_timezone_and_dst(self):
  now=datetime.fromisoformat('2026-10-17T01:00:00+00:00')
  m=normalize(BASE,now=now);self.assertIn('10月16日',m['date']);self.assertIn('PDT',m['updated'])
  d=copy.deepcopy(BASE);d['current']['last_updated_epoch']=int(datetime.fromisoformat('2026-12-01T10:00:00-08:00').timestamp())
  self.assertIn('PST',normalize(d,now=datetime.fromisoformat('2026-12-01T10:05:00-08:00'))['updated'])
 def test_missing_forecast_does_not_reuse_previous_day(self):
  d=copy.deepcopy(BASE);d['forecast']['forecastday']=d['forecast']['forecastday'][:1]
  m=normalize(d,now=NOW);self.assertFalse(m['days'][1]['available']);self.assertEqual(m['days'][1]['high'],'—')
 def test_snow_probability_not_rain(self):
  d=copy.deepcopy(BASE);r=d['forecast']['forecastday'][0]['day'];r.update(condition={'code':1213},daily_chance_of_snow=80,daily_chance_of_rain=5)
  self.assertEqual(normalize(d,now=NOW)['days'][0]['precip'],'降雪 80%')
 def test_stale_and_invalid_values(self):
  d=copy.deepcopy(BASE);d['current'].update(humidity=150,uv=-2,temp_c=float('nan'))
  m=normalize(d,now=NOW+timedelta(hours=2));self.assertTrue(m['stale']);self.assertIn('数据旧',m['updated']);self.assertEqual(m['temp'],'—');self.assertEqual(m['humidity'],'湿度 —')
  self.assertEqual(rounded(-.2),'0');self.assertEqual(rounded(-2.5),'-3')
 def test_same_cached_response_for_concurrent_languages(self):
  calls=[]
  def opener(url,timeout):calls.append(url);time.sleep(.01);return io.BytesIO(json.dumps(BASE).encode())
  with tempfile.TemporaryDirectory() as d:
   c=WeatherClient(d,opener)
   with ThreadPoolExecutor(max_workers=8) as ex:values=list(ex.map(lambda _:c.fetch('test-key','London'),range(8)))
   self.assertEqual(len(calls),1);self.assertIn('days=3',calls[0]);self.assertTrue(all(x[0]==BASE for x in values))
 def test_failure_uses_cache_and_backs_off(self):
  calls=[]
  def good(url,timeout):calls.append(url);return io.BytesIO(json.dumps(BASE).encode())
  with tempfile.TemporaryDirectory() as d:
   c=WeatherClient(d,good)
   with patch('provider.time.time',return_value=1000):c.fetch('secret','London',300)
   def bad(url,timeout):calls.append(url);raise URLError('url contains secret')
   c.opener=bad
   with patch('provider.time.time',return_value=1400):
    first=c.fetch('secret','London',300);second=c.fetch('secret','London',300)
   self.assertTrue(first[1]);self.assertEqual(len(calls),2);self.assertNotIn('secret',first[2]);self.assertEqual(first,second)
 def test_error_code_is_safe(self):
  def bad(url,timeout):raise HTTPError(url,403,'secret',{},io.BytesIO(b'{"error":{"code":2007}}'))
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(WeatherError,'quota exceeded'):WeatherClient(d,bad).fetch('secret','London')
 def test_night_precipitation_keeps_weather_scene(self):
  self.assertEqual(icons.background(1183,False),'rain');self.assertEqual(icons.background(1213,False),'snow');self.assertEqual(icons.background(1000,False),'night')
 def test_layout_edges_and_continuous_grayscale(self):
  d=copy.deepcopy(BASE);d['current']['temp_c']=-123;d['current']['condition']['code']=1282
  for lang in ('zh','en'):
   im=render(normalize(d,lang,'A very long international metropolitan location label',NOW))
   self.assertEqual(im.size,(400,300));self.assertEqual(im.mode,'L');self.assertGreater(len(im.getcolors(256)),200)
if __name__=='__main__':unittest.main()
