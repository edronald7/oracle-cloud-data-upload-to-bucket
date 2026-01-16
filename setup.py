import os
import sys
import subprocess
from pathlib import Path
import stat

def find_python_cmd():
    for cmd in ["python3", "python", "py"]:
        try:
            subprocess.run([cmd, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return cmd
        except Exception:
            continue
    print("Python 3 is not installed. Please install Python 3 to continue.")
    sys.exit(1)

def create_run_script():
    if os.name == "nt":
        # Windows run.bat
        script = (
            "@echo off\n"
            "IF NOT DEFINED VIRTUAL_ENV (\n"
            "    echo Activating virtual environment...\n"
            "    CALL venv\\Scripts\\activate.bat\n"
            ") ELSE (\n"
            "    echo Virtual environment is already activated.\n"
            ")\n"
            "python main.py\n"
        )
        with open("run.bat", "w") as f:
            f.write(script)
        print("Created run.bat for Windows.")
    else:
        # Unix-like run.sh
        script = (
            "#!/bin/bash\n"
            "if [ -z \"$VIRTUAL_ENV\" ]; then\n"
            "    echo \"Activating virtual environment...\"\n"
            "    source venv/bin/activate\n"
            "else\n"
            "    echo \"Virtual environment is already activated.\"\n"
            "fi\n"
            "python main.py\n"
        )
        run_path = Path("run.sh")
        run_path.write_text(script)
        # chmod +x run.sh to make it executable
        run_path.chmod(run_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print("Created run.sh for Unix/Linux/macOS and set it executable.")

def main():
    python_cmd = find_python_cmd()
    venv_dir = Path("venv")
    pip_path = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "pip"

    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.run([python_cmd, "-m", "venv", str(venv_dir)], check=True)
    else:
        print("Virtual environment already exists.")

    if not Path("requirements.txt").exists():
        print("requirements.txt not found. Please create it with the necessary dependencies.")
        sys.exit(1)

    if not pip_path.exists():
        print("pip not found in the virtual environment. Installing pip...")
        subprocess.run([python_cmd, "-m", "ensurepip", "--upgrade"], check=True)

    print("Installing dependencies from requirements.txt...")
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)

    create_run_script()

    print("Setup completed successfully.")

if __name__ == "__main__":
    main()