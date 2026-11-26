"""Bundle the CLI and its template into a portable Python executable archive."""

import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp


SOURCE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="destination .pyz file")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as work:
        staging = Path(work)
        package = staging / "patchbay"
        package.mkdir()
        (package / "__init__.py").touch()
        for filename in ("atlas.py", "atlas.template.html"):
            shutil.copyfile(SOURCE / filename, package / filename)
        shutil.copyfile(SOURCE / "LICENSE", staging / "LICENSE")
        zipapp.create_archive(staging, target=args.output, main="patchbay.atlas:main",
                              interpreter="/usr/bin/env python3", compressed=True)
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
