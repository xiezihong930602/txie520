@echo off
setlocal

set LARK_CLI=C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\sandbox_envs_dir\envs\084fee42-5307-4ea4-9732-9d2e322248ff\override_dlcs\lark-cli.exe
set BASE_TOKEN=Z69Pb8Zpua8h3PsKiumcidJ0nEg
set TABLE_ID=tblgZesB3dnXUgqj

echo 创建字段中...

echo {"type": "text", "name": "款式名称"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "select", "name": "分类", "options": [{"name": "儿童"}, {"name": "成人"}]} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "模板名称"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "产品标题"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "number", "name": "成本价"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "number", "name": "供货价"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "尺码列表"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "SKU分类"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "颜色名称"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "attachment", "name": "商品主图"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "select", "name": "上架状态", "options": [{"name": "待上架"}, {"name": "上架中"}, {"name": "已上架"}, {"name": "上架失败"}]} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "SKC ID"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "错误信息"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

echo {"type": "text", "name": "备注"} > _f.json
%LARK_CLI% base +field-create --base-token %BASE_TOKEN% --table-id %TABLE_ID% --json @_f.json
echo.

del _f.json
echo 全部完成!
pause
