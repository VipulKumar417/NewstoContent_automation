import sys
class Flusher:
    def __init__(self, f):
        self.f = f
    def write(self, text):
        self.f.write(text)
        self.f.flush()
    def __getattr__(self, attr):
        return getattr(self.f, attr)

f = open('output_phase1.txt', 'w', encoding='utf-8')
sys.stdout = Flusher(f)

print("Starting import...", flush=True)
import test_phase1
print("Execution finished.", flush=True)
