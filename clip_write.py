# -*- coding: utf-8 -*-
import subprocess, sys
data = sys.argv[1] if len(sys.argv) > 1 else '尺码\t胸围全围(cm)\n120\t78'
temp_path = sys.argv[2] if len(sys.argv) > 2 else 'clip_data.txt'

# Write TSV as UTF-16LE
with open(temp_path, 'w', encoding='utf-16-le') as f:
    f.write(data)

# PowerShell SetText from file
ps = f'''Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetText((Get-Content -Path '{temp_path}' -Encoding Unicode -Raw))'''
subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
print('OK')
