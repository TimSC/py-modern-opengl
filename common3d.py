#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

from __future__ import print_function
import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy as np
import math, sys

strVS = """
attribute vec3 aVert;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
attribute vec4 aColor;
varying vec4 vCol;
void main() {
  // set position
  gl_Position = uPMatrix * uMVMatrix * vec4(aVert, 1.0); 
  // set color
  vCol = aColor;
}
"""
strFS = """
varying vec4 vCol;
void main() {
  // use vertex color
  gl_FragColor = vCol;
}
"""

# initialization
def init():
	versionString = gl.glGetString(gl.GL_VERSION).split(b" ")
	openglVersionString = versionString[0]
	openglVersionNums = list(map(int, openglVersionString.split(b".")))
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
	s = 0.2
	quadV = [
			- s, s, 0.0,
			 - s, -s, 0.0,
			 s, s, 0.0,
			 s, s, 0.0,
			 - s, -s, 0.0,
			 s, -s, 0.0
			 ]

	# vertices
	vertexBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

	# define vertex colours

	vcol = [
			 0.5, 0.0, 0.0, 1.0,
			 0.0, 0.5, 0.0, 1.0,
			 0.0, 0.0, 0.5, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 1.0, 1.0
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
	mvMatrix = np.array([1.0, 0.0, 0.0, 0.0,
							0.0, 1.0, 0.0, 0.0,
							0.0, 0.0, 1.0, 0.0,
							0.5, 0.0, -5.0, 1.0], np.float32)

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

