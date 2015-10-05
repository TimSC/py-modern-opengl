#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy, math, sys

strVS = """
attribute vec3 aVert;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
uniform vec4 uColor;
varying vec4 vCol;
void main() {
  // option #1 - fails
  gl_Position = uPMatrix * uMVMatrix * vec4(aVert, 1.0); 
  // option #2 - works
  //gl_Position = vec4(aVert, 1.0); 
  // set color
  vCol = vec4(uColor.rgb, 1.0);
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
	colorU = glGetUniformLocation(program, "uColor")

	# attributes
	vertIndex = glGetAttribLocation(program, "aVert")

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
	vertexData = numpy.array(quadV, numpy.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

	out = {'program': program, 
		'pMatrixUniform': pMatrixUniform, 
		'mvMatrixUniform': mvMatrixUniform, 
		'colorU': colorU, 
		'vertIndex': vertIndex, 
		'col0': col0, 
		'vertexBuffer': vertexBuffer}
	return out

def draw(params, aspect):
	
	program = params['program']
	pMatrixUniform = params['pMatrixUniform']
	mvMatrixUniform = params['mvMatrixUniform']
	colorU = params['colorU']
	vertIndex = params['vertIndex']
	col0 = params['col0']
	vertexBuffer = params['vertexBuffer']

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	# build projection matrix
	fov = math.radians(45.0)
	f = 1.0 / math.tan(fov / 2.0)
	zN, zF = (0.1, 100.0)
	a = aspect
	pMatrix = numpy.array([f / a, 0.0, 0.0, 0.0,
						   0.0, f, 0.0, 0.0,
						   0.0, 0.0, (zF + zN) / (zN - zF), -1.0,
						   0.0, 0.0, 2.0 * zF * zN / (zN - zF), 0.0], numpy.float32)

	# modelview matrix
	mvMatrix = numpy.array([1.0, 0.0, 0.0, 0.0,
							0.0, 1.0, 0.0, 0.0,
							0.0, 0.0, 1.0, 0.0,
							0.5, 0.0, -5.0, 1.0], numpy.float32)

	# use shader
	glUseProgram(program)

	# set proj matrix
	glUniformMatrix4fv(pMatrixUniform, 1, GL_FALSE, pMatrix)

	# set modelview matrix
	glUniformMatrix4fv(mvMatrixUniform, 1, GL_FALSE, mvMatrix)

	# set color
	glUniform4fv(colorU, 1, col0)

	#enable arrays
	glEnableVertexAttribArray(vertIndex)

	# set buffers
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	glVertexAttribPointer(vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)

	# draw
	glDrawArrays(GL_TRIANGLES, 0, 6)

	# disable arrays
	glDisableVertexAttribArray(vertIndex)


