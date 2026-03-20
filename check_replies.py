import os
import imaplib
import email
from email.utils import parseaddr
from supabase import create_client, Client

# 1. 环境配置 (Namecheap 官方 IMAP 服务器)
IMAP_SERVER = "mail.privateemail.com" 
EMAIL_ACCOUNT = os.environ.get("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def check_and_update_replies():
    print("🕵️ 开始执行邮件巡逻任务...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # 2. 登录专属邮箱
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select('inbox')
        
        # 3. 搜索所有【未读】邮件
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        if not email_ids:
            print("📭 过去 12 小时内没有新的未读回复。")
            return

        print(f"📬 发现 {len(email_ids)} 封未读邮件，开始匹配数据库...")
        
        update_count = 0
        for e_id in email_ids:
            # 💡 核心细节：使用 PEEK 只读头部，不改变“未读”状态，保护你的阅读体验
            res, msg_data = mail.fetch(e_id, '(BODY.PEEK[HEADER])')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # 提取发件人邮箱
                    from_header = msg.get('From')
                    name, sender_email = parseaddr(from_header)
                    sender_email = sender_email.lower()
                    
                    if sender_email:
                        print(f"👀 收到来自 {sender_email} 的邮件，正在更新云端状态...")
                        # 4. 去 Supabase 把这名达人的状态改为“已回复”
                        supabase.table('influencer_emails').update(
                            {"status": "已回复"}
                        ).eq("email", sender_email).execute()
                        update_count += 1
                        
        print(f"✅ 巡逻结束！共处理并更新了 {update_count} 个达人状态。")
        mail.logout()
        
    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    check_and_update_replies()
