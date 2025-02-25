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


def add_message(messages: List[Dict], role: str, content: str) -> None:
    """
    向消息列表添加新消息
    
    Args:
        messages: 消息列表
        role: 消息角色
        content: 消息内容
    """
    messages.append({
        "role": role,
        "content": content
    })


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
            "description": "The city and state, e.g. San Francisco, CA",
        },
        "format": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use. Infer this from the users location.",
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


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """
    获取数据库中所有表的名称
    
    Args:
        conn: SQLite数据库连接对象
    
    Returns:
        List[str]: 数据库中所有表的名称列表
    
    Example:
        >>> conn = sqlite3.connect("database.db")
        >>> get_table_names(conn)
        ['users', 'products', 'orders']
    """
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [table[0] for table in tables.fetchall()]


def get_column_names(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """
    获取指定表的所有列名
    
    Args:
        conn: SQLite数据库连接对象
        table_name: 表名
    
    Returns:
        List[str]: 指定表的所有列名列表
    
    Example:
        >>> conn = sqlite3.connect("database.db")
        >>> get_column_names(conn, "users")
        ['id', 'name', 'email', 'created_at']
    """
    columns = conn.execute(f"PRAGMA table_info('{table_name}');").fetchall()
    return [col[1] for col in columns]


def get_database_info(conn: sqlite3.Connection) -> List[Dict[str, Union[str, List[str]]]]:
    """
    获取数据库的完整结构信息
    
    Args:
        conn: SQLite数据库连接对象
    
    Returns:
        List[Dict[str, Union[str, List[str]]]]: 包含每个表的名称和列信息的字典列表
        每个字典的格式为：{"table_name": str, "column_names": List[str]}
    
    Example:
        >>> conn = sqlite3.connect("database.db")
        >>> get_database_info(conn)
        [
            {"table_name": "users", "column_names": ["id", "name", "email"]},
            {"table_name": "orders", "column_names": ["id", "user_id", "total"]}
        ]
    """
    return [
        {
            "table_name": table_name,
            "column_names": get_column_names(conn, table_name)
        }
        for table_name in get_table_names(conn)
    ]


def ask_database(conn: sqlite3.Connection, query: str) -> str:
    """
    使用 query 来查询 SQLite 数据库
    
    Args:
        conn: 数据库连接对象
        query: SQL查询语句
    
    Returns:
        str: 查询结果或错误信息
    """
    try:
        # 执行查询并获取结果
        cursor = conn.execute(query)
        results = cursor.fetchall()
        
        if not results:
            return "Query returned no results."
            
        # 获取列名
        column_names = [description[0] for description in cursor.description]
        
        # 构建结果字符串
        result_str = f"Columns: {', '.join(column_names)}\n"
        result_str += "Results:\n"
        for row in results:
            result_str += f"{str(row)}\n"
            
        return result_str
        
    except Exception as e:
        return f"Query failed with error: {str(e)}"


def execute_function_call(message: Dict, conn: sqlite3.Connection) -> str:
    """
    执行函数调用
    
    Args:
        message: 包含函数调用信息的消息
        conn: 数据库连接对象
    
    Returns:
        str: 函数执行结果
    """
    if message["function_call"]["name"] == "ask_database":
        # 解析函数调用参数
        try:
            arguments = json.loads(message["function_call"]["arguments"])
            query = arguments["query"]
            return ask_database(conn, query)
        except json.JSONDecodeError:
            return "Error: Invalid JSON in function arguments"
        except KeyError:
            return "Error: Missing 'query' in function arguments"
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        return f"Error: function {message['function_call']['name']} does not exist"


def main():
    """主函数"""
    try:
        check_environment()
        
        # 连接数据库
        conn = sqlite3.connect("data/chinook.db")
        
        # 获取数据库信息并创建schema字符串
        database_schema = get_database_info(conn)
        database_schema_string = "\n".join(
            f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
            for table in database_schema
        )
        
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
            ),
            {
                "name": "ask_database",
                "description": "Use this function to answer user questions about music. Output should be a fully formed SQL query.",
                "parameters": 
                {
                    "type": "object",
                    "properties": 
                    {
                        "query": 
                        {
                            "type": "string",
                            "description": f"""
                                SQL query extracting info to answer the user's question.
                                SQL should be written using this database schema:
                                {database_schema_string}
                                The query should be returned in plain text, not in JSON.
                                """
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

        # # 初始化对话
        # messages = []
        # add_message(messages, "system", 
        #     "Don't make assumptions about what values to plug into functions. "
        #     "Ask for clarification if a user request is ambiguous.")
        
        # # 添加数据库信息到系统消息
        # add_message(messages, "system", 
        #     f"Available database schema:\n{database_schema_string}")
        
        # add_message(messages, "user", "What's the weather like today")

        # assistant_message = process_chat_response(messages, functions=functions)
        # messages.append(assistant_message)

        # add_message(messages, "user", "I'm in Shanghai, China.")
        # assistant_message = process_chat_response(messages, functions=functions)
        # messages.append(assistant_message)

        # # 打印对话历史
        # pretty_print_conversation(messages)

        conn = sqlite3.connect("data/chinook.db")
        database_schema_dict = get_database_info(conn)
        # 将数据库信息转换为字符串格式，方便后续使用
        database_schema_string = "\n".join(
            [
                f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
                for table in database_schema_dict
            ]
        )
        
        # 清空messages
        messages = []
        
        # 向消息列表中添加一个系统角色的消息，内容是 "Answer user questions by generating SQL queries against the Chinook Music Database."
        messages.append({"role": "system", "content": "Answer user questions by generating SQL queries against the Chinook Music Database."})

        # 向消息列表中添加一个用户角色的消息，内容是 "Hi, who are the top 5 artists by number of tracks?"
        messages.append({"role": "user", "content": "Hi, who are the top 5 artists by number of tracks?"})

        # 使用 chat_completion_request 函数获取聊天响应
        chat_response = chat_completion_request(messages, functions)

        # 从聊天响应中获取助手的消息
        assistant_message = chat_response.json()["choices"][0]["message"]

        # 将助手的消息添加到消息列表中
        messages.append(assistant_message)

        # 如果助手的消息中有功能调用
        if assistant_message.get("function_call"):
            # 使用 execute_function_call 函数执行功能调用，并获取结果
            results = execute_function_call(assistant_message, conn)
            # 将功能的结果作为一个功能角色的消息添加到消息列表中
            messages.append({"role": "function", "name": assistant_message["function_call"]["name"], "content": results})

        # 使用 pretty_print_conversation 函数打印对话
        pretty_print_conversation(messages)

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()