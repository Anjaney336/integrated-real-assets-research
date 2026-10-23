from pathlib import Path
import subprocess,sys,os
os.chdir(Path(__file__).parent)
subprocess.run([sys.executable,'-m','unittest','-v'],check=True)
subprocess.run([sys.executable,'-m','unittest','discover','-s','execution','-v'],check=True)
subprocess.run([sys.executable,'-m','pytest','-q'],cwd='signals',check=True)
subprocess.run([sys.executable,'integrated.py'],check=True)
subprocess.run([sys.executable,'execution/robustness.py'],check=True)
subprocess.run([sys.executable,'fundamentals.py'],check=True)
subprocess.run([sys.executable,'embassy_case/verify_case.py'],check=True)
subprocess.run([sys.executable,'wealth_policy.py'],check=True)
