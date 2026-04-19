import subprocess
with open('phase2_clean_log.txt', 'w', encoding='utf-8') as f:
    subprocess.run(['.\\venv\\Scripts\\python.exe', 'test_phase2.py'], stdout=f, stderr=f)
