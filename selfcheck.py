#Self-check mode for the example runners.
#
#  <runner>.py --frames N [--shot FILE.png]
#
#draws N frames, then reads the last one back (before the buffer swap, so it is
#the frame just drawn), prints the GL error state and how many different colours
#it has, saves it as FILE.png if asked, and exits: status 0 if there was no GL
#error and the frame is not blank (a single colour), 1 otherwise.
#
#Without --frames the runners behave as before. check_examples.py runs them all
#this way.
#
#Readback notes:
#  * glReadPixels returns rows bottom-up; the image is flipped to the usual
#    top-down order before saving.
#  * GL_PACK_ALIGNMENT defaults to 4, so rows of GL_RGB data are padded to a
#    multiple of 4 bytes when width*3 isn't one. It is set to 1 here.
#  * GL_BACK is read before the swap. After the swap the back buffer's
#    contents are undefined.

import os
import sys

import numpy as np
import OpenGL.GL as gl

class SelfCheck(object):

	def __init__(self, argv=None):
		argv = sys.argv if argv is None else argv
		self.frames = int(argv[argv.index("--frames") + 1]) if "--frames" in argv else None
		self.shot = argv[argv.index("--shot") + 1] if "--shot" in argv else None
		self.count = 0
		self.status = None # set when the check has run: 0 passed, 1 failed

	@property
	def active(self):
		return self.frames is not None

	def frame(self):
		# call after drawing a frame and before swapping buffers; returns True
		# when the check has run and the program should exit with self.status
		if not self.active:
			return False
		self.count += 1
		if self.count < self.frames:
			return False

		err = gl.glGetError()
		img = readback()
		colours = len(np.unique(img.reshape(-1, 3), axis=0))
		ok = err == gl.GL_NO_ERROR and colours > 1
		print("{}: frame {}, {}x{}, glGetError {}, {} colours: {}".format(
			os.path.basename(sys.argv[0]), self.count, img.shape[1], img.shape[0],
			int(err), colours, "PASS" if ok else "FAIL"))
		if self.shot:
			from PIL import Image
			Image.fromarray(img).save(self.shot)
			print("saved", self.shot)
		sys.stdout.flush()
		self.status = 0 if ok else 1
		return True

def readback():
	# the whole viewport of the current draw framebuffer, as (h, w, 3) uint8
	# with the top row first
	x, y, w, h = [int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT)]
	gl.glReadBuffer(gl.GL_BACK)
	gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
	data = gl.glReadPixels(x, y, w, h, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
	return np.ascontiguousarray(np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)[::-1])
