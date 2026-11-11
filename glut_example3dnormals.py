#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut
import selfcheck
import common3dnormals, time
lastDrawTime = 0.

aspect = 1.
params = None
width, height = None, None

check = selfcheck.SelfCheck()

def draw():
	common3dnormals.draw(params, aspect)
	# --frames N [--shot FILE]: check the Nth frame and exit (see selfcheck.py)
	if check.frame():
		glut.glutLeaveMainLoop() # not sys.exit(): see main()
		return
	glut.glutSwapBuffers()
	if check.active:
		glut.glutPostRedisplay() # keep drawing until the check has run

def main():
	# the shaders are GLSL 3.30, so ask for a 3.3 core profile (otherwise
	# freeglut makes a compatibility context, which accepts things a core one
	# rejects); double buffered for glutSwapBuffers, with a depth buffer
	glut.glutInitContextVersion(3, 3)
	glut.glutInitContextProfile(glut.GLUT_CORE_PROFILE)
	glut.glutInitDisplayMode(glut.GLUT_RGBA | glut.GLUT_DOUBLE | glut.GLUT_DEPTH)
	glut.glutInitWindowSize(640, 480)
	window = glut.glutCreateWindow("Hello world!")
	glut.glutReshapeFunc(reshape)
	glut.glutDisplayFunc(draw)
	glut.glutIdleFunc(idle)
	glut.glutKeyboardFunc(keyPressed)  # Checks for key strokes
	global params
	params = common3dnormals.init()
	# GLUT calls back into python through ctypes, and ctypes prints and then
	# ignores any exception raised in a callback, SystemExit included: sys.exit()
	# in draw() or keyPressed() would leave the program running. So the callbacks
	# call glutLeaveMainLoop, glutMainLoop returns, and the exit happens here.
	glut.glutSetOption(glut.GLUT_ACTION_ON_WINDOW_CLOSE, glut.GLUT_ACTION_GLUTMAINLOOP_RETURNS)
	glut.glutMainLoop()
	sys.exit(check.status or 0)

def reshape(widthIn, heightIn):
	global width, height
	width = widthIn
	height = heightIn
	global aspect
	aspect = (width / float(height))
	gl.glViewport(0, 0, width, height)
	gl.glEnable(gl.GL_DEPTH_TEST)
	gl.glDisable(gl.GL_CULL_FACE)
	gl.glClearColor(0.8, 0.8, 0.8, 1.0)
	glut.glutPostRedisplay()

def idle():
	global lastDrawTime
	now = time.time()
	elapse = now - lastDrawTime
	if elapse > 0.05:
		glut.glutPostRedisplay()
		lastDrawTime = now

def keyPressed(*args):
	glut.glutLeaveMainLoop()

if __name__=="__main__":
	glut.glutInit(sys.argv)
	main()


