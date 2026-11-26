import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import atlas


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True).stdout


class ParseTests(unittest.TestCase):
    def test_nul_separated_paths_and_binary(self):
        record = (b"\0PATCHBAY\0" + b"a" * 40 + b"\0" + b"0\0PATCHBAY\0\0"
                  b"\n7\t2\tsrc/tab\tand\nnewline.py\0-\t-\tassets/image.png\0")
        entry, = atlas.parse_log(record)
        self.assertEqual(entry["subject"], "")
        self.assertEqual(entry["author"], "PATCHBAY")
        self.assertEqual(entry["files"], [["src/tab\tand\nnewline.py", 7, 2],
                                          ["assets/image.png", None, None]])

    def test_script_terminator_is_json_escaped(self):
        hostile = "</script><img src=x onerror=alert(1)> & \u2028"
        report = atlas.render({"repo": hostile, "ref": "main", "commits": []})
        self.assertNotIn(hostile, report)
        payload = re.search(r'id="atlas-data">(.*?)</script>', report).group(1)
        self.assertEqual(json.loads(payload)["repo"], hostile)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "ample space"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "A. Person")
        git(self.repo, "config", "user.email", "person@example.invalid")
        git(self.repo, "config", "commit.gpgsign", "false")
        git(self.repo, "config", "core.autocrlf", "false")

    def commit(self, subject, path=None, contents=b"text\n"):
        if path:
            file = self.repo / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(contents)
            git(self.repo, "add", "--", path)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", subject)

    def test_unborn_empty_and_detached_head(self):
        data = atlas.read_repo(self.repo, 4)
        self.assertEqual((data["repo"], data["ref"], data["commits"]),
                         ("ample space", "main", []))
        self.commit("No files")
        git(self.repo, "checkout", "-q", "--detach")
        data = atlas.read_repo(self.repo, 4)
        self.assertEqual(data["ref"], data["commits"][0]["id"][:8])
        self.assertEqual(data["commits"][0]["files"], [])

    def test_subdirectory_limit_unicode_and_binary(self):
        self.commit("First entry", "README.md")
        self.commit("Signal", "音频/a.bin", b"\x00\x01\x02")
        data = atlas.read_repo(self.repo / "音频", 1)
        self.assertEqual(data["repo"], "ample space")
        self.assertEqual(len(data["commits"]), 1)
        self.assertEqual(data["commits"][0]["files"], [["音频/a.bin", None, None]])

    def test_merge_uses_its_first_parent_delta(self):
        self.commit("Start here", "readme")
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.commit("Feature work", "lib/module.py")
        git(self.repo, "checkout", "-q", "main")
        self.commit("Trunk work", "docs/intro.md")
        git(self.repo, "merge", "-q", "--no-ff", "feature", "-m", "Merge feature")
        changes = atlas.read_repo(self.repo, 10)["commits"]
        self.assertEqual([c["subject"] for c in changes],
                         ["Merge feature", "Trunk work", "Start here"])
        self.assertEqual(changes[0]["files"], [["lib/module.py", 1, 0]])

    def test_output_requires_explicit_overwrite(self):
        report = self.repo / "out.html"
        atlas.write_report(report, "first", False)
        with self.assertRaises(FileExistsError):
            atlas.write_report(report, "second", False)
        self.assertEqual(report.read_text(encoding="utf-8"), "first")
        atlas.write_report(report, "second", True)
        self.assertEqual(report.read_text(encoding="utf-8"), "second")

    def test_bare_repository(self):
        self.commit("One", "root")
        clone = self.repo.parent / "archive.git"
        git(self.repo, "clone", "-q", "--bare", ".", str(clone))
        self.assertEqual(atlas.read_repo(clone, 1)["commits"][0]["subject"], "One")


if __name__ == "__main__":
    unittest.main()
