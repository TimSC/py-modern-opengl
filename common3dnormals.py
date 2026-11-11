#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py
#and tips from http://www.opengl-tutorial.org/intermediate-tutorials/tutorial-13-normal-mapping

import OpenGL.GL as gl
from OpenGL.GL.shaders import compileShader, compileProgram
import os
import numpy as np
import math, time
import transutils
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

strVS = """
#version 330 core
in vec3 aVert;
in vec3 aVertNormal;
in vec4 aColor;
in vec3 aTangent;
in vec3 aBitangent;
in vec2 aUV;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
out vec4 vCol;
out vec3 fragNormal;
out vec3 fragWorld;
out vec3 tangent;
out vec3 bitangent;
out vec2 uv;
void main() {
  // set position
  vec4 fragWorldTmp = uMVMatrix * vec4(aVert, 1.0); 
  gl_Position = uPMatrix * fragWorldTmp;
  fragWorld = vec3(fragWorldTmp);
  vCol = aColor;
  fragNormal = aVertNormal;
  tangent = aTangent;
  bitangent = aBitangent;
  uv = aUV;
}
"""
strFS = """
#version 330 core
in vec4 vCol;
in vec3 fragNormal;
in vec3 fragWorld;
in vec3 tangent;
in vec3 bitangent;
in vec2 uv;
uniform mat4 uMVMatrix;
uniform vec3 lightPos;
uniform sampler2D uTexture;
out vec4 fragColor;

void main() {
    //calculate normal and tangents in world coordinates
    mat3 normalMatrix = transpose(inverse(mat3(uMVMatrix)));
    vec3 normal_world = normalize(normalMatrix * fragNormal);
    vec3 tangent_world = normalize(normalMatrix * tangent);
    vec3 bitangent_world = normalize(normalMatrix * bitangent);

	vec3 bumpRGB = texture(uTexture, uv).rgb;
	vec3 bumpScaled = bumpRGB * 2. - 1;
	vec3 bumpNormal = bumpScaled[0] * tangent_world +
		bumpScaled[1] * bitangent_world +
		bumpScaled[2] * normal_world;
	
    //calculate the vector from this pixels surface to the light source
    vec3 surfaceToLight = lightPos - fragWorld;

	//calculate the cosine of the angle of incidence
    float brightness = dot(bumpNormal, surfaceToLight) / (length(surfaceToLight) * length(bumpNormal));
    brightness = clamp(brightness, 0, 1);

    // use vertex color
    fragColor = vCol * brightness;
}
"""

def loadtexture(filename):
	#Create texture
	texIndex = gl.glGenTextures(1)
	gl.glBindTexture(gl.GL_TEXTURE_2D, texIndex)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
	gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
	img = Image.open(os.path.join(HERE, filename)) # .jpg, .bmp, etc. also work
	img_data = np.array(list(img.getdata()), np.uint8)
	gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, img.size[0], img.size[1], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_data)
	gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
	return texIndex

def normalize(vec):
	mag=np.linalg.norm(vec)
	if mag>0.: 
		return vec/mag
	return vec

