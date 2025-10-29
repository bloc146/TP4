import os
import sys
import subprocess


def run(cmd: str, check: bool = False) -> int:
    print(f"+ {cmd}", flush=True)
    proc = subprocess.run(cmd, shell=True)
    if check and proc.returncode != 0:
        print(f"Command failed with code {proc.returncode}: {cmd}", file=sys.stderr)
        sys.exit(proc.returncode)
    return proc.returncode


def output(cmd: str) -> str:
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(f"Command failed with code {proc.returncode}: {cmd}", file=sys.stderr)
        sys.exit(proc.returncode)
    return proc.stdout.strip()


def main() -> int:
    # Ensure full history (checkout step already uses fetch-depth: 0, but this is safe)
    run("git fetch --all --tags --prune")

    bad = os.environ.get("BAD_HASH") or output("git rev-parse HEAD")
    # Use the root/initial commit as a reasonable GOOD commit (assignment states it used to work)
    roots = output("git rev-list --max-parents=0 HEAD").splitlines()
    good = os.environ.get("GOOD_HASH") or (roots[0] if roots else None)

    if not good or not bad:
        print("GOOD_HASH or BAD_HASH could not be determined.", file=sys.stderr)
        return 2

    print(f"Using good={good} and bad={bad}")

    # The command that determines if a commit is good (exit 0) or bad (exit non-zero)
    test_cmd = os.environ.get("BISECT_TEST_CMD", "python manage.py test -q")

    # Start bisect session
    if run(f"git bisect start {bad} {good}") != 0:
        print("git bisect start failed", file=sys.stderr)
        return 3

    try:
        rc = run(f"git bisect run {test_cmd}")
        # Capture the first bad commit (HEAD points to it after a successful bisect)
        try:
            bad_commit = output("git rev-parse HEAD")
            bad_line = output("git log -1 --oneline")
            print(f"First bad commit: {bad_commit}")
            print(f"First bad commit (oneline): {bad_line}")
        except SystemExit:
            pass
        # Show bisect log to capture the path bisect took
        run("git bisect log")
        return 0 if rc == 0 else 1
    finally:
        # Always cleanup the bisect state
        run("git bisect reset")


if __name__ == "__main__":
    sys.exit(main())
