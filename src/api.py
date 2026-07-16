# ==================== 小航AI助手 - API调用模块 ====================
import time
import requests
from src.config import API_URL, API_KEY, MODEL, TIMEOUT, MAX_RETRIES


def check_network():
    """快速检测网络连通性，返回 (是否在线, 提示文本)"""
    try:
        requests.head("https://api.siliconflow.cn", timeout=3)
        return True, ""
    except Exception:
        return False, "🌐 网络连接异常，请检查网络后重试"


def call_ai_api_messages(messages):
    """
    调用硅基流动 API，messages 为完整对话列表
    格式：[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
    超时/429限流 自动重试，最多 MAX_RETRIES 次
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(API_URL, headers=headers, json=data, timeout=TIMEOUT)

            if response.status_code == 401:
                return "❌ API Key 失效，请联系老师重新获取", {}
            elif response.status_code == 429:
                last_error = "⏳ API 请求过于频繁，正在等待重试..."
                if attempt < MAX_RETRIES:
                    wait = 3 * (attempt + 1)
                    time.sleep(wait)
                    continue
            elif response.status_code != 200:
                return f"❌ API 异常，状态码：{response.status_code}", {}

            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            return answer, usage

        except requests.exceptions.Timeout:
            last_error = "⏰ AI 响应超时，请稍后再试"
            if attempt < MAX_RETRIES:
                time.sleep(2)
        except requests.exceptions.ConnectionError:
            return "🌐 网络连接失败，请检查网络", {}
        except (KeyError, IndexError):
            return "❌ AI 返回格式异常，请重试", {}
        except Exception as e:
            return f"⚠️ 发生错误：{e}", {}

    return last_error, {}


# 兼容旧接口
call_ai_api = call_ai_api_messages
