#!/usr/bin/env python3
"""Build and verify a deterministic, single-root ComfyUI Release ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "ComfyUI-SkinBeauty-CN"
ROOT_FILES = {
    "__init__.py", "nodes.py", "semantic_mediapipe.py", "skin_core.py", "pyproject.toml",
    "README.md", "README_EN.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "SUPPORT.md", "THIRD_PARTY_NOTICES.md",
    "OPEN_SOURCE_RESEARCH.md", "RELEASE_NOTES_v2.2.1.md", "AGENTS.md",
}
INCLUDED_DIRS = {"web", "locales", "workflows", "extras", "docs"}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".git", ".github", "tests", "tools", "dist", "release"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip", ".mp4"}
WINDOWS_ABSOLUTE = re.compile(r"(?i)(?<![a-z])[a-z]:[\\/](?![\\/])")
UNIX_HOME = re.compile(r"(?:^|[\s\"'])/(?:home|Users)/")
SECRET = re.compile(r"(?i)(github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        raise ValueError("pyproject.toml has no project version")
    return match.group(1)


def candidates() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS or part.startswith(".venv") for part in relative.parts):
            continue
        if path.name.endswith(".backup.json") or ".backup-" in path.name:
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        if len(relative.parts) == 1:
            if path.name in ROOT_FILES:
                files.append(path)
        elif relative.parts[0] in INCLUDED_DIRS:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def verify_sources(files: list[Path]) -> None:
    required = {ROOT / name for name in ROOT_FILES}
    missing = sorted(str(path.relative_to(ROOT)) for path in required if not path.is_file())
    if missing:
        raise ValueError(f"missing release files: {missing}")
    if (ROOT / "requirements.txt").exists() or (ROOT / "install.py").exists() or (ROOT / "uninstall.py").exists():
        raise ValueError("automatic dependency/install file exists at repository root")
    for path in files:
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS or part.startswith(".venv") for part in relative.parts):
            raise ValueError(f"excluded path selected: {relative}")
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            text = path.read_text(encoding="utf-8")
            if WINDOWS_ABSOLUTE.search(text) or UNIX_HOME.search(text):
                raise ValueError(f"absolute local path in release file: {relative}")
            if SECRET.search(text):
                raise ValueError(f"high-confidence secret in release file: {relative}")
        if path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))


def write_archive(output_dir: Path) -> tuple[Path, str, int]:
    files = candidates()
    verify_sources(files)
    version = project_version()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{PACKAGE_NAME}_v{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{PACKAGE_NAME}/{relative}", date_time=(2026, 8, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    verify_archive(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return archive, digest, len(files)


def verify_archive(archive: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if not names or {name.split("/", 1)[0] for name in names} != {PACKAGE_NAME}:
            raise ValueError("release ZIP must have exactly one top-level package directory")
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP member")
        if f"{PACKAGE_NAME}/__init__.py" not in names:
            raise ValueError("package root is nested or missing __init__.py")
        for name in names:
            parts = Path(name).parts
            if any(part in EXCLUDED_PARTS or part.startswith(".venv") for part in parts):
                raise ValueError(f"excluded content in ZIP: {name}")
            if Path(name).suffix.lower() in EXCLUDED_SUFFIXES:
                raise ValueError(f"excluded suffix in ZIP: {name}")


def write_metadata(output_dir: Path, archive: Path, digest: str, count: int) -> None:
    version = project_version()
    (output_dir / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    (output_dir / f"RELEASE_REPORT_v{version}.md").write_text(
        "\n".join((
            f"# Release build report v{version}", "",
            f"- Archive: `{archive.name}`", f"- SHA256: `{digest}`",
            f"- Included files: {count}", f"- Top-level directory: `{PACKAGE_NAME}/`",
            "- Excluded: Git/CI, tests, tools, caches, development environments, logs, ZIP/MP4 media",
            "- Checks: required files, JSON parsing, local absolute paths, high-confidence secrets, archive layout",
            "",
        )),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        files = candidates()
        verify_sources(files)
        with tempfile.TemporaryDirectory(prefix="skinbeauty-release-") as directory:
            archive, _, _ = write_archive(Path(directory))
            verify_archive(archive)
        print(f"release sources verified: {len(files)} file(s)")
        return
    archive, digest, count = write_archive(args.output_dir)
    write_metadata(args.output_dir, archive, digest, count)
    print(f"wrote {archive} ({count} files, sha256 {digest})")


if __name__ == "__main__":
    main()
