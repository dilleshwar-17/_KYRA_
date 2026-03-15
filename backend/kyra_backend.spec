# kyra_backend.spec — PyInstaller spec for KYRA backend
# Run: pyinstaller kyra_backend.spec
import os
from pathlib import Path

block_cipher = None

backend_dir = Path(SPECPATH)
model_dir   = backend_dir / "models"
env_file    = backend_dir / ".env"

a = Analysis(
    ['main.py'],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=[
        (str(model_dir), 'models'),
        (str(env_file), '.'),      # bundle .env next to exe
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'comtypes',
        'comtypes.client',
        'sounddevice',
        'soundfile',
        'speech_recognition',
        'openai',
        'dotenv',
        'fastapi',
        'starlette',
        'wakeword',
        'engine',
        'voice',
        'expression_detector',
        'cv2',
        'onnxruntime',
        'numpy',
    ],
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
    [],
    exclude_binaries=True,
    name='kyra_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # set False to hide terminal window in production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kyra_backend',
)
