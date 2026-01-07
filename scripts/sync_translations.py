from pathlib import Path
import shutil


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    component_dir = project_root / "custom_components" / "trados_cloud"
    src = component_dir / "strings.json"
    dest_dir = component_dir / "translations"
    dest = dest_dir / "en.json"

    if not src.exists():
        raise SystemExit("strings.json not found; cannot sync translations")

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    print(f"Copied {src} -> {dest}")


if __name__ == "__main__":
    main()
