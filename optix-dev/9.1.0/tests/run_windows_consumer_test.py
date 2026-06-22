import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time


def _make_writable_and_retry(func, path, _exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _remove_tree_with_retry(path):
    path = pathlib.Path(path)
    if not path.exists():
        return

    delay = 0.25
    last_error = None
    for _attempt in range(8):
        try:
            shutil.rmtree(path, onerror=_make_writable_and_retry)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(delay)
            delay = min(delay * 2, 2.0)

    raise SystemExit(f"failed to remove {path}: {last_error}")


def _require_within(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise SystemExit(f"refusing to remove {path}; it is outside {parent}") from exc


def main():
    if sys.platform != "win32":
        raise SystemExit("run_windows_consumer_test.py is only intended for Windows tests")

    prefix = pathlib.Path(os.environ["PREFIX"])
    library_prefix = pathlib.Path(os.environ.get("LIBRARY_PREFIX", prefix / "Library"))
    temp_root = pathlib.Path(tempfile.gettempdir())
    build_dir = pathlib.Path(tempfile.mkdtemp(prefix="optix-dev-cmake-", dir=temp_root))
    optix_root = library_prefix / "opt" / "optix-dev-9.1.0"

    _require_within(build_dir, temp_root)
    _require_within(optix_root, library_prefix / "opt")

    test_error = None
    try:
        subprocess.run(
            [
                "cmake",
                "-S",
                "tests",
                "-B",
                str(build_dir),
                "-GNinja",
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_PREFIX_PATH={library_prefix}",
            ],
            check=True,
        )
        subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release"], check=True)
        subprocess.run([str(build_dir / "optix_consumer.exe")], check=True)
    except subprocess.CalledProcessError as exc:
        test_error = exc
    finally:
        cleanup_errors = []
        for cleanup_path in (build_dir, optix_root):
            try:
                _remove_tree_with_retry(cleanup_path)
            except SystemExit as exc:
                cleanup_errors.append(str(exc))

        if test_error is not None:
            if cleanup_errors:
                print("cleanup failed after consumer test failure:", file=sys.stderr)
                for cleanup_error in cleanup_errors:
                    print(f"  {cleanup_error}", file=sys.stderr)
            raise test_error

        if cleanup_errors:
            raise SystemExit("\n".join(cleanup_errors))


if __name__ == "__main__":
    main()
