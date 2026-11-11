#Quake II gl3 shaders on cubes floating in space (see common3dadvanced.py), in a
#GLUT window. A key press ends it.
#
#Unlike the other glut examples this asks for an OpenGL 3.2 core profile, as q2
#does, because the shaders are "#version 150". Without glutInitContextVersion
#freeglut makes a compatibility context. With Mesa that can be stuck at 3.0 or
#3.1, where "#version 150" doesn't compile. With NVIDIA it is a 4.6
#compatibility context, which runs the shaders but hides core-profile mistakes.
#GLUT_DEPTH matters too: without a depth buffer the depth test does nothing.

import sys
import time

from OpenGL.GLUT import *
from OpenGL.GLUT.freeglut import *
import OpenGL.GL as gl
import common3dadvanced

params = None
width, height = 640, 480
lastDrawTime = 0.

def draw():
	common3dadvanced.draw(params, width, height)
	glutSwapBuffers()

def main():
	glutInitContextVersion(3, 2)
	glutInitContextProfile(GLUT_CORE_PROFILE)
	glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
	glutInitWindowSize(width, height)
	glutCreateWindow(b"Quake II gl3 shaders")
	print("GL_VERSION", gl.glGetString(gl.GL_VERSION).decode())
	glutReshapeFunc(reshape)
	glutDisplayFunc(draw)
	glutIdleFunc(idle)
	glutKeyboardFunc(keyPressed)  # Checks for key strokes
	global params
	params = common3dadvanced.init()
	glutMainLoop()

def reshape(widthIn, heightIn):
	# common3dadvanced sets the viewport itself each frame (SetupGL), from
	# these sizes
	global width, height
	width = widthIn
	height = max(1, heightIn)
	glutPostRedisplay()

def idle():
	global lastDrawTime
	now = time.time()
	if now - lastDrawTime > 0.016:
		glutPostRedisplay()
		lastDrawTime = now

def keyPressed(*args):
	sys.exit()

if __name__=="__main__":
	glutInit(sys.argv)
	main()
