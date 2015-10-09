#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy, math, sys
from PIL import Image

strVS = """
#version 330 core
attribute vec3 aVert;
attribute vec2 aUV;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
out vec2 UV;
void main() {
  gl_Position = uPMatrix * uMVMatrix * vec4(aVert, 1.0);
  UV = aUV;
}
"""
strFS = """
#version 330 core
in vec2 UV;
uniform sampler2D uTexture;
out vec3 color;
void main() {
  color = texture(uTexture, UV).rgb;;
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
	textureUniform = glGetUniformLocation(program, "uTexture")

	# define vertices
	vertIndex = glGetAttribLocation(program, "aVert")
	s = 0.9
	quadV = [
			 - s, s, 0.0, 
			 - s, -s, 0.0, 			
			 s, s, 0.0, 
			 s, s, 0.0, 
			 - s, -s, 0.0, 
			 s, -s, 0.0, 
			 ]

	vertexBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = numpy.array(quadV, numpy.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

	# define UV
	uvIndex = glGetAttribLocation(program, "aUV")
	quadUV = [
			 0., 0.,
			 0., 1.,
			 1., 0.,
			 1., 0.,
			 0., 1.,
			 1., 1.
			 ]

	uvBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, uvBuffer)
	uvData = numpy.array(quadUV, numpy.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(uvData), uvData, GL_STATIC_DRAW)

	#Create texture
	texIndex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texIndex)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	img = Image.open("butterfly.JPG") # .jpg, .bmp, etc. also work
	img_data = numpy.array(list(img.getdata()), numpy.uint8)
 	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.size[0], img.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
	glBindTexture(GL_TEXTURE_2D, 0)

	out = {'program': program, 
		'pMatrixUniform': pMatrixUniform, 
		'mvMatrixUniform': mvMatrixUniform, 
		'textureUniform': textureUniform,
		'vertIndex': vertIndex, 
		'uvIndex': uvIndex, 
		'vertexBuffer': vertexBuffer,
		'uvBuffer': uvBuffer,
		'texIndex': texIndex}
	return out

def draw(params, aspect):
	
	program = params['program']
	pMatrixUniform = params['pMatrixUniform']
	mvMatrixUniform = params['mvMatrixUniform']
	textureUniform = params['textureUniform']
	vertIndex = params['vertIndex']
	uvIndex = params['uvIndex']
	vertexBuffer = params['vertexBuffer']
	uvBuffer = params['uvBuffer']
	texIndex = params['texIndex']

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

	#enable arrays
	glEnableVertexAttribArray(vertIndex)
	glEnableVertexAttribArray(uvIndex)

	#enable texture
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, texIndex)

	# set buffers
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	glVertexAttribPointer(vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, uvBuffer)
	glVertexAttribPointer(uvIndex, 2, GL_FLOAT, GL_FALSE, 0, None)

	# draw
	glDrawArrays(GL_TRIANGLES, 0, 6)

	# disable arrays
	glDisableVertexAttribArray(vertIndex)
	glDisableVertexAttribArray(uvIndex)

