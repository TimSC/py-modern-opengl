#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

from OpenGL.GLUT import *
from OpenGL.GLUT.freeglut import *
import common3d
import OpenGL.GL as gl

aspect = 1.
params = None
width, height = None, None

def draw():
	common3d.draw(params, aspect)
	glutSwapBuffers()

def main():
	glutInitDisplayMode(GLUT_RGBA)
	glutInitWindowSize(640, 480)
	window = glutCreateWindow("Hello world!")
	glutReshapeFunc(reshape)
	glutDisplayFunc(draw)
	glutKeyboardFunc(keyPressed)  # Checks for key strokes
	global params
	params = common3d.init()
	glutMainLoop()

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
	glutPostRedisplay()

def keyPressed(*args):
	sys.exit()

if __name__=="__main__":
	glutInit(sys.argv)
	main()

