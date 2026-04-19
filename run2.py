import sys
f = open('output_phase1.txt', 'w', encoding='utf-8')
sys.stdout = f
sys.stderr = f
try:
    with open('test_phase1.py', 'r', encoding='utf-8') as src:
        exec(src.read(), {"__name__": "__main__"})
except BaseException as e:
    import traceback
    traceback.print_exc()
finally:
    f.close()
