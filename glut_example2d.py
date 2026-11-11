#! /usr/bin/env python
# -*- coding: utf-8 -*-
import common2d, sys
import OpenGL.GLUT as glut
import selfcheck
import OpenGL.GL as gl

_myProg = None

check = selfcheck.SelfCheck()

def displayFunc():
	global _myProg
	common2d.display(_myProg)
	# --frames N [--shot FILE]: check the Nth frame and exit (see selfcheck.py)
	if check.frame():
		glut.glutLeaveMainLoop() # not sys.exit(): see the glutMainLoop call
		return
	glut.glutSwapBuffers()
	if check.active:
		glut.glutPostRedisplay() # keep drawing until the check has run

def set_global_program(program):
	global _myProg
	_myProg = program

def reshape(width,height):
	gl.glViewport(0, 0, width, height)

def keyboard( key, x, y ):
	if key == b'\033': # GLUT passes the key as bytes
		glut.glutLeaveMainLoop()

if __name__=="__main__":
	# GLUT init
	# --------------------------------------
	glut.glutInit()
	# the shaders are GLSL 3.30, so ask for a 3.3 core profile
	glut.glutInitContextVersion(3, 3)
	glut.glutInitContextProfile(glut.GLUT_CORE_PROFILE)
	glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGBA)
	glut.glutCreateWindow('Hello world!')
	glut.glutReshapeWindow(640,480)
	glut.glutReshapeFunc(reshape)
	glut.glutDisplayFunc(displayFunc)
	glut.glutKeyboardFunc(keyboard)

	program = common2d.init_shader_program()
	set_global_program(program)

	# Make program the default program
	gl.glUseProgram(program)

	# Enter mainloop
	# --------------------------------------
	# GLUT calls back into python through ctypes, and ctypes prints and then
	# ignores any exception raised in a callback, SystemExit included: sys.exit()
	# in draw() or keyPressed() would leave the program running. So the callbacks
	# call glutLeaveMainLoop, glutMainLoop returns, and the exit happens here.
	glut.glutSetOption(glut.GLUT_ACTION_ON_WINDOW_CLOSE, glut.GLUT_ACTION_GLUTMAINLOOP_RETURNS)
	glut.glutMainLoop()
	sys.exit(check.status or 0)

