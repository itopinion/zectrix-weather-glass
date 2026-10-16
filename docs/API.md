# WeatherAPI 接入约定

核对时间：2026-10-16。官方来源：[Forecast](https://www.weatherapi.com/docs/forecast-api/)、[Parameters](https://www.weatherapi.com/docs/request-parameters/)、[Condition codes](https://www.weatherapi.com/docs/weather-icons/)、[Attribution](https://www.weatherapi.com/docs/attribution/)。

## 请求

服务端 HTTPS GET `/v1/forecast.json`；`key` 为用户自己的密钥，`q` 为城市或经纬度，`days=3`，`aqi=no`，`alerts=no`。不要把 Key 放进前端源码、日志、截图或 GitHub。此包用 Python 标准库发起请求；只在传输请求本身的 URL 中包含 provider 要求的 key。

## 字段对应

| 画面 | 响应字段 |
|---|---|
| 地点 | 用户自定义中英文显示名；为空使用 location.name |
| 时区与日期 | location.tz_id；当地当前日期，不用电脑的时区 |
| 右上角更新时间 | current.last_updated_epoch 转换到城市时区 |
| 温度/体感 | current.temp_c / current.feelslike_c |
| 天气与昼夜 | current.condition.code / current.is_day |
| 风向/风速 | current.wind_dir / current.wind_kph |
| 湿度/UV | current.humidity / current.uv |
| 三天最高/最低温 | forecast.forecastday[].day.maxtemp_c / mintemp_c |
| 三天图标 | forecast.forecastday[].day.condition.code，采用日间概况图标 |
| 降雨/降雪概率 | daily_chance_of_rain / daily_chance_of_snow；雪类天气优先显示降雪概率 |

forecastday 按 date 匹配当地今天、明天、后天，不依赖返回数组顺序。地点翻译由显示名控制，不假设 provider 自动翻译城市。中文天气短标签与英文短标签保存在 icons.py；完整官方文字保存在 data/。

## 缓存与失败处理

同一进程通过锁合并并发请求。缓存键由城市与 Key 的 SHA-256 组成；中文英文共享。默认 TTL 900 秒，最小 300 秒。只请求 forecast，不再额外请求 current、astronomy。每次图片重绘不一定发起 API 请求。失败后 300 秒内不重复请求；旧缓存仍带原观测时间。当前实现是单进程缓存；多实例应集中缓存和限流。

| Code | 用户提示 |
|---|---|
| 1002 | 缺少 Key |
| 1006 | 城市未找到 |
| 2006 | Key 无效 |
| 2007 | 额度已用完 |
| 2008 | Key 已停用 |
| 2009 | 套餐不支持请求 |

不自动升级套餐或重试付费端点。预报天数依账户权限返回；不足三天的格子显示 `—`。原始响应包含的小时预报等字段可供扩展，此 400×300 版本只展示参考布局中的字段。

## 完整天气覆盖

data/weather_conditions.json 为本次获取的 60 个官方代码快照。assets/icons/mapping.json 为本项目视觉映射，包含昼夜资产。极端/少见代码也保留具体标签；多个强度可共用天气背景，以图标和文案区分。未来新增未知代码进入问号兜底，不映射成晴天。升级官方列表时请同时更新 groups.json、中文标签及测试。

## 本地 HTTP

仅监听 127.0.0.1。GET `/api/boot` 取得一次运行有效的 CSRF token；写入须携带 `X-Preview-Token`，并匹配 Host / Origin。

- GET `/api/status`：无密钥的配置、状态、规范化天气。
- GET `/screen.png`：当前 400×300 PNG。
- POST `/api/settings`：query、lang、city_zh、city_en、interval、api_key；Key 为空保留原值。
- POST `/api/refresh`：重新渲染，仍遵守天气缓存与退避。

settings.json 权限为 0600，属于本地明文配置，不是系统钥匙串。请勿分享该文件或缓存目录。开发页内提供 WeatherAPI 来源链接；墨卡画面按设计要求不放服务商文字。商用部署按所选服务条款确认署名及使用范围。
