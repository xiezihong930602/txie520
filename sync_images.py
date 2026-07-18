import functools
print = functools.partial(print, flush=True)
# -*- coding: utf-8 -*-
"""
飞书附件转存公网图床脚本
读取颜色明细表的附件 → 下载到本地 → 上传图床 → 回填公网URL到飞书
"""
import os
import sys
import time
import requests
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.feishu import FeishuDataSource, BASE_URL
from utils.image_uploader import create_uploader
from config.settings import (
    FEISHU_BASE_TOKEN, IMAGE_BED_CONFIG,
    FEISHU_APP_ID, FEISHU_APP_SECRET
)

TABLE_COLOR = "tblxluGYXQyNK36g"  # 颜色明细表
ATTACH_FIELD = "商品主图"          # 附件字段名
URL_FIELD = "图片公网URL"          # 公网URL字段名（需要在飞书里新建文本字段）


def download_feishu_attachment(url: str, access_token: str, save_path: str) -> bool:
    """下载飞书附件到本地"""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"    下载失败: {e}")
    return False


def get_attach_urls(attach_val: list) -> list:
    """从附件字段值提取下载URL和文件名"""
    urls = []
    if not attach_val or not isinstance(attach_val, list):
        return urls
    for item in attach_val:
        if isinstance(item, dict):
            url = item.get("url") or item.get("tmp_url") or ""
            name = item.get("name", f"img_{int(time.time())}.jpg")
            if url:
                urls.append({"url": url, "name": name})
    return urls


def main():
    print("=" * 50)
    print("  飞书图片转存公网图床")
    print("=" * 50)
    print()

    # 初始化
    color_ds = FeishuDataSource(FEISHU_BASE_TOKEN, TABLE_COLOR)
    uploader = create_uploader(IMAGE_BED_CONFIG)

    # 临时目录
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_images")
    os.makedirs(tmp_dir, exist_ok=True)

    # 读取所有颜色记录
    print("[1/3] 读取颜色明细记录...")
    records = color_ds.list_records()
    print(f"  共 {len(records)} 条记录")

    # 筛选有附件但还没转存的
    todo = []
    for rec in records:
        attach = rec.get(ATTACH_FIELD, [])
        url_field = rec.get(URL_FIELD, "")
        if attach and not url_field:
            todo.append(rec)

    print(f"  待转存: {len(todo)} 条")
    if not todo:
        print("  没有需要转存的图片")
        return

    print(f"\n[2/3] 开始转存，共 {len(todo)} 条...")
    success = 0
    fail = 0

    for idx, rec in enumerate(todo, 1):
        record_id = rec.get("_record_id", "")
        color_name = rec.get("颜色名称", "未命名")
        print(f"\n[{idx}/{len(todo)}] {color_name}")

        attach_list = get_attach_urls(rec.get(ATTACH_FIELD, []))
        if not attach_list:
            print("  无有效附件，跳过")
            continue

        public_urls = []
        all_ok = True

        for i, att in enumerate(attach_list, 1):
            local_path = os.path.join(tmp_dir, f"{record_id}_{i}_{att['name']}")

            # 下载
            print(f"  下载 {i}/{len(attach_list)}: {att['name']}")
            ok = download_feishu_attachment(att["url"], color_ds._access_token, local_path)
            if not ok:
                print(f"    [FAIL] 下载失败")
                all_ok = False
                continue

            # 上传
            print(f"  上传图床...")
            try:
                url = uploader.upload(local_path, filename=f"temu/{color_name}_{int(time.time())}_{i}.jpg")
                public_urls.append(url)
                print(f"    [OK] {url[:60]}...")
            except Exception as e:
                print(f"    [FAIL] 上传失败: {e}")
                all_ok = False

            # 清理本地文件
            if os.path.exists(local_path):
                os.remove(local_path)

        # 回填URL到飞书
        if public_urls:
            url_text = "\n".join(public_urls)
            ok = color_ds._update_field(record_id, URL_FIELD, url_text)
            if ok:
                print(f"  [OK] 已回填 {len(public_urls)} 个URL")
                success += 1
            else:
                print(f"  [FAIL] 回填飞书失败")
                fail += 1
        else:
            fail += 1

    print(f"\n[3/3] 完成！成功 {success}，失败 {fail}")
    print()
    print("RPA上架时会自动读取「图片公网URL」字段上传")


if __name__ == "__main__":
    main()
