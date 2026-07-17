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
import time

# 项目根目录（streamlit 会切换 cwd，用绝对路径最可靠）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 将本地 pkgs 目录加入 Python 搜索路径
_LOCAL_PKGS = _PROJECT_ROOT / "pkgs"
if _LOCAL_PKGS.exists():
    sys.path.insert(0, str(_LOCAL_PKGS))

import streamlit as st
from src.prompts import load_school_info, get_system_prompt
from src.api import call_ai_api_messages, check_network
from src.history import load_history, add_record, clear_history

# ==================== 推荐问题（按类别标签页） ====================
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


# ==================== 页面配置 ====================
st.set_page_config(page_title="小航AI助手", page_icon="assets/logo.png", layout="wide")

# ==================== 标题和边界声明 ====================
col_logo, col_title = st.columns([0.06, 0.94], vertical_alignment="center")
with col_logo:
    st.image("assets/logo.png", width=80)
with col_title:
    st.markdown("## 小航 · 郑州航院校园信息助手")
st.caption("基于 Streamlit + 硅基流动大模型 API | 数据更新日期：2026-07-16")

# -- 网络检测 --
if "online" not in st.session_state:
    st.session_state.online, _ = check_network()
if not st.session_state.online:
    col_warn, col_retry = st.columns([5, 1])
    with col_warn:
        st.warning("🌐 网络连接异常，部分功能不可用")
    with col_retry:
        if st.button("🔄 重试", key="retry_network", use_container_width=True):
            st.session_state.online, _ = check_network()
            st.rerun()

# ==================== 左右分栏布局 ====================
col_left, col_right = st.columns([1, 3])

# ==================== 左侧：身份选择 + 推荐问题 ====================
with col_left:
    # -- 身份选择 --
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

    # 初始化历史记录到 session_state（仅首次加载）
    if "history" not in st.session_state:
        st.session_state.history = load_history()

    if "processing" not in st.session_state:
        st.session_state.processing = False

    if st.button("🗑️ 清空历史记录", use_container_width=True, disabled=st.session_state.processing):
        clear_history()
        st.session_state.history = []
        st.rerun()

    if st.session_state.history:
        # 导出全部历史
        full_md = "# 小航 · 全部对话历史\n\n"
        for r in reversed(st.session_state.history):
            full_md += f"---\n**时间：**{r['time']} | **身份：**{r['role']}\n\n**问题：**{r['question']}\n\n**回答：**\n{r['answer']}\n\n"
        st.download_button("📥 导出全部历史", data=full_md, file_name="小航历史记录.md", mime="text/markdown", use_container_width=True, disabled=st.session_state.processing)

        # 倒序显示，最新的在最上面
        for idx, record in enumerate(reversed(st.session_state.history)):
            real_idx = len(st.session_state.history) - 1 - idx
            label = f"{record['time']} [{record['role']}] {record['question'][:20]}..."
            if st.button(label, key=f"hist_{real_idx}", use_container_width=True, disabled=st.session_state.processing):
                st.session_state["view_history"] = record
                st.rerun()
    else:
        st.caption("暂无历史记录")

# ==================== 右侧：多轮对话 ====================
with col_right:
    # -- 加载学校资料 --
    if "school_info" not in st.session_state:
        files = list(Path("data").glob("*.md"))
        if not files:
            st.warning("⚠️ 数据文件缺失，请补齐 data/ 目录下的 md 文件")
            st.session_state.school_info = "【数据文件缺失】"
        else:
            with st.spinner("正在加载校园资料..."):
                st.session_state.school_info = load_school_info()

    # -- 初始化多轮对话 --
    if "conversation" not in st.session_state:
        st.session_state.conversation = []

    # 身份或资料变化时重建 system prompt（重置对话）
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

    question = st.chat_input("💬 有什么想问的？" if st.session_state.online else "🌐 网络异常，暂时无法提问")
    if question:
        if question.strip():
            st.session_state.pop("pending_question", None)
            if st.session_state.processing:
                st.warning("⏳ 正在回答上一条问题，请稍候...")
            else:
                st.session_state["question"] = question.strip()
                st.session_state.processing = True
                st.rerun()
        else:
            st.warning("💡 请输入你的问题，或点击左侧推荐问题")

    if st.session_state.processing:
        q = st.session_state.get("question", "")
        with st.spinner("小航正在思考中..."):
            # 追加用户消息
            st.session_state.conversation.append({"role": "user", "content": q})

            # 调用 API
            t0 = time.time()
            answer, usage = call_ai_api_messages(st.session_state.conversation)
            elapsed = time.time() - t0

            # 追加助手回复
            if not answer.startswith("❌") and not answer.startswith("⏰") and not answer.startswith("🌐") and not answer.startswith("⚠️"):
                st.session_state.conversation.append({"role": "assistant", "content": answer})

            # 保存到历史记录
            add_record(role, q, answer)
            st.session_state.history = load_history()

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

    # -- 电话黄页静态页（已隐藏，保留在代码中备用）--
    # st.divider()
    # with st.expander("📞 电话黄页（静态兜底 - AI 不可用时也能看）"):
    #     st.caption("AI 答不上来时，可以直接查这里 ↓")
    #     st.markdown("""
    # | 部门 | 电话 | 备注 |
    # |------|------|------|
    # | 校园 110（保卫处 24h） | 0371-61916110 | 紧急情况第一时间拨打 |
    # | 学校总值班室 | 0371-61911000 | 非工作时间联系 |
    # | 校医院急诊（24h） | 0371-61912120 | 龙子湖校区 |
    # | 心理咨询中心 | 0371-61912580 | 工作时间 |
    # | 后勤管理处 | 0371-61912800 | 后勤楼 |
    # | 后勤服务热线/物业报修 | 0371-61913110 | 水电维修 |
    # | 卡务中心 | 0371-61912810 | 一卡通挂失补办 |
    # | 招生办公室 | 0371-61912530 | 综合楼 |
    # | 全国心理援助热线 | 12320-5 | 24小时免费在线 |
    # """)

# ==================== 页脚 ====================
st.divider()
st.caption(
    "郑州航空工业管理学院人工智能专业认知实习项目 · "
    "API：硅基流动 https://api.siliconflow.cn · "
    "电话如有变动请以官方为准 ⚠"
)
