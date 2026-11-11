#Runs every example in self-check mode (see selfcheck.py) and reports which
#ones pass: no GL error and a frame that isn't blank.
#
#usage: check_examples.py [--frames N] [--out DIR] [--timeout S]
#  --frames N   frame to check in each example (default 5)
#  --out DIR    save each checked frame there as <example>.png
#  --timeout S  give up on an example after S seconds (default 30)
#
#Each example runs in its own process, started from another directory, so a
#crash, a hang or a file loaded relative to the current directory shows up as a
#failure of that example only. Examples whose window toolkit isn't installed
#are skipped. The exit status is 0 if nothing failed.

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# (runner, module it needs)
EXAMPLES = [
	("glut_example2d.py", "OpenGL.GLUT"),
	("glut_example3d.py", "OpenGL.GLUT"),
	("glut_example3dtex.py", "OpenGL.GLUT"),
	("glut_example3dlighting.py", "OpenGL.GLUT"),
	("glut_example3dnormals.py", "OpenGL.GLUT"),
	("glut_example3dtexnorms.py", "OpenGL.GLUT"),
	("glut_example3dadvanced.py", "OpenGL.GLUT"),
	("glfw_example2d.py", "glfw"),
	("glfw_example3d.py", "glfw"),
	("pygame_example3dadvanced.py", "pygame"),
]

def arg(name, default):
	return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def main():
	frames = int(arg("--frames", "5"))
	out = arg("--out", None)
	timeout = float(arg("--timeout", "30"))
	if out:
		os.makedirs(out, exist_ok=True)
		out = os.path.abspath(out)

	results = []
	with tempfile.TemporaryDirectory() as cwd:
		for runner, needs in EXAMPLES:
			if importlib.util.find_spec(needs.split(".")[0]) is None:
				results.append((runner, "SKIP", "{} is not installed".format(needs)))
				continue
			cmd = [sys.executable, os.path.join(HERE, runner), "--frames", str(frames)]
			if out:
				cmd += ["--shot", os.path.join(out, runner.replace(".py", ".png"))]
			try:
				p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
			except subprocess.TimeoutExpired:
				results.append((runner, "FAIL", "no result after {:.0f}s".format(timeout)))
				continue
			lines = [l for l in p.stdout.splitlines() if "PASS" in l or "FAIL" in l]
			if p.returncode == 0 and lines:
				results.append((runner, "PASS", lines[-1].split(": ", 1)[1]))
			else:
				why = lines[-1].split(": ", 1)[1] if lines else (p.stderr.strip().splitlines() or ["exit status {}".format(p.returncode)])[-1]
				results.append((runner, "FAIL", why))

	width = max(len(r[0]) for r in results)
	for runner, verdict, why in results:
		print("{}  {}  {}".format(runner.ljust(width), verdict, why))
	failed = sum(1 for r in results if r[1] == "FAIL")
	print("{} passed, {} failed, {} skipped".format(
		sum(1 for r in results if r[1] == "PASS"), failed, sum(1 for r in results if r[1] == "SKIP")))
	sys.exit(1 if failed else 0)

if __name__ == "__main__":
	main()
