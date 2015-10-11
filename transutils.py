
#Based on the PyVRML97 module, copyright (c) 1995-2012, Michael C. Fletcher and Contributors
import math

def rotMatrix(x, y, z, a):
	"""Generate an opengl rotation matrix
	x,y,z -- rotational vector axis
	a -- angle in radians
	"""
	# normalize the rotation vector!
	squared = x*x + y*y + z*z
	if squared != 1.0:
		length = squared ** .5
		x /= squared 
		y /= squared 
		z /= squared
	c = math.cos( a )
	c1 = math.cos( -a )
	s = math.sin( a )
	s1 = math.sin( -a )
	t = 1-c
	R = [
		[ t*x*x+c, t*x*y+s*z, t*x*z-s*y, 0.],
		[ t*x*y-s*z, t*y*y+c, t*y*z+s*x, 0.],
		[ t*x*z+s*y, t*y*z-s*x, t*z*z+c, 0.],
		[ 0.,		0.,		0.,		 1.]
	]
	return R

def scaleMatrix(x, y, z):
	"""Generate scale matrix
	x,y,z -- scale vector
	"""
	S = [ [x,0.,0.,0.], [0.,y,0.,0.], [0.,0.,z,0.], [0.,0.,0.,1.] ]
	return S

def transMatrix(x, y, z):
	"""Generate translation matrix
	x,y,z -- scale vector
	"""
	T = [ [1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.], [x,y,z,1] ]
	return T

def identityMatrix():
	return [[1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.], [0.,0.,0.,1.]]

if __name__ == "__main__":
	#Check functions against opengl API
	from OpenGL.GLUT import *
	from OpenGL.GLUT.freeglut import *
	import OpenGL.GL as gl
	import numpy as np
	import math

	glutInit(sys.argv)
	glutInitDisplayMode(GLUT_RGBA)
	glutInitWindowSize(640, 480)
	window = glutCreateWindow("Hello world!")

	gl.glMatrixMode(gl.GL_MODELVIEW)
	gl.glLoadIdentity()
	mat = np.array(identityMatrix())

	for i in range(10):

		vec = list(100. * np.random.random((1,3))[0] - 50.)
		gl.glTranslated(*vec)
		correct = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)
		print "correct 1 ", correct

		trans = np.array(transMatrix(*vec))
		mat = np.dot(trans, mat)
		print "predicted 1", mat
		gl.glLoadMatrixf(list(mat.reshape(mat.size)))

		#vec = list(4. * np.random.random((1,3))[0] - 2.)
		vec = [1., 0., 0.]
		ang = 4. * math.pi * np.random.random()
		print vec, ang
		gl.glRotated(vec[0], vec[1], vec[2], ang)
		correct = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)
		print "correct 2", correct

		trans = np.array(rotMatrix(vec[0], vec[1], vec[2], math.radians(ang)))
		mat = np.dot(mat, trans)
		print "predicted 2", mat
		gl.glLoadMatrixf(list(mat.reshape(mat.size)))

