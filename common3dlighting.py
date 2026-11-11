#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL.GL as gl
from OpenGL.GL.shaders import compileShader, compileProgram
import numpy as np
import math, time
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
	lightPosUniform = gl.glGetUniformLocation(program, 'lightPos')

	# attributes
	vertIndex = gl.glGetAttribLocation(program, "aVert")
	colorIndex = gl.glGetAttribLocation(program, "aColor")
	normalIndex = gl.glGetAttribLocation(program, "aVertNormal")

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

	vertexBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, gl.GL_STATIC_DRAW)

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

	normalBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, normalBuffer)
	normalData = np.array(quadN, np.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(normalData), normalData, gl.GL_STATIC_DRAW)

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

	colBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	colData = np.array(vcol, np.float32)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(colData), colData, gl.GL_STATIC_DRAW)

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
	out['vao'] = vao
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

	gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
	gl.glEnable(gl.GL_DEPTH_TEST)

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
	test = time.time()
	numPi = int(test / math.pi)

	mvMatrix = identityMvMatrix
	mvRotate1 = transutils.rotMatrix(time.time()*20., 1., 0., 0., )
	mvMatrix = np.dot(mvRotate1, mvMatrix)
	mvRotate2 = transutils.rotMatrix(time.time()*5., 0., 1., 0.)
	mvMatrix = np.dot(mvRotate2, mvMatrix)
	mvMatrix[3,2] = -5. #Translate
	mvMatrix = np.array(mvMatrix.reshape((16,)), np.float32)

	# use shader
	gl.glUseProgram(program)
	gl.glBindVertexArray(params['vao'])

	# set proj matrix
	gl.glUniformMatrix4fv(pMatrixUniform, 1, gl.GL_FALSE, pMatrix)

	# set modelview matrix
	gl.glUniformMatrix4fv(mvMatrixUniform, 1, gl.GL_FALSE, mvMatrix)

	# set lighting
	gl.glUniform3fv(lightPosUniform, 1, np.array([2., 2., 0.], np.float32))

	#enable arrays
	gl.glEnableVertexAttribArray(vertIndex)
	gl.glEnableVertexAttribArray(colorIndex)
	gl.glEnableVertexAttribArray(normalIndex)
	
	# set buffers
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)	
	gl.glVertexAttribPointer(vertIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	gl.glVertexAttribPointer(colorIndex, 4, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, normalBuffer)
	gl.glVertexAttribPointer(normalIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

	# draw
	gl.glDrawArrays(gl.GL_TRIANGLES, 0, 36)

	# disable arrays
	gl.glDisableVertexAttribArray(vertIndex)
	gl.glDisableVertexAttribArray(colorIndex)

