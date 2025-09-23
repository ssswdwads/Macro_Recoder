# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    # 确保路径正确
    [r'C:\Users\ASUS\Desktop\study\Keyboard\main.py'],
    # 添加项目路径
    pathex=[r'C:\Users\ASUS\Desktop\study\Keyboard'],
    binaries=[],
    datas=[],
    # 添加必要的隐藏导入
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MacroRecorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为 True 可以在调试时查看控制台输出
    icon=r'C:\Users\ASUS\Desktop\study\Keyboard\app_icon.ico',  # 确保图标路径正确
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MacroRecorder',
)