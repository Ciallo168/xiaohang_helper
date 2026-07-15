"""
小航 · 郑州航院校园信息查询 AI 助手
运行：双击 启动小航.bat
"""
import sys
from pathlib import Path
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
TIMEOUT = 30

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
def call_api(system_prompt, user_question):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
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
        resp = requests.post(API_URL, headers=headers, json=data, timeout=TIMEOUT)
        if resp.status_code == 401:
            return "API Key 失效，请联系老师", {}
        if resp.status_code != 200:
            return f"API 异常，状态码：{resp.status_code}", {}
        result = resp.json()
        return result["choices"][0]["message"]["content"], result.get("usage", {})
    except requests.exceptions.Timeout:
        return "⏰ AI 响应超时，请稍后再试", {}
    except requests.exceptions.ConnectionError:
        return "🌐 网络连接失败，请检查网络", {}
    except (KeyError, IndexError):
        return "❌ AI 返回格式异常，请重试", {}
    except Exception as e:
        return f"⚠️ 发生错误：{e}", {}

# ───────── 推荐问题 ─────────
PRESET = {
    "新生":   ["报到那天先去哪？","学费什么时候交？","宿舍是4人间还是6人间？","有人冒充辅导员要钱怎么办？"],
    "在校生": ["怎么开在读证明？","校园卡丢了怎么补？","转专业怎么转？","图书馆几点关？"],
    "教师":   ["差旅怎么报销？","调课怎么申请？","教室设备坏了找谁？","科研项目去哪申报？"],
}

# ───────── Streamlit 界面 ─────────
st.set_page_config(page_title="小航AI助手", page_icon="🎓", layout="wide")
st.title("🎓 小航 · 郑州航院校园信息助手")
st.caption("基于 Streamlit + 硅基流动大模型 API | 数据更新日期：2026-07-15")

col_left, col_right = st.columns([1, 3])

with col_left:
    role = st.selectbox("👤 请选择你的身份", ["新生", "在校生", "教师"])
    st.subheader("💡 试试这些问题：")
    for i, q in enumerate(PRESET.get(role, [])):
        if st.button(q, key=f"btn_{i}", use_container_width=True):
            st.session_state["question"] = q
            st.rerun()

with col_right:
    question = st.text_input(
        "💬 有什么想问的？",
        value=st.session_state.get("question", ""),
        placeholder="例如：保卫处电话是多少？",
    )

    if "school_info" not in st.session_state:
        files = list(Path("data").glob("*.md"))
        if not files:
            st.warning("⚠️ 数据文件缺失，请补齐 data/ 目录下的 md 文件")
            st.session_state.school_info = "【数据文件缺失】请检查 data/ 目录下是否有 md 文件"
        else:
            st.session_state.school_info = load_school_info()

    if st.button("🚀 提问", type="primary"):
        if question and question.strip():
            with st.spinner("小航正在思考中..."):
                prompt = get_system_prompt(role, st.session_state.school_info)
                answer, usage = call_api(prompt, question.strip())
                st.subheader("🤖 小航的回答")
                st.markdown(answer)
                if usage:
                    st.caption(f"Token：输入{usage.get('prompt_tokens','?')} + 输出{usage.get('completion_tokens','?')} = 总计{usage.get('total_tokens','?')}")
        else:
            st.info("💡 请输入你的问题，或点击左侧推荐问题")

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