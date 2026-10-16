# English integration guide

Use Python 3.10+, install requirements.txt into a virtual environment, run `python tools/build_assets.py`, then `python src/server.py`. Open localhost:8765. The gallery works without credentials. Expand the setup section and enter your own WeatherAPI key and location. Settings stay outside the repository; the API never returns the key.

The local renderer accepts WeatherAPI's forecast response. Request `forecast.json` with `key`, `q`, `days=3`, `aqi=no`, `alerts=no` over HTTPS. This single response supplies current observations and forecasts. Local language switching does not require another provider request. Actual forecast availability depends on your subscription.

```python
from model import normalize
from render import render
model = normalize(payload, lang="en", city="San Francisco")
render(model).save("screen.png")
```

Put src/ on your Python module search path. Output is a continuous grayscale 400×300 PNG, ready for the device's gray16 conversion. Preserve smooth grayscale; avoid thresholding, indexed palettes or dithering before sending it to the firmware.

The date and observation timestamp use location.tz_id. Missing forecast dates use explicit placeholders. Unknown weather codes use a question mark. A stale observation is labeled after one hour. Network failures retain the last cached observation with an offline label; credentials never appear in error messages. Invalid keys, quota errors, missing locations and plan access failures have explicit safe messages.

The default API cache interval is 15 minutes (roughly 96 provider requests per city per day). Requests within a process are serialized; failed requests back off for at least five minutes. A production multi-instance service needs shared caching/rate limiting. The localhost app is not intended to be exposed as a public web service.

All 60 provider codes have day/night icon mappings, short Chinese and English labels, and preview images. The original vector paths live in src/icons.py; reusable transparent PNGs and SVGs live in assets/icons/. Eleven weather-and-glass plates are edited directly from the approved reference. The glass rim is baked into each plate and never procedurally redrawn; text and icons remain live and data-driven. The image generation tool is not needed at runtime.

The bundled examples are fixed design fixtures, not live conditions. Live-provider validation requires a user-supplied key. The project runs independently and exports PNGs. No device SDK, firmware or device transport is included. Use your own display software to send the rendered image to hardware.
