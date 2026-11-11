#Quake II gl3 shaders on cubes floating in space (see common3dadvanced.py), in a
#GLUT window. A key press ends it.
#
#Unlike the other glut examples this asks for an OpenGL 3.2 core profile, as q2
#does, because the shaders are "#version 150". Without glut.glutInitContextVersion
#freeglut makes a compatibility context. With Mesa that can be stuck at 3.0 or
#3.1, where "#version 150" doesn't compile. With NVIDIA it is a 4.6
#compatibility context, which runs the shaders but hides core-profile mistakes.
#glut.GLUT_DEPTH matters too: without a depth buffer the depth test does nothing.

import sys
import time

import OpenGL.GL as gl
import OpenGL.GLUT as glut
import selfcheck
import common3dadvanced

params = None
width, height = 640, 480
lastDrawTime = 0.

check = selfcheck.SelfCheck()

def draw():
	common3dadvanced.draw(params, width, height)
	# --frames N [--shot FILE]: check the Nth frame and exit (see selfcheck.py)
	if check.frame():
		glut.glutLeaveMainLoop() # not sys.exit(): see main()
		return
	glut.glutSwapBuffers()
	if check.active:
		glut.glutPostRedisplay() # keep drawing until the check has run

def main():
	glut.glutInitContextVersion(3, 2)
	glut.glutInitContextProfile(glut.GLUT_CORE_PROFILE)
	glut.glutInitDisplayMode(glut.GLUT_RGBA | glut.GLUT_DOUBLE | glut.GLUT_DEPTH)
	glut.glutInitWindowSize(width, height)
	glut.glutCreateWindow(b"Quake II gl3 shaders")
	print("GL_VERSION", gl.glGetString(gl.GL_VERSION).decode())
	glut.glutReshapeFunc(reshape)
	glut.glutDisplayFunc(draw)
	glut.glutIdleFunc(idle)
	glut.glutKeyboardFunc(keyPressed)  # Checks for key strokes
	global params
	params = common3dadvanced.init()
	# GLUT calls back into python through ctypes, and ctypes prints and then
	# ignores any exception raised in a callback, SystemExit included: sys.exit()
	# in draw() or keyPressed() would leave the program running. So the callbacks
	# call glutLeaveMainLoop, glutMainLoop returns, and the exit happens here.
	glut.glutSetOption(glut.GLUT_ACTION_ON_WINDOW_CLOSE, glut.GLUT_ACTION_GLUTMAINLOOP_RETURNS)
	glut.glutMainLoop()
	sys.exit(check.status or 0)

def reshape(widthIn, heightIn):
	# common3dadvanced sets the viewport itself each frame (SetupGL), from
	# these sizes
	global width, height
	width = widthIn
	height = max(1, heightIn)
	glut.glutPostRedisplay()

def idle():
	global lastDrawTime
	now = time.time()
	if now - lastDrawTime > 0.016:
		glut.glutPostRedisplay()
		lastDrawTime = now

def keyPressed(*args):
	glut.glutLeaveMainLoop()

if __name__=="__main__":
	glut.glutInit(sys.argv)
	main()
