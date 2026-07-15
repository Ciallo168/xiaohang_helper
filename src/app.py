# ==================== 小航AI助手 - Streamlit 主程序 ====================
"""
小航 · 郑州航院校园信息查询 AI 助手

运行方式：
    双击 启动小航.bat
    或
    set PYTHONPATH=pkgs && streamlit run src/app.py
"""

import sys
from pathlib import Path

# 项目根目录（streamlit 会切换 cwd，用绝对路径最可靠）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 将本地 pkgs 目录加入 Python 搜索路径
_LOCAL_PKGS = _PROJECT_ROOT / "pkgs"
if _LOCAL_PKGS.exists():
    sys.path.insert(0, str(_LOCAL_PKGS))

import streamlit as st
from src.prompts import load_school_info, get_system_prompt
from src.api import call_ai_api

# ==================== 12 个推荐问题（按身份分类） ====================
PRESET_QUESTIONS = {
    "新生": [
        "报到那天先去哪？",
        "学费什么时候交？",
        "宿舍是4人间还是6人间？",
        "有人冒充辅导员要钱怎么办？",
    ],
    "在校生": [
        "怎么开在读证明？",
        "校园卡丢了怎么补？",
        "转专业怎么转？",
        "图书馆几点关？",
    ],
    "教师": [
        "差旅怎么报销？",
        "调课怎么申请？",
        "教室设备坏了找谁？",
        "科研项目去哪申报？",
    ],
}


# ==================== 页面配置 ====================
st.set_page_config(page_title="小航AI助手", page_icon="🎓", layout="wide")

# ==================== 标题和边界声明 ====================
st.title("🎓 小航 · 郑州航院校园信息助手")
st.caption("基于 Streamlit + 硅基流动大模型 API | 数据更新日期：2026-07-15")

# ==================== 左右分栏布局 ====================
col_left, col_right = st.columns([1, 3])

# ==================== 左侧：身份选择 + 推荐问题 ====================
with col_left:
    # -- 身份选择 --
    role = st.selectbox("👤 请选择你的身份", ["新生", "在校生", "教师"])

    # -- 推荐问题按钮（12个，按当前身份显示4个）--
    st.subheader("💡 试试这些问题：")
    questions = PRESET_QUESTIONS.get(role, [])
    for i, q in enumerate(questions):
        if st.button(q, key=f"btn_{i}", use_container_width=True):
            st.session_state["question"] = q
            st.rerun()

# ==================== 右侧：问题输入 + 回答显示 ====================
with col_right:
    # -- 问题输入框 --
    question = st.text_input(
        "💬 有什么想问的？",
        value=st.session_state.get("question", ""),
        placeholder="例如：保卫处电话是多少？",
    )

    # -- 加载学校资料（只加载一次，存 session_state）--
    if "school_info" not in st.session_state:
        # 检查数据文件是否存在
        files = list(Path("data").glob("*.md"))
        if not files:
            st.warning("⚠️ 数据文件缺失，请补齐 data/ 目录下的 md 文件")
            st.session_state.school_info = "【数据文件缺失】请检查 data/ 目录下是否有 md 文件"
        else:
            with st.spinner("正在加载校园资料..."):
                st.session_state.school_info = load_school_info()

    # -- 提问按钮 --
    if st.button("🚀 提问", type="primary"):
        if question and question.strip():
            with st.spinner("小航正在思考中..."):

                # 生成 system prompt
                system_prompt = get_system_prompt(role, st.session_state.school_info)

                # 调用 API
                answer, usage = call_ai_api(system_prompt, question.strip())

                # 显示回答
                st.subheader("🤖 小航的回答")
                st.markdown(answer)

                # 显示 Token 消耗
                if usage:
                    st.caption(
                        f"📊 Token 消耗："
                        f"输入 {usage.get('prompt_tokens', 'N/A')} + "
                        f"输出 {usage.get('completion_tokens', 'N/A')} = "
                        f"总计 {usage.get('total_tokens', 'N/A')}"
                    )
        else:
            st.info("💡 请输入你的问题，或点击左侧推荐问题")

    # -- 电话黄页静态页（API 不可用时的兜底）--
    st.divider()
    with st.expander("📞 电话黄页（静态兜底 - AI 不可用时也能看）"):
        st.caption("AI 答不上来时，可以直接查这里 ↓")

        st.markdown("""
| 部门 | 电话 | 备注 |
|------|------|------|
| 校园 110（保卫处 24h） | 0371-61916110 | 紧急情况第一时间拨打 |
| 学校总值班室 | 0371-61911000 | 非工作时间联系 |
| 校医院急诊（24h） | 0371-61912120 | 龙子湖校区 |
| 心理咨询中心 | 0371-61912580 | 工作时间 |
| 后勤管理处 | 0371-61912800 | 后勤楼 |
| 后勤服务热线/物业报修 | 0371-61913110 | 水电维修 |
| 卡务中心 | 0371-61912810 | 一卡通挂失补办 |
| 招生办公室 | 0371-61912530 | 综合楼 |
| 全国心理援助热线 | 12320-5 | 24小时免费 |
""")

# ==================== 页脚 ====================
st.divider()
st.caption(
    "郑州航空工业管理学院人工智能专业认知实习项目 · "
    "API：硅基流动 https://api.siliconflow.cn · "
    "电话如有变动请以官方为准 ⚠"
)
