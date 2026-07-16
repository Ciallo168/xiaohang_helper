"""
小航 · 郑州航院校园信息查询 AI 助手
运行：双击 启动小航.bat
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import requests

# ───────── 让 streamlit 和依赖可以被导入 ─────────
_ROOT = Path(__file__).resolve().parent
_PKGS = _ROOT / "pkgs"
if _PKGS.exists():
    sys.path.insert(0, str(_PKGS))

import streamlit as st

# ───────── 配置 ─────────
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-gfiyfctmuzepkxtylqvxygpceskmucwdypqunqcvxyxoyouq"
MODEL = "zai-org/GLM-5.2"
TIMEOUT = 60
MAX_RETRIES = 2

# ───────── 数据读取 ─────────
def load_school_info():
    """读取 data/ 下所有 md 文件"""
    files = list(Path("data").glob("*.md"))
    if not files:
        return "【数据文件缺失】"
    parts = []
    for f in sorted(files):
        try:
            parts.append(f"=== {f.name} ===\n{f.read_text(encoding='utf-8')}")
        except Exception:
            parts.append(f"=== {f.name} ===\n【读取失败】")
    return "\n\n".join(parts)

# ───────── 历史记录 ─────────
HISTORY_FILE = Path("data") / "history.json"

def _load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _add_record(role, question, answer):
    history = _load_history()
    history.append({
        "role": role,
        "question": question,
        "answer": answer,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

def _clear_history():
    HISTORY_FILE.write_text("[]", encoding="utf-8")

# ───────── Prompt 工程 ─────────
ROLE_PROMPTS = {
    "新生":   "你像热心的大二学长，语气详细、口语化、多给鼓励。",
    "在校生": "你像办事老司机学长，语气简洁直接。优先给：①地点 ②电话 ③所需材料 ④办结时间。",
    "教师":   "你面向教师，语气专业礼貌。使用\"您\"称呼。",
}

ALIAS_DICT = """
【同义词表】
- "学校""航院""ZUA""郑航" = 郑州航空工业管理学院
- "新校区""龙湖""新校" = 龙子湖校区
- "卡""饭卡""校卡" = 校园一卡通
- "保安""门卫""校警" = 保卫处
"""

HARD_RULES = """
【你必须严格遵守以下规则】
1. 只能根据【学校资料】回答，没有的说"我没收录，建议拨打 0371-61911000 总值班室"
2. 严禁编造电话号码、地址、办公时间、学费金额、人名
3. 涉及金钱/转账必须提示"请先联系辅导员核实，任何要求转账的都是诈骗！"
4. 涉及心理危机(自杀、不想活等)，立即给：12320-5 心理援助 + 学校心理咨询中心 + 告诉辅导员
5. 不接入学校系统，被问"查我的XX"礼貌拒绝
6. 回答末尾标注 [来源:文件名]
"""

def get_system_prompt(role, school_info):
    role_tone = ROLE_PROMPTS.get(role, ROLE_PROMPTS["新生"])
    return f"""你是郑州航院校园信息助手「小航」。
{role_tone}
{ALIAS_DICT}
{HARD_RULES}
【学校资料】
{school_info}"""

# ───────── API 调用 ─────────
def call_api(messages):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=data, timeout=TIMEOUT)
            if resp.status_code == 401:
                return "API Key 失效，请联系老师", {}
            if resp.status_code == 429:
                last_error = "⏳ API 请求过于频繁，正在等待重试..."
                if attempt < MAX_RETRIES:
                    wait = 3 * (attempt + 1)
                    time.sleep(wait)
                    continue
            if resp.status_code != 200:
                return f"API 异常，状态码：{resp.status_code}", {}
            result = resp.json()
            return result["choices"][0]["message"]["content"], result.get("usage", {})
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

# ───────── 推荐问题（按类别标签页） ─────────
TAB_QUESTIONS = {
    "新生指南": [
        "报到那天先去哪？",
        "学费什么时候交？",
        "宿舍是4人间还是6人间？",
        "怎么去学校？",
    ],
    "办事流程": [
        "怎么开在读证明？",
        "校园卡丢了怎么补？",
        "转专业怎么转？",
        "图书馆几点关？",
        "差旅怎么报销？",
        "调课怎么申请？",
    ],
    "应急防骗": [
        "有人冒充辅导员要钱怎么办？",
        "接到诈骗电话怎么办？",
        "保卫处电话是多少？",
        "心理压力大找谁？",
    ],
}

# ───────── Streamlit 界面 ─────────
st.set_page_config(page_title="小航AI助手", page_icon="assets/logo.png", layout="wide")

# 用校徽替换博士帽
col_logo, col_title = st.columns([0.06, 0.94], vertical_alignment="center")
with col_logo:
    st.image("assets/logo.png", width=80)
with col_title:
    st.markdown("## 小航 · 郑州航院校园信息助手")
st.caption("基于 Streamlit + 硅基流动大模型 API | 数据更新日期：2026-07-16")

col_left, col_right = st.columns([1, 3])

with col_left:
    role = st.selectbox("👤 请选择你的身份", ["新生", "在校生", "教师"])
    # -- 推荐问题标签页 --
    st.subheader("💡 试试这些问题：")
    tabs = st.tabs(list(TAB_QUESTIONS.keys()))
    for tab_idx, (tab_name, questions) in enumerate(TAB_QUESTIONS.items()):
        with tabs[tab_idx]:
            for i, q in enumerate(questions):
                if st.button(q, key=f"tab_{tab_idx}_{i}", use_container_width=True):
                    st.session_state["pending_question"] = q
                    st.rerun()

    # -- 历史记录 --
    st.divider()
    st.subheader("📋 历史记录")

    if "history" not in st.session_state:
        st.session_state.history = _load_history()

    if "processing" not in st.session_state:
        st.session_state.processing = False

    if st.button("🗑️ 清空历史记录", use_container_width=True, disabled=st.session_state.processing):
        _clear_history()
        st.session_state.history = []
        st.rerun()

    if st.session_state.history:
        # 导出全部历史
        full_md = "# 小航 · 全部对话历史\n\n"
        for r in reversed(st.session_state.history):
            full_md += f"---\n**时间：**{r['time']} | **身份：**{r['role']}\n\n**问题：**{r['question']}\n\n**回答：**\n{r['answer']}\n\n"
        st.download_button("📥 导出全部历史", data=full_md, file_name="小航历史记录.md", mime="text/markdown", use_container_width=True, disabled=st.session_state.processing)

        for idx, record in enumerate(reversed(st.session_state.history)):
            real_idx = len(st.session_state.history) - 1 - idx
            label = f"{record['time']} [{record['role']}] {record['question'][:20]}..."
            if st.button(label, key=f"hist_{real_idx}", use_container_width=True, disabled=st.session_state.processing):
                st.session_state["view_history"] = record
                st.rerun()
    else:
        st.caption("暂无历史记录")

with col_right:
    if "school_info" not in st.session_state:
        files = list(Path("data").glob("*.md"))
        if not files:
            st.warning("⚠️ 数据文件缺失，请补齐 data/ 目录下的 md 文件")
            st.session_state.school_info = "【数据文件缺失】"
        else:
            st.session_state.school_info = load_school_info()

    # -- 初始化多轮对话 --
    if "conversation" not in st.session_state:
        st.session_state.conversation = []

    current_sys = get_system_prompt(role, st.session_state.school_info)
    if st.session_state.conversation:
        if st.session_state.conversation[0]["content"] != current_sys:
            st.session_state.conversation = []
    else:
        st.session_state.conversation = [{"role": "system", "content": current_sys}]

    # -- 显示对话历史 --
    for msg in st.session_state.conversation:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    # -- 查看历史记录详情 --
    if "view_history" in st.session_state and st.session_state.view_history:
        record = st.session_state.view_history
        col_hist, col_close = st.columns([10, 1])
        with col_hist:
            st.info(f"📋 历史记录 | {record['time']} | 身份：{record['role']}")
        with col_close:
            if st.button("✖", key="close_history"):
                st.session_state.view_history = None
                st.rerun()
        st.markdown(f"**❓ 问题：**{record['question']}")
        st.markdown(f"**🤖 回答：**{record['answer']}")
        st.divider()

    # -- 问题输入区 --
    pending = st.session_state.get("pending_question", None)
    if pending:
        col_pending, col_send = st.columns([5, 1])
        with col_pending:
            st.info(f"💡 {pending}")
        with col_send:
            if st.button("🚀 发送", key="send_pending", use_container_width=True, disabled=st.session_state.processing):
                st.session_state["question"] = pending
                st.session_state.pop("pending_question", None)
                st.session_state.processing = True
                st.rerun()

    question = st.chat_input("💬 有什么想问的？")
    # 用户直接输入时清除 pending
    if question and question.strip():
        st.session_state.pop("pending_question", None)

    if question and question.strip():
        if st.session_state.processing:
            st.warning("⏳ 正在回答上一条问题，请稍候...")
        else:
            st.session_state["question"] = question.strip()
            st.session_state.processing = True
            st.rerun()

    if st.session_state.processing:
        q = st.session_state.get("question", "")
        with st.spinner("小航正在思考中..."):
            st.session_state.conversation.append({"role": "user", "content": q})

            t0 = time.time()
            answer, usage = call_api(st.session_state.conversation)
            elapsed = time.time() - t0

            if not answer.startswith("❌") and not answer.startswith("⏰") and not answer.startswith("🌐") and not answer.startswith("⚠️"):
                st.session_state.conversation.append({"role": "assistant", "content": answer})

            _add_record(role, q, answer)
            st.session_state.history = _load_history()

            st.session_state["last_answer"] = answer
            st.session_state["last_usage"] = usage
            st.session_state["elapsed"] = elapsed
            st.session_state["answer_chars"] = len(answer)

        st.session_state.processing = False
        st.rerun()

    # -- 新对话按钮 + 导出 --
    col_new, col_export = st.columns([1, 1])
    with col_new:
        if st.button("🆕 新对话", use_container_width=True, disabled=st.session_state.processing):
            st.session_state.conversation = []
            st.session_state.pop("last_answer", None)
            st.rerun()
    with col_export:
        if "last_answer" in st.session_state and st.session_state.last_answer:
            q = st.session_state.get("question", "")
            a = st.session_state.last_answer
            export_md = f"# 小航对话记录\n\n**问题：**{q}\n\n**回答：**\n{a}\n"
            st.download_button("📥 导出最后回答", data=export_md, file_name="小航对话.md", mime="text/markdown", use_container_width=True)

    # -- 显示 Token / 字数 / 耗时 --
    if "last_usage" in st.session_state and st.session_state.last_usage:
        usage = st.session_state.last_usage
        chars = st.session_state.get("answer_chars", 0)
        elapsed = st.session_state.get("elapsed", 0)
        st.caption(
            f"回答字数：{chars} 字 · 耗时：{elapsed:.1f} 秒 · "
            f"Token：输入 {usage.get('prompt_tokens', '?')} + 输出 {usage.get('completion_tokens', '?')}"
        )

    st.divider()
    with st.expander("📞 电话黄页（静态兜底）"):
        st.markdown("""
| 部门 | 电话 |
|------|------|
| 校园 110（保卫处 24h） | 0371-61916110 |
| 学校总值班室 | 0371-61911000 |
| 校医院急诊（24h） | 0371-61912120 |
| 心理咨询中心 | 0371-61912580 |
| 后勤管理处 | 0371-61912800 |
| 卡务中心 | 0371-61912810 |
| 招生办公室 | 0371-61912530 |
| 全国心理援助热线 | 12320-5 |
""")

st.divider()
st.caption("郑州航空工业管理学院人工智能专业认知实习项目 · 电话以官方为准")