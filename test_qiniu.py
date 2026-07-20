import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.image_uploader import create_uploader
from config.settings import IMAGE_BED_CONFIG
import requests

print("测试七牛云配置...")
print(f"domain: {IMAGE_BED_CONFIG['domain']}")
print(f"bucket: {IMAGE_BED_CONFIG['bucket']}")

# 先测试域名能不能访问
try:
    r = requests.get(IMAGE_BED_CONFIG['domain'], timeout=10)
    print(f"\n域名访问测试: status={r.status_code}")
except Exception as e:
    print(f"\n域名访问失败: {e}")

# 创建一个测试图片（1x1像素png）
test_file = "test_qiniu.png"
with open(test_file, "wb") as f:
    # 最小的png文件
    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

print(f"\n测试上传...")
uploader = create_uploader(IMAGE_BED_CONFIG)
try:
    url = uploader.upload(test_file, filename="test_upload.png")
    print(f"上传成功，URL: {url}")
    
    # 测试URL能不能访问
    print(f"\n测试URL访问...")
    r = requests.get(url, timeout=10)
    print(f"URL访问状态: {r.status_code}, Content-Type: {r.headers.get('Content-Type')}")
    if r.status_code == 200:
        print("公网访问正常！")
    else:
        print(f"访问失败，返回内容: {r.text[:200]}")
except Exception as e:
    print(f"上传失败: {e}")
    import traceback
    traceback.print_exc()

os.remove(test_file)
