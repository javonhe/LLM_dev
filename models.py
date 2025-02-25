import os
from openai import OpenAI
import httpx

# 创建自定义HTTP客户端
http_client = httpx.Client(
    verify=False  # 禁用SSL验证
)

# 初始化OpenAI客户端时传入自定义配置
client = OpenAI(
    http_client=http_client
)

models = client.models.list()
print(models)