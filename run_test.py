import sys
import traceback

with open("python_test_output.log", "w", encoding="utf-8") as f:
    sys.stdout = f
    sys.stderr = f
    try:
        with open("test_phase1.py", "r", encoding="utf-8") as src:
            code = src.read()
        exec(code, {"__name__": "__main__"})
    except Exception:
        traceback.print_exc()
