import zipfile
import xml.etree.ElementTree as ET
import os

os.chdir('C:/Users/Administrator/.doubao/chats/2026-07-14/new-chat/temu_auto_publish_v2')

ns = {
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
}

results = []

with zipfile.ZipFile('产品目录表.xlsx', 'r') as z:
    drawing_files = [f for f in z.namelist() if 'drawing' in f and f.endswith('.xml')]
    
    for drawing_file in drawing_files:
        print(f'解析 {drawing_file}...')
        content = z.read(drawing_file).decode('utf-8')
        root = ET.fromstring(content)
        
        for pic in root.findall('.//xdr:pic', ns):
            from_elem = pic.find('.//xdr:from', ns)
            if from_elem is not None:
                row = int(from_elem.find('xdr:row', ns).text)
                col = int(from_elem.find('xdr:col', ns).text)
            else:
                row = -1
                col = -1
            
            blip = pic.find('.//a:blip', ns)
            if blip is not None:
                r_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            else:
                r_id = ''
            
            results.append({
                'drawing': drawing_file,
                'row': row,
                'col': col,
                'r_id': r_id
            })

print(f'找到 {len(results)} 个图片位置')
results.sort(key=lambda x: x['row'])
for r in results[:15]:
    print(f'  行{r["row"]}, 列{r["col"]}, rId={r["r_id"]}')

# 保存结果
import json
with open('image_positions.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('已保存到 image_positions.json')
