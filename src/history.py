# ==================== 小航AI助手 - 历史记录模块 ====================
import json
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path("data") / "history.json"


def load_history():
    """从 JSON 文件加载历史记录，返回列表"""
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(history_list):
    """将历史记录列表写入 JSON 文件"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_record(role, question, answer):
    """添加一条 Q&A 记录到历史"""
    history = load_history()
    history.append({
        "role": role,
        "question": question,
        "answer": answer,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_history(history)


def clear_history():
    """清空所有历史记录"""
    HISTORY_FILE.write_text("[]", encoding="utf-8")
