"""
Build script completo para criar o instalador do Water Intake Tracker

Este script:
1. Compila o executavel com PyInstaller
2. Sincroniza os arquivos de recursos
3. Compila o instalador com Inno Setup

Requisitos:
    - Python 3.x
    - PyInstaller: pip install pyinstaller
    - Inno Setup 6.x instalado (https://jrsoftware.org/isinfo.php)

Uso:
    python build_installer.py           # Build completo
    python build_installer.py --exe     # Apenas o executavel
    python build_installer.py --iss     # Apenas o instalador (requer exe existente)
"""

import subprocess
import sys
import os
import shutil
import argparse
from pathlib import Path


# Configuracoes
APP_NAME = "WaterIntakeTracker"
VERSION = "1.0.0"

# Pastas de recursos que precisam estar ao lado do exe
RESOURCE_FOLDERS = ["sounds", "mascots", "personalities", "models", "data"]

# Arquivos adicionais
RESOURCE_FILES = ["icon.ico", "user_config.json"]

# Caminhos comuns do Inno Setup
INNO_SETUP_PATHS = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    r"C:\Program Files\Inno Setup 5\ISCC.exe",
    # Instalação por usuário (AppData)
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    os.path.expanduser(r"~\AppData\Local\Programs\Inno Setup 6\ISCC.exe"),
]


def find_inno_setup():
    """Encontra o compilador do Inno Setup"""
    for path in INNO_SETUP_PATHS:
        if os.path.exists(path):
            return path

    # Tenta encontrar no PATH
    try:
        result = subprocess.run(["where", "iscc"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass

    return None


def convert_icon():
    """Converte icon.webp para icon.ico se necessario"""
    if os.path.exists('icon.ico'):
        print("  [OK] icon.ico ja existe")
        return True

    if not os.path.exists('icon.webp'):
        print("  [!] Nenhum icone encontrado")
        return False

    try:
        from PIL import Image
    except ImportError:
        print("  Instalando Pillow...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
        from PIL import Image

    print("  Convertendo icon.webp -> icon.ico...")
    img = Image.open('icon.webp')
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = [img.resize(size, Image.Resampling.LANCZOS) for size in sizes]

    images[0].save(
        'icon.ico',
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    print("  [OK] Icone convertido")
    return True


def build_exe():
    """Compila o executavel com PyInstaller"""
    print("\n" + "=" * 50)
    print("ETAPA 1: Compilando executavel")
    print("=" * 50)

    # Verifica PyInstaller
    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])

    # Converte icone
    convert_icon()

    # Usa o spec file se existir
    if os.path.exists("WaterIntakeTracker.spec"):
        cmd = [sys.executable, "-m", "PyInstaller", "WaterIntakeTracker.spec", "--noconfirm"]
    else:
        print("  [!] Arquivo .spec nao encontrado, usando configuracao padrao")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name=WaterIntakeTracker",
            "--onefile",
            "--windowed",
            "--icon=icon.ico",
            "--add-data=sounds;sounds",
            "--add-data=mascots;mascots",
            "--add-data=personalities;personalities",
            "--add-data=models;models",
            "--add-data=data;data",
            "--hidden-import=winsound",
            "--hidden-import=mediapipe",
            "--hidden-import=cv2",
            "--hidden-import=PyQt5",
            "--collect-data=mediapipe",
            "main.py"
        ]

    print("  Compilando... (isso pode levar alguns minutos)")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("  [ERRO] Falha na compilacao!")
        print(result.stderr)
        return False

    exe_path = os.path.join("dist", f"{APP_NAME}.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  [OK] Executavel criado: {exe_path} ({size_mb:.1f} MB)")
        return True
    else:
        print("  [ERRO] Executavel nao encontrado!")
        return False


def sync_resources():
    """Sincroniza pastas de recursos para a pasta dist"""
    print("\n" + "=" * 50)
    print("ETAPA 2: Sincronizando recursos")
    print("=" * 50)

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("  [ERRO] Pasta dist/ nao encontrada!")
        return False

    # Sincroniza pastas
    for folder in RESOURCE_FOLDERS:
        src = Path(folder)
        dst = dist_dir / folder

        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            count = sum(1 for _ in dst.rglob("*") if _.is_file())
            print(f"  [OK] {folder}/ ({count} arquivos)")
        else:
            print(f"  [!] {folder}/ nao encontrado (ignorando)")

    # Sincroniza arquivos
    for file in RESOURCE_FILES:
        src = Path(file)
        dst = dist_dir / file

        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [OK] {file}")
        else:
            print(f"  [!] {file} nao encontrado")

    return True


def build_installer():
    """Compila o instalador com Inno Setup"""
    print("\n" + "=" * 50)
    print("ETAPA 3: Criando instalador")
    print("=" * 50)

    # Verifica se o exe existe
    exe_path = os.path.join("dist", f"{APP_NAME}.exe")
    if not os.path.exists(exe_path):
        print("  [ERRO] Executavel nao encontrado!")
        print("         Execute primeiro: python build_installer.py --exe")
        return False

    # Encontra o Inno Setup
    iscc = find_inno_setup()
    if not iscc:
        print("  [ERRO] Inno Setup nao encontrado!")
        print("")
        print("  Por favor instale o Inno Setup 6:")
        print("  https://jrsoftware.org/isdl.php")
        print("")
        print("  Ou adicione ISCC.exe ao PATH do sistema.")
        return False

    print(f"  Inno Setup: {iscc}")

    # Verifica o script
    if not os.path.exists("installer.iss"):
        print("  [ERRO] installer.iss nao encontrado!")
        return False

    # Cria pasta de saida
    os.makedirs("installer_output", exist_ok=True)

    # Compila
    print("  Compilando instalador...")
    result = subprocess.run([iscc, "installer.iss"], capture_output=True, text=True)

    if result.returncode != 0:
        print("  [ERRO] Falha na compilacao do instalador!")
        print(result.stdout)
        print(result.stderr)
        return False

    # Verifica o resultado
    output_file = f"installer_output/WaterIntakeTracker_Setup_{VERSION}.exe"
    if os.path.exists(output_file):
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"  [OK] Instalador criado: {output_file} ({size_mb:.1f} MB)")
        return True
    else:
        print("  [ERRO] Instalador nao encontrado!")
        return False


def main():
    parser = argparse.ArgumentParser(description="Build Water Intake Tracker Installer")
    parser.add_argument("--exe", action="store_true", help="Apenas compilar o executavel")
    parser.add_argument("--iss", action="store_true", help="Apenas criar o instalador")
    parser.add_argument("--sync", action="store_true", help="Apenas sincronizar recursos")
    args = parser.parse_args()

    print("")
    print("=" * 50)
    print(f"  WATER INTAKE TRACKER - BUILD v{VERSION}")
    print("=" * 50)

    success = True

    if args.exe:
        success = build_exe()
    elif args.iss:
        success = sync_resources() and build_installer()
    elif args.sync:
        success = sync_resources()
    else:
        # Build completo
        success = build_exe() and sync_resources() and build_installer()

    print("\n" + "=" * 50)
    if success:
        print("  BUILD COMPLETO!")
        if not args.exe and not args.sync:
            print("")
            print(f"  Instalador: installer_output/WaterIntakeTracker_Setup_{VERSION}.exe")
            print("")
            print("  Proximo passo: Teste o instalador em uma VM ou outro PC")
    else:
        print("  BUILD FALHOU!")
        print("  Verifique os erros acima.")
    print("=" * 50)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
