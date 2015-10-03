#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

from OpenGL.GLUT import *
from OpenGL.GLUT.freeglut import *
import common3d
import OpenGL.GL as gl

def main():
	glutInitDisplayMode(GLUT_RGBA)
	glutInitWindowSize(640, 480)
	window = glutCreateWindow("Minimal")
	glutReshapeFunc(reshape)
	glutDisplayFunc(common3d.draw)
	glutKeyboardFunc(keyPressed)  # Checks for key strokes
	common3d.init()
	glutMainLoop()

def reshape(widthIn, heightIn):
	global width, height
	width = widthIn
	height = heightIn
	common3d.set_aspect(width / float(height))
	gl.glViewport(0, 0, width, height)
	gl.glEnable(GL_DEPTH_TEST)
	gl.glDisable(GL_CULL_FACE)
	gl.glClearColor(0.8, 0.8, 0.8, 1.0)
	glutPostRedisplay()

def keyPressed(*args):
	sys.exit()

if __name__=="__main__":
	glutInit(sys.argv)
	main()

