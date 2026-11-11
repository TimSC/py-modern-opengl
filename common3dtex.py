#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL.GL as gl
from OpenGL.GL.shaders import compileShader, compileProgram
import os
import numpy, math
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

strVS = """
#version 330 core
in vec3 aVert; // "attribute" is not allowed in a core profile
in vec2 aUV;
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
	textureUniform = gl.glGetUniformLocation(program, "uTexture")

	# define vertices
	vertIndex = gl.glGetAttribLocation(program, "aVert")
	s = 0.9
	quadV = [
			 - s, s, 0.0, 
			 - s, -s, 0.0, 			
			 s, s, 0.0, 
			 s, s, 0.0, 
			 - s, -s, 0.0, 
			 s, -s, 0.0, 
			 ]

	vertexBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = numpy.array(quadV, numpy.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, gl.GL_STATIC_DRAW)

	# define UV
	uvIndex = gl.glGetAttribLocation(program, "aUV")
	quadUV = [
			 0., 0.,
			 0., 1.,
			 1., 0.,
			 1., 0.,
			 0., 1.,
			 1., 1.
			 ]

	uvBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, uvBuffer)
	uvData = numpy.array(quadUV, numpy.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(uvData), uvData, gl.GL_STATIC_DRAW)

	#Create texture
	texIndex = gl.glGenTextures(1)
	gl.glBindTexture(gl.GL_TEXTURE_2D, texIndex)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
	img = Image.open(os.path.join(HERE, "butterfly.JPG")) # .jpg, .bmp, etc. also work
	img_data = numpy.array(list(img.getdata()), numpy.uint8)
	gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, img.size[0], img.size[1], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_data)
	gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

	out = {'program': program, 
		'pMatrixUniform': pMatrixUniform, 
		'mvMatrixUniform': mvMatrixUniform, 
		'textureUniform': textureUniform,
		'vertIndex': vertIndex, 
		'uvIndex': uvIndex, 
		'vertexBuffer': vertexBuffer,
		'uvBuffer': uvBuffer,
		'texIndex': texIndex}
	out['vao'] = vao
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

	gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
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
	gl.glUseProgram(program)
	gl.glBindVertexArray(params['vao'])

	# set proj matrix
	gl.glUniformMatrix4fv(pMatrixUniform, 1, gl.GL_FALSE, pMatrix)

	# set modelview matrix
	gl.glUniformMatrix4fv(mvMatrixUniform, 1, gl.GL_FALSE, mvMatrix)

	#enable arrays
	gl.glEnableVertexAttribArray(vertIndex)
	gl.glEnableVertexAttribArray(uvIndex)

	#enable texture
	gl.glActiveTexture(gl.GL_TEXTURE0);
	gl.glBindTexture(gl.GL_TEXTURE_2D, texIndex)

	# set buffers
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)
	gl.glVertexAttribPointer(vertIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, uvBuffer)
	gl.glVertexAttribPointer(uvIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

	# draw
	gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

	# disable arrays
	gl.glDisableVertexAttribArray(vertIndex)
	gl.glDisableVertexAttribArray(uvIndex)

