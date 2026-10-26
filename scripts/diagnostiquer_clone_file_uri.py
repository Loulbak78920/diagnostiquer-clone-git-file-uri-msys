#!/usr/bin/env python3
"""Diagnose a local git clone failure caused by exported MSYS path variables.

Builds a disposable bare origin under ~/.qoder/tmp, seeds one commit, then
clones it with file:///C:/... and file://C:/... under four environment
conditions: inherit, MSYS_NO_PATHCONV=1, MSYS2_ARG_CONV_EXCL='*', both.

The verdict uses only the three-slash matrix observed in the source session.
Two-slash cells are observations, never assertions.

Exit codes: 0 REPRODUCED, 1 PARTIAL/NOT_REPRODUCED, 2 usage/environment.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.home()
TMP_ROOT = HOME / ".qoder" / "tmp"
FIXTURE_PREFIX = "diag-clone-file-uri-"
GIT_TIMEOUT = 120
MSYS_KEYS = ("MSYS_NO_PATHCONV", "MSYS2_ARG_CONV_EXCL")
CONDITIONS = ("inherit", "no_pathconv", "arg_excl", "both")
FORMS = ("three", "two")
CONFIG_KEYS = ("core.autocrlf", "user.name", "user.email")
FAILED_TOKEN = "does not appear to be a git repository"


class Failure(Exception):
    pass


def ascii_text(value: object) -> str:
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError):
            pass


def emit(message: str = "") -> None:
    print(ascii_text(message), flush=True)


def base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def env_for(condition: str) -> dict[str, str]:
    if condition == "inherit":
        return base_env()
    env = base_env()
    for key in MSYS_KEYS:
        env.pop(key, None)
    if condition == "no_pathconv":
        env["MSYS_NO_PATHCONV"] = "1"
    elif condition == "arg_excl":
        env["MSYS2_ARG_CONV_EXCL"] = "*"
    elif condition == "both":
        env["MSYS_NO_PATHCONV"] = "1"
        env["MSYS2_ARG_CONV_EXCL"] = "*"
    else:
        raise Failure(f"unknown condition: {condition}")
    return env


def run(
    cmd: list[str], env: dict[str, str], cwd: Path | None = None
) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
            env=env,
            cwd=str(cwd) if cwd is not None else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Failure(f"cannot run {cmd[0]}: {exc}") from None
    output = "\n".join(
        part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip()
    )
    return proc.returncode, output.strip()


def git(repo: Path, *args: str) -> str:
    code, output = run(["git", "-C", str(repo), *args], base_env())
    if code != 0:
        label = args[0] if args else ""
        raise Failure(f"git {label} rc={code}: {ascii_text(output)}")
    return output.strip()


def url_for(origin: Path, form: str) -> str:
    if form == "three":
        return origin.as_uri()
    return "file://" + origin.resolve().as_posix()


def fatal_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.lower().startswith("fatal:") or FAILED_TOKEN in line:
            return line
    return lines[-1] if lines else ""


def setup_fixture(root: Path) -> Path:
    origin = root / "origin.git"
    work = root / "work"

    git(root, "init", "--bare", "--initial-branch=main", str(origin))
    git(root, "init", "--initial-branch=main", str(work))
    for key, value in (
        ("user.name", "MSYS File URI Test"),
        ("user.email", "msys-file-uri@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
    ):
        git(work, "config", key, value)

    (work / "base.txt").write_bytes(b"base\n")
    git(work, "add", "base.txt")
    git(work, "commit", "-m", "seed")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-u", "origin", "main")
    return origin


def clone_cell(root: Path, origin: Path, form: str, condition: str) -> dict:
    url = url_for(origin, form)
    dst = root / "cells" / f"{form}-{condition}"
    code, output = run(["git", "clone", "--quiet", url, str(dst)], env_for(condition))
    cell = {
        "form": form,
        "condition": condition,
        "url": url,
        "rc": code,
        "fatal": fatal_line(output),
        "clone": dst.exists(),
        "branch": "",
        "status": "",
        "remote": "",
        "local_config": [],
        "anomalies": [],
    }
    if code == 0 and dst.exists():
        cell["branch"] = git(dst, "rev-parse", "--abbrev-ref", "HEAD")
        cell["status"] = git(dst, "status", "--porcelain=v1")
        cell["remote"] = git(dst, "remote", "get-url", "origin")
        for key in CONFIG_KEYS:
            key_code, _ = run(
                ["git", "-C", str(dst), "config", "--local", "--get", key],
                base_env(),
            )
            if key_code == 0:
                cell["local_config"].append(key)
        if cell["branch"] != "main":
            cell["anomalies"].append(f"branch={cell['branch']}")
        if cell["status"]:
            cell["anomalies"].append("status not clean")
        if not cell["remote"]:
            cell["anomalies"].append("remote empty")
        if cell["local_config"]:
            cell["anomalies"].append(
                "local config: " + ",".join(cell["local_config"])
            )
        if not (dst / "base.txt").is_file():
            cell["anomalies"].append("base.txt missing")
    return cell


def print_cell(cell: dict) -> None:
    prefix = "CELL" if cell["form"] == "three" else "OBSERVE"
    head = (
        f"{prefix} form={cell['form']} env={cell['condition']} "
        f"rc={cell['rc']} clone={'yes' if cell['clone'] else 'no'}"
    )
    if cell["rc"] == 0 and cell["clone"]:
        status = "clean" if not cell["status"] else "dirty"
        local = (
            "absent"
            if not cell["local_config"]
            else "present:" + ",".join(cell["local_config"])
        )
        emit(
            f"{head} branch={cell['branch']} status={status} "
            f"remote={cell['remote']} local_config={local}"
        )
    else:
        emit(f"{head} fatal={cell['fatal']}")
    for anomaly in cell["anomalies"]:
        emit(
            f"  anomaly form={cell['form']} env={cell['condition']}: {anomaly}"
        )


def evaluate(cells: list[dict]) -> tuple[str, list[str]]:
    three = {cell["condition"]: cell for cell in cells if cell["form"] == "three"}
    witness = three.get("inherit")
    if witness is None:
        return "NOT_REPRODUCED", ["three-slash inherit cell missing"]
    if witness["rc"] != 0:
        return "NOT_REPRODUCED", [
            f"inherit rc={witness['rc']} (expected 0): {witness['fatal']}"
        ]

    reasons: list[str] = []
    if witness["anomalies"]:
        reasons.append("inherit anomalies: " + "; ".join(witness["anomalies"]))

    matched = 0
    for condition in ("no_pathconv", "arg_excl", "both"):
        cell = three.get(condition)
        if cell is None:
            reasons.append(f"{condition} missing")
            continue
        if (
            cell["rc"] == 128
            and "/C:/" in cell["fatal"]
            and FAILED_TOKEN in cell["fatal"]
        ):
            matched += 1
        else:
            reasons.append(
                f"{condition} rc={cell['rc']} fatal={cell['fatal']}"
            )

    if matched == 3 and not reasons:
        return "REPRODUCED", []
    if matched == 0 and not witness["anomalies"]:
        return "NOT_REPRODUCED", reasons
    return "PARTIAL", reasons


def cleanup(root: Path, keep: bool) -> bool:
    if keep:
        emit(f"KEEP fixture root: {root}")
        return True
    if not root.exists():
        emit("CLEANUP root and clones absent")
        return True
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        except OSError:
            pass
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    shutil.rmtree(root, ignore_errors=True)
    if root.exists():
        emit(f"CLEANUP FAIL root still exists: {root}")
        return False
    emit("CLEANUP root and clones absent")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose a local git clone failure under exported MSYS variables."
        )
    )
    parser.add_argument(
        "--url-forms",
        choices=("both", "three"),
        default="both",
        help="URL forms to measure (default: both)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the fixture for inspection instead of deleting it",
    )
    args = parser.parse_args(argv)

    configure_stdout()
    emit("Skill: diagnostiquer-clone-git-file-uri-msys")
    emit(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    parent = {key: os.environ.get(key, "unset") for key in MSYS_KEYS}
    emit("Parent: " + " | ".join(f"{key}={value}" for key, value in parent.items()))
    if any(value != "unset" for value in parent.values()):
        emit(
            "ERROR parent exports MSYS variables; unset MSYS_NO_PATHCONV and "
            "MSYS2_ARG_CONV_EXCL for this session, then rerun."
        )
        return 2

    code = 2
    root: Path | None = None
    try:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix=FIXTURE_PREFIX, dir=str(TMP_ROOT)))
        emit(f"Fixture root: {root}")

        version_code, version = run(["git", "--version"], base_env())
        if version_code != 0:
            raise Failure(f"git --version rc={version_code}: {ascii_text(version)}")
        emit(f"Git: {version}")

        origin = setup_fixture(root)
        emit(f"Origin: {origin}")
        emit(f"URL three: {url_for(origin, 'three')}")
        if args.url_forms == "both":
            emit(f"URL two:   {url_for(origin, 'two')}")

        forms = FORMS if args.url_forms == "both" else ("three",)
        cells: list[dict] = []
        for form in forms:
            for condition in CONDITIONS:
                cell = clone_cell(root, origin, form, condition)
                cells.append(cell)
                print_cell(cell)

        verdict, reasons = evaluate(cells)
        for reason in reasons:
            emit(f"  why {reason}")
        emit(f"RESULT {verdict} msys_file_uri_clone")
        code = 0 if verdict == "REPRODUCED" else 1
    except Failure as exc:
        emit(f"ERROR {ascii_text(exc)}")
        code = 2
    except Exception as exc:  # noqa: BLE001
        emit(f"ERROR unexpected {type(exc).__name__}: {ascii_text(exc)}")
        code = 2
    finally:
        if root is not None:
            if not cleanup(root, args.keep):
                code = 2
    return code


if __name__ == "__main__":
    sys.exit(main())
