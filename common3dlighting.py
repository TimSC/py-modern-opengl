#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy as np
import math, sys, time
import transutils

strVS = """
#version 330 core
in vec3 aVert;
in vec3 aVertNormal;
in vec4 aColor;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
out vec4 vCol;
out vec3 fragNormal;
out vec3 fragWorld;
void main() {
  // set position
  vec4 fragWorldTmp = uMVMatrix * vec4(aVert, 1.0); 
  gl_Position = uPMatrix * fragWorldTmp;
  fragWorld = vec3(fragWorldTmp);
  vCol = aColor;
  fragNormal = aVertNormal;
}
"""
strFS = """
#version 330 core
in vec4 vCol;
in vec3 fragNormal;
in vec3 fragWorld;
out vec4 fragColor;
uniform mat4 uMVMatrix;
uniform vec3 lightPos;

void main() {
    //calculate normal in world coordinates
    mat3 normalMatrix = transpose(inverse(mat3(uMVMatrix)));
    vec3 normal = normalize(normalMatrix * fragNormal);

    //calculate the vector from this pixels surface to the light source
    vec3 surfaceToLight = lightPos - fragWorld;

	//calculate the cosine of the angle of incidence
    float brightness = dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal));
    brightness = clamp(brightness, 0, 1);

    // use vertex color
    fragColor = vCol * brightness;
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
	lightPosUniform = glGetUniformLocation(program, 'lightPos')

	# attributes
	vertIndex = glGetAttribLocation(program, "aVert")
	colorIndex = glGetAttribLocation(program, "aColor")
	normalIndex = glGetAttribLocation(program, "aVertNormal")

	# define quad vertices
	s = 0.9
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
			#Left
			 s, - s, s,
			 s, - s, -s,
			 s, s, s,
			 s, s, s,
			 s, - s, -s,
			 s, s, -s,
			#Right
			 -s, - s, s, 
			 -s, - s, -s, 
			 -s, s, s, 
			 -s, s, s, 
			 -s, - s, -s, 
			 -s, s, -s, 
			#Top
			- s, -s, s,
			 - s, -s, -s,
			 s, -s, s,
			 s, -s, s,
			 - s, -s, -s,
			 s, -s, -s,
			#Bottom
			- s, s, s,
			 - s, s, -s,
			 s, s, s,
			 s, s, s,
			 - s, s, -s,
			 s, s, -s,
			 ]

	vertexBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

	# define normals
	s = 1.
	quadN = [
			#Front
			 0, 0, -s,
			 0, 0, -s,
			 0, 0, -s,
			 0, 0, -s,
			 0, 0, -s,
			 0, 0, -s,
			#Back
			 0, 0, s,
			 0, 0, s,
			 0, 0, s,
			 0, 0, s,
			 0, 0, s,
			 0, 0, s,
			#Left
			 s, 0, 0,
			 s, 0, 0,
			 s, 0, 0,
			 s, 0, 0,
			 s, 0, 0,
			 s, 0, 0,
			#Right
			 -s, 0, 0,
			 -s, 0, 0, 
			 -s, 0, 0, 
			 -s, 0, 0, 
			 -s, 0, 0, 
			 -s, 0, 0,  
			#Top
			 0, -s, 0,
			 0, -s, 0,
			 0, -s, 0,
			 0, -s, 0,
			 0, -s, 0,
			 0, -s, 0,
			#Bottom
			 0, s, 0,
			 0, s, 0,
			 0, s, 0,
			 0, s, 0,
			 0, s, 0,
			 0, s, 0,
			 ]

	normalBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, normalBuffer)
	normalData = np.array(quadN, np.float32)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(normalData), normalData, GL_STATIC_DRAW)

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
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 0.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 0.0, 1.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 0.0, 1.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
			 1.0, 1.0, 0.0, 1.0,
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
		'vertexBuffer': vertexBuffer,
		'colBuffer': colBuffer}
	out['lightPosUniform'] = lightPosUniform
	out['normalIndex'] = normalIndex
	out['normalBuffer'] = normalBuffer
	return out

def draw(params, aspect):
	program = params['program']
	pMatrixUniform = params['pMatrixUniform']
	mvMatrixUniform = params['mvMatrixUniform']
	colorIndex = params['colorIndex']
	vertIndex = params['vertIndex']
	vertexBuffer = params['vertexBuffer']
	colBuffer = params['colBuffer']
	lightPosUniform = params['lightPosUniform']
	normalIndex = params['normalIndex']
	normalBuffer = params['normalBuffer']

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glEnable(GL_DEPTH_TEST)

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
							[0.0, 0.0, 0.0, 1.0]])
	test = time.clock()
	numPi = int(test / math.pi)

	mvMatrix = identityMvMatrix
	mvRotate1 = transutils.rotMatrix(time.clock()*20., 1., 0., 0., )
	mvMatrix = np.dot(mvRotate1, mvMatrix)
	mvRotate2 = transutils.rotMatrix(time.clock()*5., 0., 1., 0.)
	mvMatrix = np.dot(mvRotate2, mvMatrix)
	mvMatrix[3,2] = -5. #Translate
	mvMatrix = np.array(mvMatrix.reshape((16,)), np.float32)

	# use shader
	glUseProgram(program)

	# set proj matrix
	glUniformMatrix4fv(pMatrixUniform, 1, GL_FALSE, pMatrix)

	# set modelview matrix
	glUniformMatrix4fv(mvMatrixUniform, 1, GL_FALSE, mvMatrix)

	# set lighting
	glUniform3fv(lightPosUniform, 1, np.array([2., 2., 0.], np.float32))

	#enable arrays
	glEnableVertexAttribArray(vertIndex)
	glEnableVertexAttribArray(colorIndex)
	glEnableVertexAttribArray(normalIndex)
	
	# set buffers
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)	
	glVertexAttribPointer(vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, colBuffer)
	glVertexAttribPointer(colorIndex, 4, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, normalBuffer)
	glVertexAttribPointer(normalIndex, 3, GL_FLOAT, GL_FALSE, 0, None)

	# draw
	glDrawArrays(GL_TRIANGLES, 0, 36)

	# disable arrays
	glDisableVertexAttribArray(vertIndex)
	glDisableVertexAttribArray(colorIndex)

