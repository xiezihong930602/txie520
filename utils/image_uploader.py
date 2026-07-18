# -*- coding: utf-8 -*-
"""
图床上传抽象层
支持多种云存储：七牛云、阿里云OSS、腾讯云COS等
"""
from abc import ABC, abstractmethod
from typing import List


class ImageUploader(ABC):
    """图床上抽象基类"""

    @abstractmethod
    def upload(self, local_path: str, filename: str = None) -> str:
        """上传单张图片，返回公网URL"""
        pass

    def upload_batch(self, local_paths: List[str]) -> List[str]:
        """批量上传，返回URL列表"""
        return [self.upload(p) for p in local_paths]


class QiniuUploader(ImageUploader):
    """七牛云图床"""

    def __init__(self, access_key: str, secret_key: str, bucket: str, domain: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.domain = domain.rstrip("/")
        self._token = None

    def _get_token(self, key: str = None) -> str:
        """生成上传token"""
        try:
            from qiniu import Auth
        except ImportError:
            raise Exception("请先安装七牛云SDK: pip install qiniu")

        q = Auth(self.access_key, self.secret_key)
        return q.upload_token(self.bucket, key, 3600)

    def upload(self, local_path: str, filename: str = None) -> str:
        try:
            from qiniu import put_file
        except ImportError:
            raise Exception("请先安装七牛云SDK: pip install qiniu")

        import os
        key = filename or os.path.basename(local_path)
        token = self._get_token(key)
        ret, info = put_file(token, key, local_path)

        if info.status_code != 200:
            raise Exception(f"七牛上传失败: {info}")

        return f"{self.domain}/{ret.get('key', key)}"


class AliyunOSSUploader(ImageUploader):
    """阿里云OSS图床（预留）"""

    def __init__(self, access_key_id: str, access_key_secret: str,
                 bucket: str, endpoint: str, domain: str = None):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.bucket = bucket
        self.endpoint = endpoint
        self.domain = domain.rstrip("/") if domain else f"https://{bucket}.{endpoint}"

    def upload(self, local_path: str, filename: str = None) -> str:
        raise NotImplementedError("阿里云OSS待实现")


class TencentCOSUploader(ImageUploader):
    """腾讯云COS图床（预留）"""

    def __init__(self, secret_id: str, secret_key: str, bucket: str,
                 region: str, domain: str = None):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region
        self.domain = domain

    def upload(self, local_path: str, filename: str = None) -> str:
        raise NotImplementedError("腾讯云COS待实现")


def create_uploader(config: dict) -> ImageUploader:
    """工厂方法：根据配置创建对应图床上"""
    provider = config.get("provider", "qiniu").lower()

    if provider == "qiniu":
        return QiniuUploader(
            access_key=config.get("access_key", ""),
            secret_key=config.get("secret_key", ""),
            bucket=config.get("bucket", ""),
            domain=config.get("domain", "")
        )
    elif provider == "aliyun":
        return AliyunOSSUploader(
            access_key_id=config.get("access_key_id", ""),
            access_key_secret=config.get("access_key_secret", ""),
            bucket=config.get("bucket", ""),
            endpoint=config.get("endpoint", ""),
            domain=config.get("domain", "")
        )
    elif provider == "tencent":
        return TencentCOSUploader(
            secret_id=config.get("secret_id", ""),
            secret_key=config.get("secret_key", ""),
            bucket=config.get("bucket", ""),
            region=config.get("region", ""),
            domain=config.get("domain", "")
        )
    else:
        raise ValueError(f"不支持的图床类型: {provider}")
