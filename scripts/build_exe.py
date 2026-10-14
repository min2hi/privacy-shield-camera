"""
build_exe.py — Script đóng gói ứng dụng Privacy Shield Camera thành file .exe
sử dụng PyInstaller cho Windows.

Usage:
    python scripts/build_exe.py
"""
import subprocess
import sys
from pathlib import Path

# Paths
APP_DIR = Path(__file__).parent.parent / "privacy-shield-app"
MAIN_SCRIPT = APP_DIR / "main.py"
MODELS_DIR = APP_DIR / "models"
CONFIGS_DIR = APP_DIR / "configs"
ICON_PATH = APP_DIR / "assets" / "icon.ico"  # Optional

# PyInstaller arguments
args = [
    sys.executable, "-m", "PyInstaller",
    str(MAIN_SCRIPT),
    "--name=PrivacyShieldCamera",
    "--onedir",
    "--windowed",
    "--noconfirm",
    "--clean",
    # Add data files
    f"--add-data={MODELS_DIR};models",
    f"--add-data={CONFIGS_DIR};configs",
    # Hidden imports for dynamic loading
    "--hidden-import=app.core.detector",
    "--hidden-import=app.core.face_recognizer",
    "--hidden-import=app.core.pipeline",
    "--hidden-import=app.core.masking",
    "--hidden-import=app.core.frame_scheduler",
    "--hidden-import=app.core.temporal_smoothing",
    "--hidden-import=app.core.virtual_camera",
    "--hidden-import=app.core.model_bundle",
    "--hidden-import=app.ui.main_window",
    "--hidden-import=app.ui.camera_worker",
    "--hidden-import=app.ui.custom_widgets",
    "--hidden-import=app.ui.enroll_dialog",
    "--hidden-import=app.ui.style_sheets",
    "--hidden-import=app.utils.config_loader",
    "--hidden-import=app.utils.console",
    "--hidden-import=app.utils.logging_config",
    "--hidden-import=onnxruntime",
    "--hidden-import=ultralytics",
    # Exclude unnecessary packages
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=scipy",
    "--exclude-module=pandas",
    # Output directory
    f"--distpath={Path(__file__).parent.parent / 'dist'}",
    f"--workpath={Path(__file__).parent.parent / 'build'}",
    f"--specpath={Path(__file__).parent.parent / 'build'}",
]

# Add icon if exists
if ICON_PATH.exists():
    args.append(f"--icon={ICON_PATH}")

print("\n🛡️ Building Privacy Shield Camera...")
print(f"  Entry: {MAIN_SCRIPT}")
print(f"  Models: {MODELS_DIR}")
print(f"  Configs: {CONFIGS_DIR}")
print()

result = subprocess.run(args, cwd=str(Path(__file__).parent.parent))

if result.returncode == 0:
    print("\n✅ Build successful!")
    print("   Output: dist/PrivacyShieldCamera/")
else:
    print("\n❌ Build failed!")
    sys.exit(1)
