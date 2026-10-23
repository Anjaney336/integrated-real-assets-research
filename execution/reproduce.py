from pathlib import Path
import subprocess,sys
root=Path(__file__).parent
for args in [['-m','unittest','discover','-v'],['run.py'],['experiments.py']]:
    subprocess.run([sys.executable,*args],cwd=root,check=True)
