#Based on https://github.com/Habitats/uni/blob/master/img_processing/project/graphics_modern2.py

import OpenGL
from OpenGL.GL import *
import OpenGL.GL as gl
from OpenGL.GL.shaders import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import numpy as np
import math, sys, time
import vrml.vrml97.transformmatrix as tr
from PIL import Image

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
	vec3 bumpNormal = bumpScaled[1] * tangent_world +
		bumpScaled[0] * bitangent_world +
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
	texIndex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texIndex)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	img = Image.open(filename) # .jpg, .bmp, etc. also work
	img_data = np.array(list(img.getdata()), np.uint8)
 	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.size[0], img.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
	glBindTexture(GL_TEXTURE_2D, 0)
	return texIndex

def calcTangentsTri(verts, normals, uvs):
	deltaPos1 = verts[1]-verts[0];
	deltaPos2 = verts[2]-verts[0];
	deltaUV1 = uvs[1]-uvs[0];
	deltaUV2 = uvs[2]-uvs[0];
	normal = normals.mean(axis=0)
	
	r = 1.0 / (deltaUV1[0] * deltaUV2[1] - deltaUV1[1] * deltaUV2[0])
	tangent = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1])*r
	bitangent = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0])*r

	return list(tangent), list(bitangent)

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
	#textureUniform = glGetUniformLocation(program, "uTexture")

	# attributes
	vertIndex = glGetAttribLocation(program, "aVert")
	colorIndex = glGetAttribLocation(program, "aColor")
	normalIndex = glGetAttribLocation(program, "aVertNormal")
	tangentIndex = glGetAttribLocation(program, "aTangent")
	bitangentIndex = glGetAttribLocation(program, "aBitangent")
	uvIndex = glGetAttribLocation(program, "aUV")

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

	vertexBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)
	vertexData = np.array(quadV, np.float32).reshape(quadV.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(vertexData), vertexData, GL_STATIC_DRAW)

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

	normalBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, normalBuffer)
	normalData = np.array(quadN, np.float32).reshape(quadN.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(normalData), normalData, GL_STATIC_DRAW)

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

	colBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, colBuffer)
	colData = np.array(vcol, np.float32).reshape(vcol.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(colData), colData, GL_STATIC_DRAW)

	#UV texture data

	quadUV = np.array([
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 [0., 0.,],[0., 1.,],[1., 0.,],[1., 0.,],[0., 1.,],[1., 1.],
			 ])

	uvBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, uvBuffer)
	uvData = np.array(quadUV, np.float32).reshape(quadUV.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(uvData), uvData, GL_STATIC_DRAW)

	#Load textures and maps
	normalTexIndex = loadtexture("normalmap.jpg")

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

	tangentsBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, tangentsBuffer)
	tangentData = np.array(tangents, np.float32).reshape(tangents.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(tangentData), tangentData, GL_STATIC_DRAW)

	bitangentsBuffer = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, bitangentsBuffer)
	bitangentsData = np.array(bitangents, np.float32).reshape(bitangents.size)
	glBufferData(GL_ARRAY_BUFFER, 4 * len(bitangentsData), bitangentsData, GL_STATIC_DRAW)

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
	mvRotate1 = tr.rotMatrix([1., 0., 0., time.clock()])[0]
	mvMatrix = np.dot(mvRotate1, mvMatrix)
	mvRotate2 = tr.rotMatrix([0., 1., 0., time.clock()/5.])[0]
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

	#enable normal map
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, normalTexIndex)

	#enable arrays
	glEnableVertexAttribArray(vertIndex)
	glEnableVertexAttribArray(colorIndex)
	glEnableVertexAttribArray(normalIndex)
	glEnableVertexAttribArray(tangentIndex)
	glEnableVertexAttribArray(bitangentIndex)
	glEnableVertexAttribArray(uvIndex)
	
	# set buffers
	glBindBuffer(GL_ARRAY_BUFFER, vertexBuffer)	
	glVertexAttribPointer(vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, colBuffer)
	glVertexAttribPointer(colorIndex, 4, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, normalBuffer)
	glVertexAttribPointer(normalIndex, 3, GL_FLOAT, GL_FALSE, 0, None)

	glBindBuffer(GL_ARRAY_BUFFER, tangentsBuffer)
	glVertexAttribPointer(tangentIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, bitangentsBuffer)
	glVertexAttribPointer(bitangentIndex, 3, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, uvBuffer)
	glVertexAttribPointer(uvIndex, 2, GL_FLOAT, GL_FALSE, 0, None)

	# draw
	glDrawArrays(GL_TRIANGLES, 0, 36)

	# disable arrays
	glDisableVertexAttribArray(vertIndex)
	glDisableVertexAttribArray(colorIndex)
	glDisableVertexAttribArray(normalIndex)

	glDisableVertexAttribArray(tangentIndex)
	glDisableVertexAttribArray(bitangentIndex)
	glDisableVertexAttribArray(uvIndex)

