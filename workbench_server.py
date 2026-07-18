# -*- coding: utf-8 -*-
"""
工作台本地服务
提供HTTP接口，让网页按钮可以调用本地脚本
"""
import os
import sys
import json
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(WORK_DIR, "工作台.html")
PORT = 8765

_running_task = None
_task_output = []
_task_lock = threading.Lock()


def get_stats():
    """获取飞书数据统计"""
    try:
        sys.path.insert(0, WORK_DIR)
        from data_source.feishu import FeishuDataSource
        from config.settings import FEISHU_BASE_TOKEN

        TABLE_PRODUCT = "tbl8vDRirTY5Cv3Y"
        ds = FeishuDataSource(FEISHU_BASE_TOKEN, TABLE_PRODUCT)
        records = ds.list_records()

        total = len(records)
        pending = 0
        success = 0
        fail = 0

        for rec in records:
            status = rec.get("上架状态", [])
            if isinstance(status, list):
                status = status[0] if status else ""
            if status == "待上架":
                pending += 1
            elif status == "已上架":
                success += 1
            elif status == "上架失败":
                fail += 1

        return {
            "total": total,
            "pending": pending,
            "success": success,
            "fail": fail
        }
    except Exception as e:
        print("[统计接口错误]", e)
        return {
            "total": 0,
            "pending": 0,
            "success": 0,
            "fail": 0,
            "error": str(e)
        }


def run_script(script_name):
    """后台运行脚本"""
    global _running_task, _task_output
    with _task_lock:
        if _running_task and _running_task.is_alive():
            return False, "有任务正在运行，请稍候"

    _task_output.clear()
    _task_output.append("=== 开始执行: " + script_name + " ===")

    def target():
        global _task_output
        try:
            proc = subprocess.Popen(
                [sys.executable, "-u", script_name],
                cwd=WORK_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="gbk",
                bufsize=1
            )
            for line in proc.stdout:
                with _task_lock:
                    _task_output.append(line.rstrip())
            proc.wait()
            with _task_lock:
                _task_output.append("=== 执行完成，退出码: " + str(proc.returncode) + " ===")
        except Exception as e:
            with _task_lock:
                _task_output.append("执行异常: " + str(e))

    t = threading.Thread(target=target, daemon=True)
    t.start()
    with _task_lock:
        _running_task = t
    return True, "任务已启动"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            try:
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    html = f.read()
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self._send_json({"error": "工作台页面不存在"}, 404)
        elif path == "/api/status":
            with _task_lock:
                running = _running_task.is_alive() if _running_task else False
                output = list(_task_output)
            self._send_json({"running": running, "output": output})
        elif path == "/api/stats":
            stats = get_stats()
            self._send_json(stats)
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/sync":
            ok, msg = run_script("sync_images.py")
            self._send_json({"ok": ok, "msg": msg})
        elif path == "/api/publish":
            ok, msg = run_script("batch_publish.py")
            self._send_json({"ok": ok, "msg": msg})
        elif path == "/api/stop":
            global _running_task, _task_output
            with _task_lock:
                if _running_task and _running_task.is_alive():
                    _task_output.append("=== 用户手动停止 ===")
                    _running_task = None
                self._send_json({"ok": True, "msg": "stopped"})
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("工作台服务已启动: http://127.0.0.1:" + str(PORT))
    print("不要关闭此窗口，关闭后网页按钮将失效")
    print()
    print("浏览器打开: http://127.0.0.1:" + str(PORT))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()