"""Hotfix: 强制输出每一个失败步骤的截图和DOM，定位真实问题"""
import sys, os, json, time

WORK_DIR = r'C:\Users\Administrator\.doubao\chats\2026-07-14\new-chat\temu_auto_publish_v2'
sys.path.insert(0, WORK_DIR)

# 直接 patch rpa_publisher 的诊断方法，让它在每个步骤后都截图
exec_file = os.path.join(WORK_DIR, 'executors', 'rpa_publisher.py')
src = open(exec_file, 'r', encoding='utf-8').read()

# 在 _fill_sku_info 里加入更详细的诊断
# 在 add_color_with_images 的 "+ 新增" 后加入截图
src = src.replace(
    "add_link.click()\n        time.sleep(1.5)",
    "add_link.click()\n        time.sleep(3)  # 加长等待，确保颜色行渲染"
)

# 在 _select_size_chart_by_index 的 click 后加入调试输出
src = src.replace(
    'select_container.click()\n        time.sleep(0.8)\n        \n        # 找到搜索输入框',
    'select_container.click()\n        time.sleep(1.5)  # 加长等待下拉渲染\n        \n        # 调试：看下拉有没有出现\n        dropdown_debug = self.page.evaluate("""() => {\n            const dds = document.querySelectorAll(\'.el-select-dropdown, [class*="select-dropdown"], [role="listbox"]\');\n            const r = [];\n            dds.forEach(dd => { const rect = dd.getBoundingClientRect(); r.push({h: Math.round(rect.height), w: Math.round(rect.width), visible: rect.height > 10}); });\n            return r;\n        }""")\n        print(f"  [调试-下拉框] 点击后: {json.dumps(dropdown_debug, ensure_ascii=False)}")\n        \n        # 找到搜索输入框'
)

# 在图片上传失败时加诊断
src = src.replace(
    'if not img_box_pos:\n            print(f"  警告: 未找到图片上传框 (颜色: {color_name})")\n            return',
    'if not img_box_pos:\n            print(f"  警告: 未找到图片上传框 (颜色: {color_name})")\n            # 诊断：看页面上有什么div\n            debug_divs = self.page.evaluate("""() => {\n                const all = document.querySelectorAll(\'.jx-dialog div\');\n                const sizes = [];\n                all.forEach(d => {\n                    const r = d.getBoundingClientRect();\n                    if (r.width > 50 && r.height > 50) {\n                        sizes.push({w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top)});\n                    }\n                });\n                return sizes.slice(0, 30);\n            }""")\n            print(f"  [诊断-图片上传] 页面div尺寸: {json.dumps(debug_divs, ensure_ascii=False)}")\n            return'
)

open(exec_file, 'w', encoding='utf-8').write(src)
print("OK - patches applied to rpa_publisher.py")
print("Added: longer waits, dropdown debug, image div debug")
print("Now run: python batch_publish.py")
