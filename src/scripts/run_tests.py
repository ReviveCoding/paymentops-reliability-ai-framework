from __future__ import annotations

import importlib.util
import inspect
import traceback
import tempfile
from pathlib import Path


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def main() -> int:
    test_dir = Path("tests")
    total = 0
    failed = 0
    for path in sorted(test_dir.glob("test_*.py")):
        module = _load_module(path)
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                sig = inspect.signature(fn)
                kwargs = {}
                if "tmp_path" in sig.parameters:
                    with tempfile.TemporaryDirectory() as td:
                        kwargs["tmp_path"] = Path(td)
                        fn(**kwargs)
                else:
                    fn()
                print(f"PASS {path.name}::{name}")
            except Exception:
                failed += 1
                print(f"FAIL {path.name}::{name}")
                traceback.print_exc()
    print(f"{total - failed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
