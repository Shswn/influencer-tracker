import streamlit as st
import pandas as pd
from supabase import create_client, Client
import re
from datetime import datetime

# ================= 1. 页面配置 =================
st.set_page_config(page_title="达人建联系统 (SaaS 云端版)", layout="wide")

# ================= 2. 数据库初始化 =================
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

# ================= 3. 登录校验逻辑 =================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.write("## ")  
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 团队内部管理系统")
        password = st.text_input("请输入访问密码：", type="password")
        if st.button("进入系统"):
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
    # 💡 这里多加了一个菜单选项！
    menu = st.sidebar.radio("请选择操作", [
        "1. 批量抓取今日新邮箱", 
        "2. 批量更新已回复", 
        "3. 每日数据看板", 
        "4. 邮件模板配置中心"
    ])
    
    if st.sidebar.button("安全退出"):
        st.session_state["password_correct"] = False
        st.rerun()

    # --- 模块 1：抓取 ---
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
                    success_count, duplicate_count = 0, 0
                    for email in extracted_emails:
                        email_clean = email.lower()
                        try:
                            # 💡 插入时自动将 last_contact_date 留空，followup_count 设为 0
                            supabase.table('influencer_emails').insert(
                                {"email": email_clean, "collect_date": today_date, "status": "未回复", "followup_count": 0}
                            ).execute()
                            success_count += 1
                        except:
                            duplicate_count += 1
                    st.success(f"✅ 同步成功！新录入 {success_count} 个，过滤重复 {duplicate_count} 个。")
            else:
                st.warning("⚠️ 文本框为空！")

    # --- 模块 2：更新 ---
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

    # --- 模块 3：看板 ---
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
            with right_col:
                st.subheader(f"🎉 成功破冰名单 ({replied}个)：")
                replied_df = df_view[df_view['status'] == '已回复'].reset_index(drop=True)
                if not replied_df.empty:
                    st.dataframe(replied_df[['email']], use_container_width=True)
        else:
            st.info("云端数据库为空，快去录入吧！")

    # --- 模块 4：全新增加的邮件模板配置中心 ---
    elif menu == "4. 邮件模板配置中心":
        st.header("📝 自动化发信模板配置")
        st.info("💡 在这里修改的模板，将作为后续全自动二刷发信的标准内容。")

        # 从云端拉取当前已有的模板
        response = supabase.table('email_templates').select("*").eq("id", 1).execute()
        existing_data = response.data

        # 如果云端有数据就显示云端的，如果没有就显示默认的占位符
        default_subject = existing_data[0]['subject'] if existing_data else "Follow up regarding our collaboration"
        default_body = existing_data[0]['body'] if existing_data else "Hi there,\n\nJust following up on my previous email to see if you'd be interested in collaborating with us!\n\nBest,\nShawn"

        new_subject = st.text_input("✉️ 邮件标题 (Subject)：", value=default_subject)
        new_body = st.text_area("📄 邮件正文 (Body)：", value=default_body, height=300)

        if st.button("💾 保存模板到云端"):
            try:
                # 使用 upsert：如果 id=1 存在就更新，不存在就新建
                supabase.table('email_templates').upsert(
                    {"id": 1, "subject": new_subject, "body": new_body}
                ).execute()
                st.success("✅ 模板已成功保存！明天的自动化任务将使用此最新内容。")
            except Exception as e:
                st.error(f"保存失败，请检查数据库配置: {e}")
