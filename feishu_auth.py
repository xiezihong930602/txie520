# -*- coding: utf-8 -*-
"""
飞书OAuth授权脚本
第一次运行，浏览器扫码授权，自动保存token到本地
"""
import webbrowser
import http.server
import urllib.parse
import requests
import json
import os
import sys

APP_ID = "cli_aad2542de4b81cfd"
APP_SECRET = "vMwvpzPe8kgvFN6H274DYg7MNH310NXy"
REDIRECT_URI = "http://localhost:8080/callback"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feishu_token.json")

auth_code = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            auth_code = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Auth success! You can close this page now.</h2>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    print("=" * 50)
    print("  飞书OAuth授权")
    print("=" * 50)
    print()

    # 构造授权URL
    auth_url = (
        f"https://open.feishu.cn/open-apis/authen/v1/index"
        f"?app_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state=random_state"
    )

    print("即将打开浏览器，请用飞书扫码登录授权...")
    print("如果浏览器没有自动打开，请手动访问：")
    print(auth_url)
    print()

    # 启动本地HTTP服务器
    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)

    # 打开浏览器
    webbrowser.open(auth_url)

    # 等待回调
    print("等待授权中...")
    while auth_code is None:
        server.handle_request()

    server.server_close()

    if not auth_code:
        print("授权失败，没有拿到code")
        sys.exit(1)

    print("拿到授权码，正在换取token...")

    # 用code换user_access_token
    url = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
    headers = {"Content-Type": "application/json"}

    # 先拿tenant_access_token
    tenant_resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}
    )
    tenant_token = tenant_resp.json().get("tenant_access_token")
    headers["Authorization"] = f"Bearer {tenant_token}"

    # 换user token
    resp = requests.post(url, headers=headers, json={
        "grant_type": "authorization_code",
        "code": auth_code
    })
    data = resp.json()

    if data.get("code") != 0:
        print(f"换取token失败: {data.get('msg')}")
        sys.exit(1)

    token_data = data.get("data", {})

    # 保存到文件
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    print()
    print(f"授权成功！token已保存到: {TOKEN_FILE}")
    print(f"access_token 有效期: {token_data.get('expires_in', 7200)}秒")
    print(f"refresh_token 有效期: {token_data.get('refresh_expires_in', 2592000)}秒")
    print()
    print("后续运行会自动刷新token，不用再授权了。")


if __name__ == "__main__":
    main()
