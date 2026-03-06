import openai
import tiktoken
import time
import os
from typing import Dict, List, Optional
from tenacity import retry, wait_random_exponential, stop_after_attempt


class LLMHandler_inf:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        openai.base_url = os.getenv("OPENAI_BASE_URL", 'http://openai.infly.tech/v1/')
        openai.api_key = 'no-modify'  # 不是改这个值，改下面的
        self.api_key = api_key
        self.extra = {}

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def get_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> str:

        try:
            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "extra_body": self.extra,
                "extra_headers": {'apikey': self.api_key},
                "stream": False,
            }
            
            # 添加可选参数
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            if response_format is not None:
                request_params["response_format"] = response_format
            
            # 添加其他额外参数
            request_params.update(kwargs)
            
            response = openai.chat.completions.create(**request_params)
            return response.choices[0].message.content
        except Exception as e:
            print(f"调用API时发生错误: {str(e)}")
            raise e

if __name__ == '__main__':
    handler = LLMHandler_inf(os.getenv("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI, based on the GPT-4 architecture."},
        {"role": "user", "content": "帮我重写下面的gpt system prompt"}
    ]
    print(handler.get_completion(messages))
