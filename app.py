import streamlit as st
import pandas as pd
from supabase import create_client, Client
import re
from datetime import datetime

# ================= 1. 数据库初始化 (Supabase 云端版) =================
# 已经替换为你的专属真实 URL 和 Key
SUPABASE_URL = "https://guqverqjfiqokketodup.supabase.co"
SUPABASE_KEY = "sb_publishable_iRoesdrYPkhT5KkdgAwITA_FIRVOeM8"

# 使用 Streamlit 缓存机制，避免每次刷新页面都重新连接数据库
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# ================= 2. 核心提取函数 =================
def extract_emails(text):
    """利用正则表达式，精准提取邮箱"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))

# ================= 3. 页面与侧边栏设置 =================
st.set_page_config(page_title="达人建联系统 (SaaS 云端版)", layout="wide")
st.sidebar.title("⚡️ 自动化管理中心")
menu = st.sidebar.radio("请选择操作", ["1. 批量抓取今日新邮箱", "2. 批量更新已回复", "3. 每日数据看板"])

# ================= 4. 功能模块实现 =================

# 模块 1：智能抓取今日新邮箱
if menu == "1. 批量抓取今日新邮箱":
    st.header("📥 智能提取并录入今日新邮箱")
    
    today_date = datetime.today().strftime("%Y-%m-%d")
    st.info(f"📅 系统已自动锁定今天日期：**{today_date}**")
    
    raw_text = st.text_area("把带有邮箱的内容全部粘贴到这里（随便粘）：", height=250)
    
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
                        # Supabase 插入数据语法
                        data, count = supabase.table('influencer_emails').insert(
                            {"email": email_clean, "collect_date": today_date, "status": "未回复"}
                        ).execute()
                        success_count += 1
                    except Exception as e:
                        # 如果出现异常，通常是因为 email 违反了主键唯一性（即邮箱已存在）
                        duplicate_count += 1
                
                st.success(f"✅ 云端同步成功！识别到 {len(extracted_emails)} 个。新录入 {success_count} 个 (过滤掉 {duplicate_count} 个重复)。")
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
                    # Supabase 更新数据语法
                    response = supabase.table('influencer_emails').update({"status": "已回复"}).eq("email", email_clean).execute()
                    
                    # 检查是否真的更新到了数据
                    if len(response.data) > 0:
                        update_count += 1
                        
                st.success(f"🎉 云端状态更新完毕！成功匹配并更新了 {update_count} 个邮箱。")
        else:
            st.warning("⚠️ 请先粘贴内容！")

# 模块 3：按天查看数据看板 (保留了左右分栏优化的UI)
elif menu == "3. 每日数据看板":
    st.header("📊 每日跟进数据追踪 (云端实时)")
    
    # 从云端拉取所有数据
    response = supabase.table('influencer_emails').select("*").execute()
    df_all = pd.DataFrame(response.data)
    
    if not df_all.empty:
        # 获取所有不重复的日期，并降序排列
        dates_list = df_all['collect_date'].drop_duplicates().sort_values(ascending=False).tolist()
        view_date = st.selectbox("选择要查看的建联批次", dates_list)
        
        # 过滤出当前选中日期的数据
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
                st.text_area("复制此框内的邮箱，去发密送(BCC)：", emails_to_copy, height=150)
            else:
                st.success("全部回复完毕！")
                
        with right_col:
            st.subheader(f"🎉 成功破冰名单 ({replied}个)：")
            replied_df = df_view[df_view['status'] == '已回复'].reset_index(drop=True)
            if not replied_df.empty:
                st.dataframe(replied_df[['email']], use_container_width=True)
            else:
                st.info("暂无回复，继续加油！")
            
    else:
        st.info("云端数据库为空，快去录入第一批达人邮箱吧！")