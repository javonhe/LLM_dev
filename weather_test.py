import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_city_code(city_pinyin, api_key):
    """通过城市拼音获取行政编码"""
    geo_url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": api_key,
        "address": city_pinyin,
        "city": city_pinyin  # 增加城市限定提高准确性
    }
    
    try:
        response = requests.get(geo_url, params=params, verify=False)
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            return data["geocodes"][0]["adcode"]
        print(f"未找到城市: {city_pinyin}")
    except Exception as e:
        print(f"地理编码查询失败: {str(e)}")
    return None


def get_weather(adcode, api_key, forecast=False):
    """查询天气（支持未来预报）"""
    weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": api_key,
        "city": adcode,
        "extensions": "all" if forecast else "base",
        "output": "JSON"
    }
    
    try:
        response = requests.get(weather_url, params=params, verify=False)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"天气查询失败: {str(e)}")
    return None


def display_weather(data):
    """展示天气信息"""
    if data and data["status"] == "1":
        weather = data["lives"][0]
        print(f"城市: {weather['province']}{weather['city']}")
        print(f"天气: {weather['weather']}")
        print(f"温度: {weather['temperature']}℃")
        print(f"湿度: {weather['humidity']}%")
        print(f"风速: {weather['windpower']}级")
        print(f"发布时间: {weather['reporttime']}")
    else:
        print("获取天气信息失败")

def display_forecast(data):
    """展示未来天气预报"""
    if data and data["status"] == "1":
        forecasts = data["forecasts"][0]["casts"]
        print(f"【{data['forecasts'][0]['city']}未来天气预报】")
        for day in forecasts[1:3]:  # 展示未来2天预报
            print(f"\n日期: {day['date']}")
            print(f"白天: {day['dayweather']} {day['daytemp']}℃ {day['daywind']}风{day['daypower']}级")
            print(f"夜间: {day['nightweather']} {day['nighttemp']}℃ {day['nightwind']}风{day['nightpower']}级")
    else:
        print("获取预报失败")


if __name__ == "__main__":
    api_key = os.environ.get("AMAP_API_KEY")
    if not api_key:
        print("请设置环境变量 AMAP_API_KEY")
        exit(1)

    city = input("请输入城市拼音（如shanghai）: ").strip()
    adcode = get_city_code(city, api_key)
    
    if adcode:
        # 查询实时天气
        realtime_data = get_weather(adcode, api_key)
        display_weather(realtime_data)
        
        # 查询未来天气
        forecast_data = get_weather(adcode, api_key, forecast=True)
        display_forecast(forecast_data)