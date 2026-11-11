#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL.GL as gl
from OpenGL.GL.shaders import compileShader, compileProgram
import numpy as np
import math

# GLSL 3.30 core: "in"/"out" instead of attribute/varying, and a declared
# fragment output instead of gl_FragColor (all removed in core profiles)
strVS = """
#version 330 core
in vec3 aVert;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
in vec4 aColor;
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
	versionString = gl.glGetString(gl.GL_VERSION).split(b" ")
	openglVersionString = versionString[0]
	openglVersionNums = list(map(int, openglVersionString.split(b".")))
	if openglVersionNums[0] < 3 or (openglVersionNums[0] == 3 and openglVersionNums[1] < 3):
		exit("Requires opengl 3.3 or better, you have {0}".format(openglVersionString))

	out = {}
	# A core profile draws nothing unless a vertex array object (VAO) is bound,
	# and compileProgram (which validates the program) fails without one, so
	# make it first. It records the attribute setup done in draw().
	vao = gl.glGenVertexArrays(1)
	gl.glBindVertexArray(vao)

	# create shader
	vs = compileShader(strVS, gl.GL_VERTEX_SHADER)
	fs = compileShader(strFS, gl.GL_FRAGMENT_SHADER)
	program = compileProgram(vs, fs)
	gl.glUseProgram(program)

	pMatrixUniform = gl.glGetUniformLocation(program, 'uPMatrix')
	mvMatrixUniform = gl.glGetUniformLocation(program, "uMVMatrix")

	# attributes
	vertIndex = gl.glGetAttribLocation(program, "aVert")
	colorIndex = gl.glGetAttribLocation(program, "aColor")

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
	vertexBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, gl.GL_STATIC_DRAW)

	# define vertex colours

	vcol = [
			 0.5, 0.0, 0.0, 1.0,
			 0.0, 0.5, 0.0, 1.0,
			 0.0, 0.0, 0.5, 1.0,
			 1.0, 0.0, 0.0, 1.0,
			 0.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 1.0, 1.0
			 ]

	colBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	colData = np.array(vcol, np.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(colData), colData, gl.GL_STATIC_DRAW)

	out = {'program': program, 
		'pMatrixUniform': pMatrixUniform, 
		'mvMatrixUniform': mvMatrixUniform, 
		'colorIndex': colorIndex, 
		'vertIndex': vertIndex, 
		'col0': col0, 
		'vertexBuffer': vertexBuffer,
		'colBuffer': colBuffer}
	out['vao'] = vao
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

	gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
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
	gl.glUseProgram(program)
	gl.glBindVertexArray(params['vao'])

	# set proj matrix
	gl.glUniformMatrix4fv(pMatrixUniform, 1, gl.GL_FALSE, pMatrix)

	# set modelview matrix
	gl.glUniformMatrix4fv(mvMatrixUniform, 1, gl.GL_FALSE, mvMatrix)

	#enable arrays
	gl.glEnableVertexAttribArray(vertIndex)
	gl.glEnableVertexAttribArray(colorIndex)
	
	# set buffers
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)	
	gl.glVertexAttribPointer(vertIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	gl.glVertexAttribPointer(colorIndex, 4, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

	# draw
	gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

	# disable arrays
	gl.glDisableVertexAttribArray(vertIndex)
	gl.glDisableVertexAttribArray(colorIndex)

