#!/usr/bin/env python3
"""Write a portable, deterministic PAX catalog archive without executable files."""
import gzip
import pathlib
import sys
import tarfile


def write_archive(stage, output):
    stage = pathlib.Path(stage)
    if stage.is_symlink() or not stage.is_dir():
        raise ValueError("Catalog stage must be a regular directory")
    paths = [stage] + sorted(stage.rglob("*"))
    for item in paths:
        if item.is_symlink() or not (item.is_dir() or item.is_file()):
            raise ValueError("Catalog archive accepts only regular files and directories")

    def normalize(info):
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        info.mode = 0o755 if info.isdir() else 0o644
        info.pax_headers = {}
        return info

    with open(output, "xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for item in paths:
                    relative = item.relative_to(stage).as_posix()
                    name = "package" if relative == "." else "package/" + relative
                    archive.add(item, arcname=name, recursive=False, filter=normalize)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: catalog_archive.py STAGE OUTPUT.tgz")
    write_archive(sys.argv[1], sys.argv[2])
