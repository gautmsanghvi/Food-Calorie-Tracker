import subprocess
import os

# Run pylint on all Python files in the current directory and subdirectories
subprocess.run(["pylint", "*.py", "*/**/*.py"], check=True)
