from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import settings


PROJECT_ROOT = Path(settings.PROJECT_ROOT)


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def clear_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        remove_path(child)


def remove_recursive_named(root: Path, names: set[str]) -> int:
    removed = 0
    for current_root, dirnames, filenames in os.walk(root, topdown=False):
        current = Path(current_root)
        for filename in filenames:
            if filename in names:
                remove_path(current / filename)
                removed += 1
        for dirname in dirnames:
            if dirname in names:
                remove_path(current / dirname)
                removed += 1
    return removed


def stop_docker_compose() -> None:
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        return
    try:
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass


def reset_env() -> None:
    settings._write_env("openai", api_key="")
    settings._write_env_values(
        {
            "FIRST_START_DONE": "0",
            "LOG_LEVEL": "WARNING",
            "OBSIDIAN_VAULT_PATH": "",
            "GITHUB_TOKEN": "",
            "GITHUB_DEFAULT_REPO": "",
            "SUBSCRIPTION_PLAN": "studio",
            "ACCESS_MODE": "approval",
            "FILE_ACCESS_MODE": "approval",
            "SHELL_ACCESS_MODE": "approval",
            "TOOL_WEB_ENABLED": "1",
            "TOOL_OBSIDIAN_ENABLED": "1",
            "TOOL_UPLOADS_ENABLED": "1",
            "TOOL_ZIP_ENABLED": "1",
            "TOOL_PDF_ENABLED": "1",
            "TOOL_GITHUB_READ_ENABLED": "1",
            "TOOL_GITHUB_WRITE_ENABLED": "1",
            "TOOL_PROJECT_SCAN_ENABLED": "1",
        }
    )


def main() -> int:
    print("AgentCompany reset")
    print(f"Project: {PROJECT_ROOT}")
    print()
    print("This will reset the project to a clean default state.")
    print("It will:")
    print("- stop Docker Compose if it is running")
    print("- reset .env to default values")
    print("- clear databases/")
    print("- clear incoming_files/")
    print("- clear memory/")
    print("- clear workspaces/")
    print("- remove .DS_Store and __pycache__")
    print()
    print("It will keep:")
    print("- source code")
    print("- .venv")
    print()

    if "--yes" not in sys.argv:
        confirm = input("Type RESET to continue: ").strip()
        if confirm != "RESET":
            print("Cancelled.")
            return 1

    stop_docker_compose()
    reset_env()

    clear_directory(Path(settings.DB_DIR))
    clear_directory(Path(settings.INBOX_DIR))
    clear_directory(Path(settings.MEMORY_DIR))
    clear_directory(Path(settings.WORKSPACE_DIR))

    removed_misc = remove_recursive_named(
        PROJECT_ROOT,
        {".DS_Store", "__pycache__"},
    )

    print()
    print("Reset complete.")
    print(f"- Databases cleared: {settings.DB_DIR}")
    print(f"- Upload inbox cleared: {settings.INBOX_DIR}")
    print(f"- Memory cleared: {settings.MEMORY_DIR}")
    print(f"- Workspaces cleared: {settings.WORKSPACE_DIR}")
    print(f"- Extra generated items removed: {removed_misc}")
    print("- .env reset to default OpenAI mode with no API key")
    print()
    print("Next steps:")
    print("1. Configure a provider again:")
    print("   python3 settings.py setup openai")
    print("   or")
    print("   python3 settings.py setup ollama")
    print("2. Start the app:")
    print("   python3 webapp.py 7842")
    print("   or")
    print("   docker compose up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
