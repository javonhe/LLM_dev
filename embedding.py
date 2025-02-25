# pandas 提供了 DataFrame 数据结构，方便进行数据的读取、处理、分析等操作。
import pandas as pd
# 导入 tiktoken 库。Tiktoken 是 OpenAI 开发的一个库，用于从模型生成的文本中计算 token 数量。
import tiktoken
import tiktoken.load
import requests

# 在导入pandas后添加显示配置
pd.set_option("display.max_columns", None)  # 显示所有列
pd.set_option("display.max_rows", None)     # 显示所有行
pd.set_option("display.max_colwidth", 30)  # 设置列最大宽度为100字符
pd.set_option("display.width", 1000)        # 设置整体输出宽度

input_datapath = "data/fine_food_reviews_1k.csv"
df = pd.read_csv(input_datapath, index_col=0)
df = df[["Time", "ProductId", "UserId", "Score", "Summary", "Text"]]
df = df.dropna()

# 将 "Summary" 和 "Text" 字段组合成新的字段 "combined"
df["combined"] = (
    "Title: " + df.Summary.str.strip() + "; Content: " + df.Text.str.strip()
)

# 模型类型
embedding_model = "text-embedding-ada-002"

# text-embedding-ada-002 模型对应的分词器（TOKENIZER）
embedding_encoding = "cl100k_base"

# text-embedding-ada-002 模型支持的输入最大 Token 数是8191，向量维度 1536
max_tokens = 8000 

# 设置要筛选的评论数量为1000
top_n = 1000

# 对DataFrame进行排序，基于"Time"列，然后选取最后的2000条评论。
# 这个假设是，我们认为最近的评论可能更相关，因此我们将对它们进行初始筛选。
df = df.sort_values("Time").tail(top_n * 2) 

# 丢弃"Time"列，因为我们在这个分析中不再需要它。
df.drop("Time", axis=1, inplace=True)

# 创建自定义会话
session = requests.Session()
session.verify = False  # 禁用证书验证

# 覆盖tiktoken的下载函数
def custom_download(url: str) -> bytes:
    return session.get(url).content

tiktoken.load.read_file = custom_download    # 覆盖文件读取函数

# 从'embedding_encoding'获取编码
encoding = tiktoken.get_encoding(embedding_encoding)

# 计算每条评论的token数量。我们通过使用encoding.encode方法获取每条评论的token数，然后把结果存储在新的'n_tokens'列中。
df["n_tokens"] = df.combined.apply(lambda x: len(encoding.encode(x)))

# 如果评论的token数量超过最大允许的token数量，我们将忽略（删除）该评论。
# 我们使用.tail方法获取token数量在允许范围内的最后top_n（1000）条评论。
df = df[df.n_tokens <= max_tokens].tail(top_n)

# 打印出剩余评论的数量。
print(len(df))