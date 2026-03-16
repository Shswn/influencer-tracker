import streamlit as st
import pandas as pd
from supabase import create_client, Client
import re
from datetime import datetime

# ================= 1. 页面配置 (必须放在最前面) =================
st.set_page_config(page_title="达人建联系统 (SaaS 云端版)", layout="wide")

# ================= 2. 数据库初始化 (Secrets 云端安全版) =================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("❌ 未检测到 Secrets 配置，请在 Streamlit 后台设置环境变量。")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# ================= 3. 极简登录校验逻辑 =================
def check_password():
    """如果密码正确则返回 True，否则显示登录界面"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # 绘制登录界面
    st.write("## ")  
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 团队内部管理系统")
        password = st.text_input("请输入访问密码：", type="password")
        if st.button("进入系统"):
            # 💡 极其安全：系统去后台读取你刚才设置的 APP_PASSWORD
            if password == st.secrets["APP_PASSWORD"]: 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚫 密码错误，请联系管理员")
    return False

# ================= 4. 核心功能函数 =================
def extract_emails(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))

# ================= 5. 主程序入口 =================
if check_password():
    # 侧边栏设置
    st.sidebar.title("⚡️ 自动化管理中心")
    st.sidebar.info("当前状态：已登录")
    menu = st.sidebar.radio("请选择操作", ["1. 批量抓取今日新邮箱", "2. 批量更新已回复", "3. 每日数据看板"])
    
    if st.sidebar.button("安全退出"):
        st.session_state["password_correct"] = False
        st.rerun()

    # 模块 1：智能抓取今日新邮箱
    if menu == "1. 批量抓取今日新邮箱":
        st.header("📥 智能提取并录入今日新邮箱")
        today_date = datetime.today().strftime("%Y-%m-%d")
        st.info(f"📅 系统已自动锁定今天日期：**{today_date}**")
        raw_text = st.text_area("把带有邮箱的内容全部粘贴到这里：", height=250)
        
        if st.button("🚀 一键提取并存入云端"):
            if raw_text:
                extracted_emails = extract_emails(raw_text)
                if not extracted_emails:
                    st.warning("⚠️ 没有识别到有效的邮箱地址！")
                else:
                    success_count = 0
                    duplicate_count = 0
                    for email in extracted_emails:
                        email_clean = email.lower()
                        try:
                            supabase.table('influencer_emails').insert(
                                {"email": email_clean, "collect_date": today_date, "status": "未回复"}
                            ).execute()
                            success_count += 1
                        except:
                            duplicate_count += 1
                    st.success(f"✅ 同步成功！新录入 {success_count} 个，过滤重复 {duplicate_count} 个。")
            else:
                st.warning("⚠️ 文本框为空！")

    # 模块 2：批量更新已回复邮箱
    elif menu == "2. 批量更新已回复":
        st.header("🔄 自动匹配并更新【已回复】")
        reply_text = st.text_area("粘贴已回复的邮件信息：", height=250)
        if st.button("✨ 全局更新云端状态"):
            if reply_text:
                replied_emails = extract_emails(reply_text)
                if not replied_emails:
                    st.warning("⚠️ 没有识别到有效的邮箱！")
                else:
                    update_count = 0
                    for email in replied_emails:
                        email_clean = email.lower()
                        response = supabase.table('influencer_emails').update({"status": "已回复"}).eq("email", email_clean).execute()
                        if len(response.data) > 0:
                            update_count += 1
                    st.success(f"🎉 更新完毕！成功匹配并更新了 {update_count} 个邮箱。")

    # 模块 3：每日数据看板
    elif menu == "3. 每日数据看板":
        st.header("📊 每日跟进数据追踪 (云端实时)")
        response = supabase.table('influencer_emails').select("*").execute()
        df_all = pd.DataFrame(response.data)
        
        if not df_all.empty:
            dates_list = df_all['collect_date'].drop_duplicates().sort_values(ascending=False).tolist()
            view_date = st.selectbox("选择要查看的建联批次", dates_list)
            df_view = df_all[df_all['collect_date'] == view_date]
            
            total = len(df_view)
            replied = len(df_view[df_view['status'] == '已回复'])
            unreplied = len(df_view[df_view['status'] == '未回复'])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("当日收集总数", total)
            col2.metric("已回复 (成功破冰)", replied)
            col3.metric("未回复 (需跟进)", unreplied)
            
            st.divider()
            left_col, right_col = st.columns(2)
            with left_col:
                st.subheader(f"📌 需二刷跟进 ({unreplied}个)：")
                unreplied_df = df_view[df_view['status'] == '未回复'].reset_index(drop=True)
                if not unreplied_df.empty:
                    st.dataframe(unreplied_df[['email']], use_container_width=True)
                    emails_to_copy = "\n".join(unreplied_df['email'].tolist())
                    st.text_area("复制发密送(BCC)：", emails_to_copy, height=150)
            with right_col:
                st.subheader(f"🎉 成功破冰名单 ({replied}个)：")
                replied_df = df_view[df_view['status'] == '已回复'].reset_index(drop=True)
                if not replied_df.empty:
                    st.dataframe(replied_df[['email']], use_container_width=True)
        else:
            st.info("云端数据库为空，快去录入吧！")
