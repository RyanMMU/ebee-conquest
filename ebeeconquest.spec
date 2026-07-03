from pathlib import Path


projectroot = Path(SPECPATH)
datadirectories = (
    "assets",
    "flags",
    "fonts",
    "game/data",
    "game/images",
    "game/sounds",
    "game/speeches",
    "images",
    "map",
    "scripts",
)
datas = [
    (str(projectroot / directory), directory.replace("/", "\\"))
    for directory in datadirectories
]

analysis = Analysis(
    [str(projectroot / "main.py")],
    pathex=[str(projectroot)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pythonarchive = PYZ(analysis.pure)

executable = EXE(
    pythonarchive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="ebeeconquest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(projectroot / "game" / "images" / "ebeeconquestlogo.png"),
    version=str(projectroot / "tools" / "ebeeconquest_version_info.txt"),
)
