#!/usr/bin/env python3
"""Turn a local Git repository into a self-contained, offline HTML atlas."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


TEMPLATE = Path(__file__).with_name("atlas.template.html")
DATA_SLOT = "<!-- PATCHBAY_DATA -->"


def git(repo, *arguments, check=True):
    return subprocess.run(
        ["git", "-c", "log.showSignature=false", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check,
    )


def display_text(value):
    return value.decode("utf-8", errors="backslashreplace")


def parse_log(output):
    """Git terminates fields with NUL. Paths may contain tabs and newlines."""
    fields = iter(output.split(b"\0"))
    commits = []
    for field in fields:
        if not field:
            continue
        if field == b"PATCHBAY":
            oid, timestamp, author, subject = (next(fields) for _ in range(4))
            commits.append({
                "id": oid.decode("ascii"), "time": int(timestamp),
                "author": display_text(author), "subject": display_text(subject),
                "files": [],
            })
            continue
        added, removed, path = field.lstrip(b"\n").split(b"\t", 2)
        commits[-1]["files"].append([
            display_text(path),
            None if added == b"-" else int(added),
            None if removed == b"-" else int(removed),
        ])
    return commits


def read_repo(repo, limit):
    root = git(repo, "rev-parse", "--show-toplevel", check=False)
    if root.returncode:
        root = git(repo, "rev-parse", "--absolute-git-dir")
    project = Path(os.fsdecode(root.stdout.rstrip(b"\r\n"))).name
    branch = git(repo, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    head = git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False)
    branch_name = display_text(branch.stdout.rstrip(b"\r\n")) or (
        display_text(head.stdout[:8]) if head.returncode == 0 else "unborn HEAD"
    )
    commits = []
    if head.returncode == 0:
        output = git(
            repo, "log", "--first-parent", "--diff-merges=first-parent",
            "--no-ext-diff", "--no-textconv", "--no-renames", "--no-notes",
            "--no-color", "--no-decorate", "--encoding=UTF-8", "-z", "--numstat",
            "--format=%x00PATCHBAY%x00%H%x00%ct%x00%an%x00%s",
            "--max-count=" + str(limit), "HEAD", "--",
        ).stdout
        commits = parse_log(output)
    return {"repo": project, "ref": branch_name, "demo": False, "commits": commits}


def load_template():
    if __package__:
        from importlib import resources
        return resources.files(__package__).joinpath(TEMPLATE.name).read_text(encoding="utf-8")
    return TEMPLATE.read_text(encoding="utf-8")


def render(data):
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    # Prevent embedded repository text from closing the HTML script element.
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = load_template()
    if template.count(DATA_SLOT) != 1:
        raise ValueError("The atlas template is missing its data slot.")
    return template.replace(DATA_SLOT, encoded)


def write_report(path, html, force):
    if not force:
        with path.open("x", encoding="utf-8", newline="\n") as report:
            report.write(html)
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w",
                                     encoding="utf-8", newline="\n") as report:
        staged = Path(report.name)
        try:
            report.write(html)
        except BaseException:
            report.close()
            staged.unlink()
            raise
    try:
        os.replace(staged, path)
    finally:
        if staged.exists():
            staged.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, nargs="?", default=Path("."),
                        help="Git repository or a directory inside it (default: current directory)")
    parser.add_argument("-o", "--output", type=Path, default=Path("atlas.html"),
                        help="output file (default: atlas.html)")
    parser.add_argument("-n", "--limit", type=int, default=250,
                        help="maximum first-parent commits to include (default: 250)")
    parser.add_argument("-f", "--force", action="store_true", help="replace an existing output file")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be a positive integer")
    try:
        data = read_repo(args.repository, args.limit)
        write_report(args.output, render(data), args.force)
    except FileExistsError:
        parser.exit(1, f"{args.output} already exists. Choose a new path or pass --force.\n")
    except subprocess.CalledProcessError as error:
        parser.exit(1, display_text(error.stderr).strip() + "\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Patchbay Atlas: {error}\n")
    count = len(data["commits"])
    print(f"Wrote {args.output} ({count} {'commit' if count == 1 else 'commits'}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
