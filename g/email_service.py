"""邮箱服务类 - 适配 freemail API"""
import os
import time
import requests
from dotenv import load_dotenv


class EmailService:
    def __init__(self, proxies=None):
        load_dotenv()
        self.worker_domain = os.getenv("WORKER_DOMAIN")
        self.freemail_token = os.getenv("FREEMAIL_TOKEN")
        if not all([self.worker_domain, self.freemail_token]):
            raise ValueError("Missing: WORKER_DOMAIN or FREEMAIL_TOKEN")
        self.base_url = f"https://{self.worker_domain}"
        self.headers = {"Authorization": f"Bearer {self.freemail_token}"}
        self.proxies = proxies or {}

    def create_email(self):
        """创建临时邮箱 GET /api/generate"""
        try:
            res = requests.get(
                f"{self.base_url}/api/generate",
                headers=self.headers,
                proxies=self.proxies,
                timeout=10
            )
            if res.status_code == 200:
                email = res.json().get("email")
                return email, email  # 兼容原接口 (jwt, email)
            print(f"[-] 创建邮箱失败: {res.status_code} - {res.text}")
            return None, None
        except Exception as e:
            print(f"[-] 创建邮箱失败: {e}")
            return None, None

    def fetch_verification_code(self, email, max_attempts=30, debug=False):
        """轮询获取验证码 GET /api/emails?mailbox=xxx"""
        if debug:
            print(f"[DEBUG] 开始轮询获取验证码，邮箱: {email}")
        for i in range(max_attempts):
            try:
                if debug:
                    print(f"[DEBUG] 第 {i+1}/{max_attempts} 次轮询...")
                res = requests.get(
                    f"{self.base_url}/api/emails",
                    params={"mailbox": email},
                    headers=self.headers,
                    proxies=self.proxies,
                    timeout=10
                )
                if debug:
                    print(f"[DEBUG] 响应状态: {res.status_code}")
                if res.status_code == 200:
                    emails = res.json()
                    if debug:
                        print(f"[DEBUG] 响应数据: {emails}")
                    if emails and len(emails) > 0:
                        # 检查邮件字段
                        first_email = emails[0]
                        if debug:
                            print(f"[DEBUG] 第一封邮件字段: {first_email.keys()}")
                        # 可能的验证码字段名
                        code = first_email.get("verification_code") or first_email.get("code") or first_email.get("verify_code")
                        if code:
                            if debug:
                                print(f"[DEBUG] 获取到验证码: {code}")
                            return code.replace("-", "")
                        else:
                            # 从 subject 提取验证码（格式: "XXX-XXX xAI confirmation code"）
                            subject = first_email.get("subject", "")
                            if debug:
                                print(f"[DEBUG] Subject: {subject}")
                            # 提取前 7 位（含横杠）或匹配 XXX-XXX 模式
                            import re
                            match = re.search(r'^([A-Z0-9]{3}-[A-Z0-9]{3})', subject)
                            if match:
                                code = match.group(1)
                                if debug:
                                    print(f"[DEBUG] 从 Subject 提取验证码: {code}")
                                return code.replace("-", "")
            except Exception as e:
                if debug:
                    print(f"[DEBUG] 轮询异常: {e}")
            time.sleep(1)
        if debug:
            print(f"[DEBUG] 轮询结束，未获取到验证码")
        return None

    def delete_email(self, address):
        """删除邮箱 DELETE /api/mailboxes?address=xxx"""
        try:
            res = requests.delete(
                f"{self.base_url}/api/mailboxes",
                params={"address": address},
                headers=self.headers,
                proxies=self.proxies,
                timeout=10
            )
            return res.status_code == 200 and res.json().get("success")
        except:
            return False
