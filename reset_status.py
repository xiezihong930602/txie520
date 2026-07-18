import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_source.feishu import FeishuDataSource

ds = FeishuDataSource('Z69Pb8Zpua8h3PsKiumcidJ0nEg', 'tbl8vDRirTY5Cv3Y')
for r in ds.list_records():
    if '男童' in str(r.get('产品标题', '')):
        ds._update_field(r['_record_id'], '上架状态', '待上架')
        print(f"已重置: {r.get('产品标题')} → 待上架")
        break
