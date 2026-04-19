import sys

f = open('trace.log', 'w', encoding='utf-8')
def trace_calls(frame, event, arg):
    if event == 'line':
        f.write(f"{frame.f_code.co_filename}:{frame.f_lineno}\n")
        f.flush()
    return trace_calls

sys.settrace(trace_calls)

try:
    with open('test_phase1.py', 'r', encoding='utf-8') as src:
        exec(src.read(), {"__name__": "__main__"})
except Exception as e:
    f.write(f"EXCEPTION: {e}\n")
finally:
    f.close()
