import requests
import simplejson
import time
import os
import openai
import httpx

from model import Model
from utils import LOG
from openai import OpenAI

class OpenAIModel(Model):
    def __init__(self, model: str):
        self.model = model
        # 创建禁用 SSL 验证的 httpx 客户端
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            http_client=http_client
        )

        # 禁用 SSL 警告（可选）
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def make_request(self, prompt):
        attempts = 0
        while attempts < 3:
            try:
                if self.model == "gpt-3.5-turbo":
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    translation = response.choices[0].message.content.strip()
                else:
                    response = self.client.completions.create(
                        model=self.model,
                        prompt=prompt,
                        max_tokens=150,
                        temperature=0
                    )
                    translation = response.choices[0].text.strip()

                return translation, True
            except openai.RateLimitError as e:
                attempts += 1
                if attempts < 3:
                    LOG.warning("Rate limit reached. Waiting for 60 seconds before retrying.")
                    time.sleep(60)
                else:
                    raise Exception("Rate limit reached. Maximum attempts exceeded.")
            except openai.APIConnectionError as e:
                print("The server could not be reached")
                print(e.__cause__)  # an underlying Exception, likely raised within httpx.            except requests.exceptions.Timeout as e:
            except openai.APIStatusError as e:
                print("Another non-200-range status code was received")
                print(e.status_code)
                print(e.response)
            except Exception as e:
                raise Exception(f"发生了未知错误：{e}")
        return "", False
