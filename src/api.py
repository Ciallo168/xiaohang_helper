# ==================== 小航AI助手 - API调用模块 ====================
import requests
from src.config import API_URL, API_KEY, MODEL, TIMEOUT


def call_ai_api(system_prompt, user_question):
    """
    调用硅基流动 API，返回 (回答文本, token使用量字典)
    
    异常处理覆盖：
    - 请求超时（Timeout）
    - 网络连接失败（ConnectionError）
    - API Key 失效（401）
    - API 返回格式异常（KeyError/IndexError）
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=TIMEOUT)

        # 检查 HTTP 状态码
        if response.status_code == 401:
            return "❌ API Key 失效，请联系老师重新获取", {}
        elif response.status_code != 200:
            return f"❌ API 异常，状态码：{response.status_code}", {}

        result = response.json()

        # 解析 AI 回答
        answer = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        return answer, usage

    except requests.exceptions.Timeout:
        return "⏰ AI 响应超时，请稍后再试", {}
    except requests.exceptions.ConnectionError:
        return "🌐 网络连接失败，请检查网络", {}
    except (KeyError, IndexError):
        return "❌ AI 返回格式异常，请重试", {}
    except Exception as e:
        return f"⚠️ 发生错误：{e}", {}
