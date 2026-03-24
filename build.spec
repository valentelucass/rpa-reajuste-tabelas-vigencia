# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).resolve()
APP_NAME = "RPA-Reajuste-Tabelas-Vigencia"
ICON_FILE = ROOT / "public" / "app-icon.ico"


def _listar_modulos_internos() -> list[str]:
    modulos = {"config"}

    for arquivo in (ROOT / "src").rglob("*.py"):
        relativo = arquivo.relative_to(ROOT).with_suffix("")
        if relativo.name == "__init__":
            modulos.add(".".join(relativo.parts[:-1]))
            continue
        modulos.add(".".join(relativo.parts))

    return sorted(modulos)


def _listar_assets_publicos() -> list[tuple[str, str]]:
    assets: list[tuple[str, str]] = []
    public_dir = ROOT / "public"

    if not public_dir.exists():
        return assets

    for arquivo in public_dir.rglob("*"):
        if not arquivo.is_file():
            continue
        destino = arquivo.parent.relative_to(ROOT).as_posix()
        assets.append((str(arquivo), destino))

    return assets


hiddenimports = sorted(
    {
        *collect_submodules("selenium"),
        *_listar_modulos_internos(),
    }
)

datas = _listar_assets_publicos()


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
