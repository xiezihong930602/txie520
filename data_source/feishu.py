# -*- coding: utf-8 -*-
"""
飞书多维表格数据读写模块（用户身份OAuth版）
自动刷新token，代表用户操作，权限和用户一致
"""
import requests
import json
import time
import os
from typing import List, Optional, Dict, Any


APP_ID = "cli_aad2542de4b81cfd"
APP_SECRET = "vMwvpzPe8kgvFN6H274DYg7MNH310NXy"
BASE_URL = "https://open.feishu.cn/open-apis"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "feishu_token.json")


class FeishuDataSource:
    """飞书多维表格数据源（用户身份）"""

    def __init__(self, base_token: str, table_id: str):
        self.base_token = base_token
        self.table_id = table_id
        self._access_token = None
        self._refresh_token = None
        self._token_expire = 0
        self._use_tenant_token = False
        self._load_token()
    
    def _load_token(self):
        """加载token：优先用用户token，过期则自动切换到应用token"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._access_token = data.get("access_token", "")
                self._refresh_token = data.get("refresh_token", "")
                self._token_expire = data.get("expire_time", 0)
                if self._token_expire == 0:
                    expires_in = data.get("expires_in", 7200)
                    self._token_expire = time.time() + expires_in - 60
                # 如果用户token还没过期，使用它
                if time.time() < self._token_expire:
                    self._use_tenant_token = False
                    return
            except:
                pass
        
        # 用户token不存在或已过期 → 自动用应用token（无需用户任何操作）
        print("  [飞书] 使用应用级token（自动续期，无需扫码）")
        self._use_tenant_token = True
        self._access_token = self._get_tenant_token()
        self._token_expire = time.time() + 7200  # 应用token约2小时，之后自动刷新

    def _save_token(self, data: dict):
        """保存token到文件"""
        # 计算绝对过期时间戳
        expire_time = time.time() + data.get("expires_in", 7200) - 60
        save_data = {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token", ""),
            "expires_in": data.get("expires_in", 7200),
            "expire_time": expire_time
        }
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        self._access_token = data.get("access_token", "")
        self._refresh_token = data.get("refresh_token", "")
        self._token_expire = expire_time

    def _get_tenant_token(self) -> str:
        """获取应用tenant_token（刷新user token时需要）"""
        url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        })
        return resp.json().get("tenant_access_token", "")

    def _refresh_access_token(self):
        """用refresh_token刷新access_token"""
        tenant_token = self._get_tenant_token()
        url = f"{BASE_URL}/authen/v1/oidc/refresh_access_token"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json={
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token
        })
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(
                f"刷新token失败: {data.get('msg')}，请重新运行 feishu_auth.py 授权"
            )
        self._save_token(data.get("data", {}))

    def _ensure_token(self):
        """确保token有效，过期自动刷新"""
        if time.time() >= self._token_expire:
            if self._use_tenant_token:
                # 应用token：直接重新获取（自动续，无需用户操作）
                self._access_token = self._get_tenant_token()
                self._token_expire = time.time() + 7200
                print("  [飞书] 应用token已自动刷新")
            else:
                self._refresh_access_token()

    def _headers(self) -> dict:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, path: str, json_data: dict = None,
                 params: dict = None) -> dict:
        """发送API请求"""
        url = f"{BASE_URL}{path}"
        headers = self._headers()

        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=params)
        else:
            resp = requests.post(url, headers=headers, json=json_data, params=params)

        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"API错误 [{result.get('code')}]: {result.get('msg')}")
        return result.get("data", {})

    def list_records(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """列出所有记录"""
        records = []
        page_token = None

        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            path = f"/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records"
            data = self._request("GET", path, params=params)

            for item in data.get("items", []):
                record = {"_record_id": item["record_id"]}
                record.update(item.get("fields", {}))
                records.append(record)

            if not data.get("has_more"):
                break
            page_token = data.get("page_token")

        return records

    def get_pending_records(self) -> List[Dict[str, Any]]:
        """获取所有待上架的记录"""
        all_records = self.list_records()
        pending = []
        for rec in all_records:
            status = rec.get("上架状态", [])
            if isinstance(status, list) and "待上架" in status:
                pending.append(rec)
            elif status == "待上架":
                pending.append(rec)
        return pending

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录详情"""
        path = f"/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records/{record_id}"
        try:
            data = self._request("GET", path)
            record = {"_record_id": data["record"]["record_id"]}
            record.update(data["record"].get("fields", {}))
            return record
        except Exception:
            return None

    def update_status(self, record_id: str, status: str) -> bool:
        """更新上架状态"""
        return self._update_field(record_id, "上架状态", status)

    def update_skc_id(self, record_id: str, skc_id: str) -> bool:
        """回填SKC ID"""
        return self._update_field(record_id, "SKC ID", skc_id)

    def update_error(self, record_id: str, error_msg: str) -> bool:
        """更新错误信息"""
        return self._update_field(record_id, "错误信息", error_msg)

    def _update_field(self, record_id: str, field_name: str, value: Any) -> bool:
        """更新单个字段"""
        path = f"/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records/batch_update"
        payload = {
            "records": [
                {
                    "record_id": record_id,
                    "fields": {field_name: value}
                }
            ]
        }
        try:
            self._request("POST", path, json_data=payload)
            return True
        except Exception:
            return False
