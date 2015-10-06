#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy as np
import math, sys, time, glutils

strVS = """
#version 330 core
attribute vec3 aVert;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
attribute vec4 aColor;
out vec4 vCol;
void main() {
  // set position
  gl_Position = uPMatrix * uMVMatrix * vec4(aVert, 1.0); 
  // set color
  vCol = aColor;
}
"""
strFS = """
#version 330 core
in vec4 vCol;
out vec4 fragColor;
void main() {
  // use vertex color
  fragColor = vCol;
}
"""

# initialization
def init():
	versionString = gl.glGetString(gl.GL_VERSION).split(" ")
	openglVersionString = versionString[0]
	openglVersionNums = map(int, openglVersionString.split("."))
	if openglVersionNums[0] < 3 or (openglVersionNums[0] == 3 and openglVersionNums[1] < 3):
		exit("Requires opengl 3.3 or better, you have {0}".format(openglVersionString))

	out = {}
	# create shader
	vs = compileShader(strVS, GL_VERTEX_SHADER)
	fs = compileShader(strFS, GL_FRAGMENT_SHADER)
	program = compileProgram(vs, fs)
	glUseProgram(program)

	pMatrixUniform = glGetUniformLocation(program, 'uPMatrix')
	mvMatrixUniform = glGetUniformLocation(program, "uMVMatrix")

	# attributes
	vertIndex = glGetAttribLocation(program, "aVert")
	colorIndex = glGetAttribLocation(program, "aColor")

	# color
	col0 = [1.0, 1.0, 0.0, 1.0]

	# define quad vertices
	s = 0.5
	quadV = [
			#Front
			- s, s, -s,
			 - s, -s, -s,
			 s, s, -s,
			 s, s, -s,
			 - s, -s, -s,
			 s, -s, -s,
			#Back
			- s, s, s,
			 - s, -s, s,
			 s, s, s,
			 s, s, s,
			 - s, -s, s,
			 s, -s, s,
			 ]

	# vertices
	vertexBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

	# define vertex colours

	vcol = [
			 1.0, 0.0, 0.0, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 ]

	colBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, colBuffer)
	colData = np.array(vcol, np.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(colData), colData, GL_STATIC_DRAW)

	out = {'program': program, 
		'pMatrixUniform': pMatrixUniform, 
		'mvMatrixUniform': mvMatrixUniform, 
		'colorIndex': colorIndex, 
		'vertIndex': vertIndex, 
		'col0': col0, 
		'vertexBuffer': vertexBuffer,
		'colBuffer': colBuffer}
	return out

def draw(params, aspect):
	program = params['program']
	pMatrixUniform = params['pMatrixUniform']
	mvMatrixUniform = params['mvMatrixUniform']
	colorIndex = params['colorIndex']
	vertIndex = params['vertIndex']
	col0 = params['col0']
	vertexBuffer = params['vertexBuffer']
	colBuffer = params['colBuffer']

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	# build projection matrix
	fov = math.radians(45.0)
	f = 1.0 / math.tan(fov / 2.0)
	zN, zF = (0.1, 100.0)
	a = aspect
	pMatrix = np.array([f / a, 0.0, 0.0, 0.0,
						   0.0, f, 0.0, 0.0,
						   0.0, 0.0, (zF + zN) / (zN - zF), -1.0,
						   0.0, 0.0, 2.0 * zF * zN / (zN - zF), 0.0], np.float32)

	# modelview matrix
	identityMvMatrix = np.array([[1.0, 0.0, 0.0, 0.0],
							[0.0, 1.0, 0.0, 0.0],
							[0.0, 0.0, 1.0, 0.0],
							[0.5, 0.0, -5.0, 1.0]])
	mvRotate = glutils.rotation_matrix((1., 0., 0.), time.time())
	mvMatrix = np.dot(mvRotate, identityMvMatrix)
	mvMatrix = np.array(mvMatrix.reshape((16,)), np.float32)

	# use shader
	glUseProgram(program)

	# set proj matrix
	glUniformMatrix4fv(pMatrixUniform, 1, GL_FALSE, pMatrix)

	# set modelview matrix
	glUniformMatrix4fv(mvMatrixUniform, 1, GL_FALSE, mvMatrix)

	#enable arrays
	glEnableVertexAttribArray(vertIndex)
	glEnableVertexAttribArray(colorIndex)
	
	# set buffers
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)	
	glVertexAttribPointer(vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, colBuffer)
	glVertexAttribPointer(colorIndex, 4, GL_FLOAT, GL_FALSE, 0, None)

	# draw
	glDrawArrays(GL_TRIANGLES, 0, 6)

	# disable arrays
	glDisableVertexAttribArray(vertIndex)
	glDisableVertexAttribArray(colorIndex)

