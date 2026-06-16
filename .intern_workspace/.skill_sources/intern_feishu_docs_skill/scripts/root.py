"""Locate WORK_AGENTS_ROOT the same way intern-cli does.

Precedence:
1. env WORK_AGENTS_ROOT  (what the VS Code plugin also exports)
2. walk up from CWD looking for a directory that contains BOTH `key.txt`
   and `.feishu_registry/` — the two markers intern-cli's `setup` writes.
"""

import os


def find_work_agents_root():
    env = os.environ.get("WORK_AGENTS_ROOT")
    if env:
        return os.path.abspath(env)
    path = os.path.abspath(os.getcwd())
    while True:
        if (
            os.path.isfile(os.path.join(path, "key.txt"))
            and os.path.isdir(os.path.join(path, ".feishu_registry"))
        ):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    raise RuntimeError(
        "Cannot locate WORK_AGENTS_ROOT. Set env WORK_AGENTS_ROOT, or run this "
        "skill from inside your intern-agents workspace (the directory that "
        "contains key.txt and .feishu_registry/)."
    )


if __name__ == "__main__":
    print(f"WORK_AGENTS_ROOT = {find_work_agents_root()}")
