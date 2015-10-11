
import math

def identityMatrix():
	return [[1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.], [0.,0.,0.,1.]]

def zeroMatrix():
	return [[0.,0.,0.,0.], [0.,0.,0.,0.], [0.,0.,0.,0.], [0.,0.,0.,0.]]

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

def rotMatrix(x, y, z, angDeg):

	#Based on https://github.com/freedreno/mesa/blob/383558c56427b0e8b4e56cce8737771ad053f753/src/mesa/math/m_matrix.c
	M = identityMatrix()
	s = math.sin(math.radians(angDeg))
	c = math.cos(math.radians(angDeg))
	mag = math.sqrt(x * x + y * y + z * z)

	if mag <= 1.0e-4:
		# no rotation, leave mat as-is
		return M

	x /= mag
	y /= mag
	z /= mag

	#
	# Arbitrary axis rotation matrix.
	#
	# This is composed of 5 matrices, Rz, Ry, T, Ry', Rz', multiplied
	# like so:  Rz * Ry * T * Ry' * Rz'.  T is the final rotation
	# (which is about the X-axis), and the two composite transforms
	# Ry' * Rz' and Rz * Ry are (respectively) the rotations necessary
	# from the arbitrary axis to the X-axis then back.  They are
	# all elementary rotations.
	#
	# Rz' is a rotation about the Z-axis, to bring the axis vector
	# into the x-z plane.  Then Ry' is applied, rotating about the
	# Y-axis to bring the axis vector parallel with the X-axis.  The
	# rotation about the X-axis is then performed.  Ry and Rz are
	# simply the respective inverse transforms to bring the arbitrary
	# axis back to its original orientation.  The first transforms
	# Rz' and Ry' are considered inverses, since the data from the
	# arbitrary axis gives you info on how to get to it, not how
	# to get away from it, and an inverse must be applied.
	#
	# The basic calculation used is to recognize that the arbitrary
	# axis vector (x, y, z), since it is of unit length, actually
	# represents the sines and cosines of the angles to rotate the
	# X-axis to the same orientation, with theta being the angle about
	# Z and phi the angle about Y (in the order described above)
	# as follows:
	#
	# cos ( theta ) = x / sqrt ( 1 - z^2 )
	# sin ( theta ) = y / sqrt ( 1 - z^2 )
	#
	# cos ( phi ) = sqrt ( 1 - z^2 )
	# sin ( phi ) = z
	#
	# Note that cos ( phi ) can further be inserted to the above
	# formulas:
	#
	# cos ( theta ) = x / cos ( phi )
	# sin ( theta ) = y / sin ( phi )
	#
	# ...etc.  Because of those relations and the standard trigonometric
	# relations, it is pssible to reduce the transforms down to what
	# is used below.  It may be that any primary axis chosen will give the
	# same results (modulo a sign convention) using thie method.
	#
	# Particularly nice is to notice that all divisions that might
	# have caused trouble when parallel to certain planes or
	# axis go away with care paid to reducing the expressions.
	# After checking, it does perform correctly under all cases, since
	# in all the cases of division where the denominator would have
	# been zero, the numerator would have been zero as well, giving
	# the expected result.

	xx = x * x
	yy = y * y
	zz = z * z
	xy = x * y
	yz = y * z
	zx = z * x
	xs = x * s
	ys = y * s
	zs = z * s
	one_c = 1.0 - c

	# We already hold the identity-matrix so we can skip some statements
	row0 = M[0]
	row0[0] = (one_c * xx) + c;
	row0[1] = (one_c * xy) - zs;
	row0[2] = (one_c * zx) + ys;
#	row0[3] = 0.0F;

	row1 = M[1]
	row1[0] = (one_c * xy) + zs;
	row1[1] = (one_c * yy) + c;
	row1[2] = (one_c * yz) - xs;
#	row1[3] = 0.0F; 

	row2 = M[2]
	row2[0] = (one_c * zx) - ys;
	row2[1] = (one_c * yz) + xs;
	row2[2] = (one_c * zz) + c;
#	row2[3] = 0.0F; 

#	row3 = M[3]
#	row3[0] = 0.0F;
#	row3[1] = 0.0F;
#	row3[2] = 0.0F;
#	row3[3] = 1.0F;

	return M


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

		vec = list(4. * np.random.random((1,3))[0] - 2.)
		ang = 4. * math.pi * np.random.random() - 2
		print vec, ang
		gl.glRotated(vec[0], vec[1], vec[2], ang)
		correct = gl.glGetFloatv(gl.GL_MODELVIEW_MATRIX)
		print "correct 2", correct

		rot = np.array(rotMatrix(vec[0], vec[1], vec[2], ang))
		mat = np.dot(rot, mat)
		print "predicted 2", mat
		gl.glLoadMatrixf(list(mat.reshape(mat.size)))

