import subprocess
import sys

steps = ["inputUser.py", "hardFilter.py", "embedded.py", "showResult.py"]

for step in steps:
	result = subprocess.run([sys.executable, step])

	if result.returncode != 0:
		print("")
		print("The step " + step + " failed, so the pipeline stopped here.")
		break