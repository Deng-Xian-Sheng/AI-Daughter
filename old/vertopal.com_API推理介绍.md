## 概要

魔搭通过API-Inference，将开源模型服务化并通过API接口进行标准化，让开发者能以更轻量和迅捷的方式体验开源模型，并集成到不同的AI应用中，从而展开富有创造力的尝试，包括与工具结合调用，来构建多种多样的AI应用原型。

> \[!NOTE\]
> 具体使用的额度，请关注**使用限制**说明。欢迎广大开发者[提供反馈](https://modelscope.cn/docs/联系我们)。

## 前提条件：创建账号并获取Token

API-Inference面向ModelScope注册用户免费提供，请在登陆后获取您专属的访问令牌（Access
Token）。具体可以参见[账号注册和登陆](https://modelscope.cn/docs/账号注册与登录)以及[Token的管理](https://modelscope.cn/docs/访问令牌)等相关文档。
![img.png](https://resouces.modelscope.cn/document/docdata/2025-9-11_11:43/dist/%E6%A8%A1%E5%9E%8B%E6%9C%8D%E5%8A%A1/%E6%A8%A1%E5%9E%8B%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1/resources/token.png)

## 使用方法

### 大语言模型 LLM

当前魔搭平台的API-Inference，针对大语言模型提供OpenAI API兼容的接口。
对于LLM模型的API，使用前，请先安装OpenAI SDK:

``` 
pip install openai
```

> \[!NOTE\] 其他流行的接口也陆续支持中，例如[Anthropic
> API](https://docs.anthropic.com/en/api)，可参见下面的 "大语言模型
> LLM（Anthropic API兼容接口）" 部分。

安装后就可以通过标准的OpenAI调用方式使用。具体调用方式，在每个模型页面右侧的API-Inference范例中以提供，**请以模型页面的
API-Inference
示范代码为准**，尤其例如对于reasoning模型，调用的方式与标准LLM会有一些细微区别。以下范例仅供参考。

``` python
from openai import OpenAI

client = OpenAI(
    api_key="MODELSCOPE_ACCESS_TOKEN", # 请替换成您的ModelScope Access Token
    base_url="https://api-inference.modelscope.cn/v1/"
)


response = client.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-32B-Instruct", # ModleScope Model-Id
    messages=[
        {
            'role': 'system',
            'content': 'You are a helpful assistant.'
        },
        {
            'role': 'user',
            'content': '用python写一下快排'
        }
    ],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end='', flush=True)
```

在这个范例里，使用魔搭的API-Inference，有几个需要适配的有几个地方：

-   base url: 指向魔搭API-Inference服务
    `https://api-inference.modelscope.cn/v1/`。
-   api_key: 使用魔搭的访问令牌(Access Token),
    可以从您的魔搭账号中获取：<https://modelscope.cn/my/myaccesstoken>
    。
-   模型名字(model):使用魔搭上开源模型的Model
    Id，例如`Qwen/Qwen2.5-Coder-32B-Instruct` 。

### 大语言模型 LLM（Anthropic API兼容接口）

针对LLM模型，API-Inference也支持与Anthropic
API兼容的调用方式。要使用Anthropic模式，请在使用前，安装Anthropic SDK:

``` 
pip install anthropic
```

> \[!IMPORTANT\] Anthropic
> API兼容调用方式当前整处于beta测试阶段。如果您在使用过程中遇到任何问题，请联系我们[提供反馈](https://modelscope.cn/docs/联系我们)。

安装Anthropic SDK后，即可调用，以下为使用范例。

#### 流式调用

``` python
import anthropic

client = anthropic.Anthropic(
    api_key="MODELSCOPE_ACCESS_TOKEN", # 请替换成您的ModelScope Access Token
    base_url="https://api-inference.modelscope.cn")

with client.messages.stream(
    model="Qwen/Qwen2.5-7B-Instruct", # ModleScope Model-Id
    messages=[
        {"role": "user", "content": "write a python quicksort"}
    ],
    max_tokens = 1024
) as stream:
  for text in stream.text_stream:
      print(text, end="", flush=True)
```

#### 非流式调用

``` python
import anthropic

client = anthropic.Anthropic(
    api_key="MODELSCOPE_ACCESS_TOKEN", # 请替换成您的ModelScope Access Token
    base_url="https://api-inference.modelscope.cn")

message = client.messages.create(
    model="Qwen/Qwen2.5-7B-Instruct", # ModleScope Model-Id
    messages=[
        {"role": "user", "content": "write a python quicksort"}
    ],
    max_tokens = 1024
)
print(message.content[0].text)
```

在这个范例里，使用魔搭的API-Inference，有几个需要适配的有几个地方：

-   base url: 指向魔搭API-Inference服务
    `https://api-inference.modelscope.cn` 。
-   api_key: 使用魔搭的访问令牌(Access Token),
    可以从您的魔搭账号中获取：<https://modelscope.cn/my/myaccesstoken>
    。
-   模型名字(model):使用魔搭上开源模型的Model
    Id，例如`Qwen/Qwen2.5-Coder-32B-Instruct` 。

更多Anthropic API的接口用法以及参数，可以参考 [Anthropic
API官方文档](https://docs.anthropic.com/en/api)。

### 视觉模型

对于视觉VL模型，同样可以通过OpenAI API调用，例如：

``` python
from openai import OpenAI

client = OpenAI(
    api_key="MODELSCOPE_ACCESS_TOKEN", # 请替换成您的ModelScope Access Token
    base_url="https://api-inference.modelscope.cn/v1"
)

response = client.chat.completions.create(
    model="Qwen/QVQ-72B-Preview", # ModleScope Model-Id
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step."}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/QVQ/demo.png"}
                },
                {   "type": "text", 
                    "text": "What value should be filled in the blank space?"
                },
            ],
        }
    ],
    stream=True
    )


for chunk in response:
    print(chunk.choices[0].delta.content, end='', flush=True)
```

### 文生图模型

支持API调用的模型列表，可以通过[AIGC模型](https://www.modelscope.cn/aigc/models)页面进行搜索。
API的调用示例如下:

``` python
import requests
import time
import json
from PIL import Image
from io import BytesIO

base_url = 'https://api-inference.modelscope.cn/'
api_key = "<MODELSCOPE_SDK_TOKEN>"

common_headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

response = requests.post(
    f"{base_url}v1/images/generations",
    headers={**common_headers, "X-ModelScope-Async-Mode": "true"},
    data=json.dumps({
        "model": "black-forest-labs/FLUX.1-Krea-dev",  # ModelScope Model-Id, required
        "prompt": "A golden cat"
    }, ensure_ascii=False).encode('utf-8')
)

response.raise_for_status()
task_id = response.json()["task_id"]

while True:
    result = requests.get(
        f"{base_url}v1/tasks/{task_id}",
        headers={**common_headers, "X-ModelScope-Task-Type": "image_generation"},
    )
    result.raise_for_status()
    data = result.json()

    if data["task_status"] == "SUCCEED":
        image = Image.open(BytesIO(requests.get(data["output_images"][0]).content))
        image.save("result_image.jpg")
        break
    elif data["task_status"] == "FAILED":
        print("Image Generation Failed.")
        break

    time.sleep(5)
```

| 参数名 | 参数说明 | 是否必须 | 参数类型 | 示例 | 取值范围 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| model | 模型id | 是 | string | MAILAND/majicflus_v1 | ModelScope上的AIGC 模型ID |
| prompt | 正向提示词，大部分模型建议使用英文提示词效果较好。 | 是 | string | A mysterious girl walking down the corridor. | 长度小于2000 |
| negative_prompt | 负向提示词 | 否 | string | lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry | 长度小于2000 |
| size | 生成图像分辨率大小 | 否 | string | 1024x1024 | 分辨率范围:<br>SD系列:[64x64,2048x2048]，FLUX:[64x64,1024x1024]，Qwen-Image:[64x64,1664x1664] |
| seed | 随机种子 | 否 | int | 12345 | [0,2^31-1] |
| steps | 采样步数 | 否 | int | 30 | [1,100] |
| guidance | 提示词引导系数 | 否 | float | 3.5 | [1.5,20] |
| image_url | 待编辑图片的url地址，该参数只适用于支持图片编辑的模型 | 否 | string | https://resources.modelscope.cn/aigc/image_edit.png | 确保公网可访问 |

### 使用限制

-   魔搭推理API-Inference，旨在为开发者提供免费的便捷模型调用方式，**请勿用于需要高并发以及SLA保障的线上任务**，如有商业化使用的需求，建议使用各商业化平台的API。
-   免费推理API由阿里云提供算力支持，**要求您的ModelScope账号必须[绑定阿里云账号](https://modelscope.cn/docs/阿里云账号绑定与授权教程)后才能正常使用**。
-   每位魔搭注册用户，当前每天允许进行**总数为2000次的API-Inference调用**，其中每**单个模型不超过500次**，具体每个模型的限制可能随时动态调整。
-   在上述调用次数限制的基础上，不同模型允许的调用并发，会根据平台的压力进行动态的速率限制调整，原则上以**保障开发者单并发正常使用**为目标。

> \[!IMPORTANT\]
> 出于资源等因素考虑，在每个模型每天不超过500次调用的基础上，平台可能对于部分模型**再进行单独的限制**，这包括单个模型的单天调用总数限制，以及并发限制。
>
> -   例如，[deepseek-ai/DeepSeek-R1-0528](https://www.modelscope.cn/models/deepseek-ai/DeepSeek-R1-0528)，[deepseek-ai/DeepSeek-V3.1](https://modelscope.cn/models/deepseek-ai/DeepSeek-V3.1)等规格较大模型，当前限制**单模型每天200次**调用额度。其他模型的API调用，也可能会有类似的限制并进行**动态调整**。实际单模型可用次数以及允许的并发，**以平台实时调整为准**。
> -   此外随着新模型的推出，比较早的模型可能逐渐从API-Inference下架，在下架过程中会进一步降低使用额度，直至完全下架。

## 支持的模型范围

当前API-Inference为魔搭平台上的部分开源**大语言模型（LLM）**，**多模态模型（MLLM）**，以及[**AIGC专区文生图模型**](https://www.modelscope.cn/aigc/models)等，提供了可直接使用的API。

API-Inference覆盖的模型范围，主要根据模型在魔搭社区中的关注程度（参考了点赞，下载等数据）来判断。因此，在能力更强，关注度更高的下一代开源模型发布之后，支持的模型清单也会持续迭代。开发者可根据模型页面的过滤条件直接筛选，根据标记有"蓝绿色闪电"的
API-Inference logo 来判断。
![img.png](https://resouces.modelscope.cn/document/docdata/2025-9-11_11:43/dist/%E6%A8%A1%E5%9E%8B%E6%9C%8D%E5%8A%A1/%E6%A8%A1%E5%9E%8B%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1/resources/api-inference-logo.png)

同时在模型详情页面右侧，对于支持API-Inference的模型，也会展示使用入口和对应的代码范例。
![img.png](https://resouces.modelscope.cn/document/docdata/2025-9-11_11:43/dist/%E6%A8%A1%E5%9E%8B%E6%9C%8D%E5%8A%A1/%E6%A8%A1%E5%9E%8B%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1/resources/api-inference-sample-code.png)

后续我们会积极推进API-Inference支持的模型的覆盖范围，✌️ 敬请期待️。