import json
import requests
import os
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import urllib3
from typing import List, Dict, Optional, Union
import sqlite3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 常量定义
GPT_MODEL = "gpt-3.5-turbo"
MAX_RETRIES = 3
RETRY_MULTIPLIER = 1
MAX_WAIT = 40


def check_environment() -> None:
    """
    检查必要的环境变量是否存在
    Raises:
        EnvironmentError: 当缺少必要的环境变量时
    """
    required_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


@retry(wait=wait_random_exponential(multiplier=RETRY_MULTIPLIER, max=MAX_WAIT),
       stop=stop_after_attempt(MAX_RETRIES))
def chat_completion_request(
    messages: List[Dict],
    functions: Optional[List[Dict]] = None,
    function_call: Optional[Dict] = None,
    model: str = GPT_MODEL
) -> Union[requests.Response, Exception]:
    """
    发送聊天补全请求到OpenAI API

    Args:
        messages: 对话消息列表
        functions: 可用的函数列表
        function_call: 函数调用信息
        model: 使用的模型名称

    Returns:
        Response对象或Exception对象
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("OPENAI_API_KEY"),
    }

    base = os.getenv("OPENAI_BASE_URL") + "/chat/completions"

    # 设定请求的JSON数据，包括GPT 模型名和要进行补全的消息
    json_data = {"model": model, "messages": messages}

    # 如果传入了functions，将其加入到json_data中
    if functions is not None:
        json_data.update({"functions": functions})

    # 如果传入了function_call，将其加入到json_data中
    if function_call is not None:
        json_data.update({"function_call": function_call})

    try:
        # 创建会话并禁用证书验证
        session = requests.Session()
        session.verify = False

        # 使用会话发送请求
        response = session.post(
            base,
            headers=headers,
            json=json_data,
        )
        return response

    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


def process_chat_response(messages: List[Dict], functions: Optional[List[Dict]] = None) -> Dict:
    """
    处理聊天请求并返回助手消息

    Args:
        messages: 对话消息列表
        functions: 可选的函数列表

    Returns:
        Dict: 助手的回复消息
    """
    chat_response = chat_completion_request(
        messages, functions=functions
    )

    if isinstance(chat_response, Exception):
        print(f"Error occurred: {chat_response}")
        exit(1)

    if chat_response.status_code != 200:
        print(f"Error: API returned status code {chat_response.status_code}")
        print(f"Response: {chat_response.text}")
        exit(1)

    # 解析返回的JSON数据，获取助手的回复消息
    response_data = chat_response.json()
    if "choices" not in response_data:
        print(f"Error: Unexpected API response format")
        print(f"Response: {response_data}")
        exit(1)

    return response_data["choices"][0]["message"]


def add_message(messages: List[Dict], role: str, content: str, name: str = None) -> None:
    """
    向消息列表添加新消息

    Args:
        messages: 消息列表
        role: 消息角色
        content: 消息内容
        name: 函数名称（当role为"function"时需要）
    """
    message = {
        "role": role,
        "content": content
    }

    if role == "function" and name is not None:
        message["name"] = name

    messages.append(message)


def pretty_print_conversation(messages: List[Dict]) -> None:
    """
    格式化打印对话内容

    Args:
        messages: 包含对话消息的列表
    """
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }

    for message in messages:
        role = message["role"]
        color = role_to_color.get(role, "white")

        if role == "system":
            print(colored(f"system: {message['content']}\n", color))
        elif role == "user":
            print(colored(f"user: {message['content']}\n", color))
        elif role == "assistant" and message.get("function_call"):
            print(colored(f"assistant[function_call]: {message['function_call']}\n", color))
        elif role == "assistant":
            print(colored(f"assistant[content]: {message['content']}\n", color))
        elif role == "function":
            print(colored(f"function ({message['name']}): {message['content']}\n", color))


def create_weather_function_schema(name: str, description: str, additional_params: Dict = None) -> Dict:
    """
    创建天气相关函数的schema

    Args:
        name: 函数名称
        description: 函数描述
        additional_params: 额外的参数定义

    Returns:
        Dict: 函数schema
    """
    base_params = {
        "location": {
            "type": "string",
            "description": "The city and state, e.g. shenzhen, china",
        }
    }

    if additional_params:
        base_params.update(additional_params)

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": base_params,
            "required": list(base_params.keys())
        }
    }


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

def display_forecast(data, days=2):
    """展示未来天气预报"""
    if data and data["status"] == "1":
        forecasts = data["forecasts"][0]["casts"]
        print(f"【{data['forecasts'][0]['city']}未来{days}天天气预报】")

        # 限制最大天数为实际数据长度减1（去掉当天）
        max_days = len(forecasts) - 1
        days = min(days, max_days) if days > 0 else 1

        for day in forecasts[1:1+days]:  # 从第二天开始取指定天数
            print(f"\n日期: {day['date']}")
            print(f"白天: {day['dayweather']} {day['daytemp']}℃ {day['daywind']}风{day['daypower']}级")
            print(f"夜间: {day['nightweather']} {day['nighttemp']}℃ {day['nightwind']}风{day['nightpower']}级")

        if days < max_days:
            print(f"\n（最多可查询{max_days}天预报）")
    else:
        print("获取预报失败")


def get_current_weather(city: str) -> str:
    """获取当前天气"""
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        return "错误：未设置高德地图API密钥(AMAP_API_KEY)"

    adcode = get_city_code(city, api_key)
    if not adcode:
        return f"无法找到城市: {city}"

    realtime_data = get_weather(adcode, api_key)
    if realtime_data and realtime_data["status"] == "1":
        weather = realtime_data["lives"][0]
        return f"{weather['province']}{weather['city']}当前天气: {weather['weather']}, 温度: {weather['temperature']}℃, 湿度: {weather['humidity']}%, 风力: {weather['windpower']}级, 发布时间: {weather['reporttime']}"
    else:
        return "获取天气信息失败"

def get_forecast_weather(city: str, days: int) -> str:
    """获取未来天气预报"""
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        return "错误：未设置高德地图API密钥(AMAP_API_KEY)"

    adcode = get_city_code(city, api_key)
    if not adcode:
        return f"无法找到城市: {city}"

    forecast_data = get_weather(adcode, api_key, forecast=True)
    if forecast_data and forecast_data["status"] == "1":
        forecasts = forecast_data["forecasts"][0]["casts"]
        city_name = forecast_data["forecasts"][0]["city"]

        max_days = len(forecasts) - 1
        days = min(days, max_days) if days > 0 else 1

        result = f"【{city_name}未来{days}天天气预报】\n"
        for day in forecasts[1:1+days]:
            result += f"\n日期: {day['date']}\n"
            result += f"白天: {day['dayweather']} {day['daytemp']}℃ {day['daywind']}风{day['daypower']}级\n"
            result += f"夜间: {day['nightweather']} {day['nighttemp']}℃ {day['nightwind']}风{day['nightpower']}级\n"

        return result
    else:
        return "获取预报失败"

def execute_function_call(function_call):
    """
    执行函数调用并返回结果

    Args:
        function_call: 函数调用信息

    Returns:
        str: 函数执行结果
    """
    function_name = function_call.get("name")
    function_args = json.loads(function_call.get("arguments", "{}"))

    if function_name == "get_current_weather":
        location = function_args.get("location")
        return get_current_weather(location)

    elif function_name == "get_n_day_weather_forecast":
        location = function_args.get("location")
        num_days = function_args.get("num_days", 2)
        return get_forecast_weather(location, num_days)

    return f"未知的函数: {function_name}"


def main():
    """主函数"""
    try:
        check_environment()

        # 定义可用的函数
        functions = [
            create_weather_function_schema(
                "get_current_weather",
                "Get the current weather"
            ),
            create_weather_function_schema(
                "get_n_day_weather_forecast",
                "Get an N-day weather forecast",
                {
                    "num_days": {
                        "type": "integer",
                        "description": "The number of days to forecast"
                    }
                }
            )
        ]

        # 初始化对话
        messages = []
        add_message(messages, "system",
            "使用中文回答问题。如果用户请求不明确，请询问更多细节。"
            "你是一个友好的天气助手，可以提供天气信息。")

        print(colored("欢迎使用天气助手！您可以询问任何地点的天气情况。", "cyan"))
        print(colored("输入'退出'结束对话。", "cyan"))

        # 开始对话循环
        while True:
            user_input = input(colored("\n您: ", "green"))
            if user_input.lower() in ['退出', 'exit', 'quit']:
                print(colored("谢谢使用，再见！", "cyan"))
                break

            # 添加用户输入到对话
            add_message(messages, "user", user_input)

            # 打印当前对话内容
            print(colored("\n当前对话内容:", "yellow"))
            pretty_print_conversation(messages)

            # 处理助手回复
            assistant_message = process_chat_response(messages, functions=functions)
            messages.append(assistant_message)

            # 打印当前对话内容
            print(colored("\n当前对话内容:", "yellow"))
            pretty_print_conversation(messages)

            # 检查是否有函数调用
            if assistant_message.get("function_call"):
                print(colored(f"正在获取天气信息...", "yellow"))

                # 执行函数调用
                function_result = execute_function_call(assistant_message["function_call"])

                # 添加函数结果到对话
                add_message(messages, "function", function_result, assistant_message["function_call"]["name"])

                # 获取下一个助手回复
                assistant_message = process_chat_response(messages, functions=functions)
                messages.append(assistant_message)

            # 打印助手回复
            print(colored(f"助手: {assistant_message.get('content', '')}", "cyan"))

    except Exception as e:
        print(f"错误: {e}")
        exit(1)

if __name__ == "__main__":
    main()