def calcTangentsTri(verts, normals, uvs):
	deltaPos1 = verts[1]-verts[0];
	deltaPos2 = verts[2]-verts[0];
	deltaUV1 = uvs[1]-uvs[0];
	deltaUV2 = uvs[2]-uvs[0];
	normal = normals.mean(axis=0)
	
	r = 1.0 / (deltaUV1[0] * deltaUV2[1] - deltaUV1[1] * deltaUV2[0])
	tangent = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1])*r
	bitangent = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0])*r
	tangent = normalize(tangent - normal * np.dot(normal, tangent)) #orthogonalize

	#Check for right handed system
	if np.dot(np.cross(normal, tangent), bitangent) < 0.:
		tangent *= -1.

	return list(tangent), list(bitangent)

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
	#textureUniform = gl.glGetUniformLocation(program, "uTexture")

	# attributes
	vertIndex = gl.glGetAttribLocation(program, "aVert")
	colorIndex = gl.glGetAttribLocation(program, "aColor")
	normalIndex = gl.glGetAttribLocation(program, "aVertNormal")
	tangentIndex = gl.glGetAttribLocation(program, "aTangent")
	bitangentIndex = gl.glGetAttribLocation(program, "aBitangent")
	uvIndex = gl.glGetAttribLocation(program, "aUV")

	# define quad vertices
	s = 0.9
	quadV = np.array([
			#Front
			 [- s, s, -s,],
			 [- s, -s, -s,],
			 [s, s, -s,],
			 [s, s, -s,],
			 [- s, -s, -s,],
			 [s, -s, -s,],
			#Back
			 [-s, s, s,],
			 [- s, -s, s,],
			 [s, s, s,],
			 [s, s, s,],
			 [- s, -s, s,],
			 [s, -s, s,],
			#Left
			 [s, - s, s,],
			 [s, - s, -s,],
			 [s, s, s,],
			 [s, s, s,],
			 [s, - s, -s,],
			 [s, s, -s,],
			#Right
			 [-s, - s, s, ],
			 [-s, - s, -s, ],
			 [-s, s, s, ],
			 [-s, s, s, ],
			 [-s, - s, -s, ],
			 [-s, s, -s, ],
			#Top
			 [- s, -s, s,],
			 [- s, -s, -s,],
			 [s, -s, s,],
			 [s, -s, s,],
			 [- s, -s, -s,],
			 [s, -s, -s,],
			#Bottom
			 [- s, s, s,],
			 [- s, s, -s,],
			 [s, s, s,],
			 [s, s, s,],
			 [- s, s, -s,],
			 [s, s, -s,],
			 ])

	vertexBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32).reshape(quadV.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, gl.GL_STATIC_DRAW)

	# define normals
	s = 1.
	quadN = np.array([
			#Front
			 [0, 0, -s,],
			 [0, 0, -s,],
			 [0, 0, -s,],
			 [0, 0, -s,],
			 [0, 0, -s,],
			 [0, 0, -s,],
			#Back
			 [0, 0, s,],
			 [0, 0, s,],
			 [0, 0, s,],
			 [0, 0, s,],
			 [0, 0, s,],
			 [0, 0, s,],
			#Left
			 [s, 0, 0,],
			 [s, 0, 0,],
			 [s, 0, 0,],
			 [s, 0, 0,],
			 [s, 0, 0,],
			 [s, 0, 0,],
			#Right
			 [-s, 0, 0,],
			 [-s, 0, 0,],
			 [-s, 0, 0,], 
			 [-s, 0, 0,], 
			 [-s, 0, 0,], 
			 [-s, 0, 0,],
			#Top
			 [0, -s, 0,],
			 [0, -s, 0,],
			 [0, -s, 0,],
			 [0, -s, 0,],
			 [0, -s, 0,],
			 [0, -s, 0,],
			#Bottom
			 [0, s, 0,],
			 [0, s, 0,],
			 [0, s, 0,],
			 [0, s, 0,],
			 [0, s, 0,],
			 [0, s, 0,]
			 ])

	normalBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, normalBuffer)
	normalData = np.array(quadN, np.float32).reshape(quadN.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(normalData), normalData, gl.GL_STATIC_DRAW)

	# define vertex colours

	vcol = np.array([
			 [1.0, 0.0, 0.0, 1.0,],
			 [1.0, 0.0, 0.0, 1.0,],
			 [1.0, 0.0, 0.0, 1.0,],
			 [1.0, 0.0, 0.0, 1.0,],
			 [1.0, 0.0, 0.0, 1.0,],
			 [1.0, 0.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 1.0, 0.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 0.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [0.0, 1.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 0.0, 1.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 [1.0, 1.0, 0.0, 1.0,],
			 ])

	colBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	colData = np.array(vcol, np.float32).reshape(vcol.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(colData), colData, gl.GL_STATIC_DRAW)

	#UV texture data

	quadUV = np.array([
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 ])

	uvBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, uvBuffer)
	uvData = np.array(quadUV, np.float32).reshape(quadUV.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(uvData), uvData, gl.GL_STATIC_DRAW)

	#Load textures and maps
	normalTexIndex = loadtexture("brick-normalmap.jpg")

	#Compute tangents
	tangents, bitangents = [], []
	for triIndex in range(0, len(quadV), 3):
		faceVerts = quadV[triIndex:triIndex+3, :]
		faceNormals = quadN[triIndex:triIndex+3, :]
		faceUVs = quadUV[triIndex:triIndex+3, :]
		tangent, bitangent = calcTangentsTri(faceVerts, faceNormals, faceUVs)
		tangents.extend([tangent, tangent, tangent])
		bitangents.extend([bitangent, bitangent, bitangent])
	tangents = np.array(tangents)
	bitangents = np.array(bitangents)

	tangentsBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, tangentsBuffer)
	tangentData = np.array(tangents, np.float32).reshape(tangents.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(tangentData), tangentData, gl.GL_STATIC_DRAW)

	bitangentsBuffer = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, bitangentsBuffer)
	bitangentsData = np.array(bitangents, np.float32).reshape(bitangents.size)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, 4 * len(bitangentsData), bitangentsData, gl.GL_STATIC_DRAW)

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
	out['uvIndex'] = uvIndex
	out['uvBuffer'] = uvBuffer
	out['normalTexIndex'] = normalTexIndex
	out['tangentIndex'] = tangentIndex
	out['bitangentIndex'] = bitangentIndex
	out['tangentsBuffer'] = tangentsBuffer
	out['bitangentsBuffer'] = bitangentsBuffer
	
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
	uvIndex = params['uvIndex']
	uvBuffer = params['uvBuffer']
	normalTexIndex = params['normalTexIndex']
	tangentIndex = params['tangentIndex']
	bitangentIndex = params['bitangentIndex']
	tangentsBuffer = params['tangentsBuffer']
	bitangentsBuffer = params['bitangentsBuffer']

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

	#enable normal map
	gl.glActiveTexture(gl.GL_TEXTURE0);
	gl.glBindTexture(gl.GL_TEXTURE_2D, normalTexIndex)

	#enable arrays
	gl.glEnableVertexAttribArray(vertIndex)
	gl.glEnableVertexAttribArray(colorIndex)
	gl.glEnableVertexAttribArray(normalIndex)
	gl.glEnableVertexAttribArray(tangentIndex)
	gl.glEnableVertexAttribArray(bitangentIndex)
	gl.glEnableVertexAttribArray(uvIndex)
	
	# set buffers
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertexBuffer)	
	gl.glVertexAttribPointer(vertIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, colBuffer)
	gl.glVertexAttribPointer(colorIndex, 4, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, normalBuffer)
	gl.glVertexAttribPointer(normalIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, tangentsBuffer)
	gl.glVertexAttribPointer(tangentIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, bitangentsBuffer)
	gl.glVertexAttribPointer(bitangentIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, uvBuffer)
	gl.glVertexAttribPointer(uvIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, 0, None)

	# draw
	gl.glDrawArrays(gl.GL_TRIANGLES, 0, 36)

	# disable arrays
	gl.glDisableVertexAttribArray(vertIndex)
	gl.glDisableVertexAttribArray(colorIndex)
	gl.glDisableVertexAttribArray(normalIndex)

	gl.glDisableVertexAttribArray(tangentIndex)
	gl.glDisableVertexAttribArray(bitangentIndex)
	gl.glDisableVertexAttribArray(uvIndex)

