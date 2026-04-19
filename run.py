import sys
f = open("log.txt", "w", encoding="utf-8")
sys.stdout = f
sys.stderr = f
try:
    with open("test_phase1.py", "r", encoding="utf-8") as file:
        exec(file.read(), {"__name__": "__main__"})
except Exception:
    import traceback
    traceback.print_exc()
finally:
    f.close()
