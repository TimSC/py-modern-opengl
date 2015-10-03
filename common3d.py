#! /usr/bin/env python
# -*- coding: utf-8 -*-
#Based on http://www.opengl-tutorial.org/beginners-tutorials/tutorial-4-a-colored-cube/

import numpy as np
import OpenGL.GL as gl
import glm #From https://bitbucket.org/duangle/python-glm
import OpenGL.arrays.vbo as glvbo

# Vertex shader
VS = """
#version 330 core

// Input vertex data, different for all executions of this shader.
layout(location = 0) in vec3 vertexPosition_modelspace;
layout(location = 1) in vec3 vertexColor;

// Output data ; will be interpolated for each fragment.
out vec3 fragmentColor;
// Values that stay constant for the whole mesh.
uniform mat4 MVP;

void main(){	

	// Output position of the vertex, in clip space : MVP * position
	gl_Position =  MVP * vec4(vertexPosition_modelspace,1);

	// The color of each vertex will be interpolated
	// to produce the color of each fragment
	fragmentColor = vertexColor;
}
"""

# Fragment shader
FS = """
#version 330 core

// Interpolated values from the vertex shaders
in vec3 fragmentColor;

// Ouput data
out vec3 color;

void main(){

	// Output color = color specified in the vertex shader, 
	// interpolated between all 3 surrounding vertices
	color = fragmentColor;

}
"""

#Our vertices. Tree consecutive floats give a 3D vertex; Three consecutive vertices give a triangle.
#A cube has 6 faces with 2 triangles each, so this makes 6*2=12 triangles, and 12*3 vertices
g_vertex_buffer_data = [
    -1.0,-1.0,-1.0, # triangle 1 : begin
    -1.0,-1.0, 1.0,
    -1.0, 1.0, 1.0, # triangle 1 : end
    1.0, 1.0,-1.0, # triangle 2 : begin
    -1.0,-1.0,-1.0,
    -1.0, 1.0,-1.0, # triangle 2 : end
    1.0,-1.0, 1.0,
    -1.0,-1.0,-1.0,
    1.0,-1.0,-1.0,
    1.0, 1.0,-1.0,
    1.0,-1.0,-1.0,
    -1.0,-1.0,-1.0,
    -1.0,-1.0,-1.0,
    -1.0, 1.0, 1.0,
    -1.0, 1.0,-1.0,
    1.0,-1.0, 1.0,
    -1.0,-1.0, 1.0,
    -1.0,-1.0,-1.0,
    -1.0, 1.0, 1.0,
    -1.0,-1.0, 1.0,
    1.0,-1.0, 1.0,
    1.0, 1.0, 1.0,
    1.0,-1.0,-1.0,
    1.0, 1.0,-1.0,
    1.0,-1.0,-1.0,
    1.0, 1.0, 1.0,
    1.0,-1.0, 1.0,
    1.0, 1.0, 1.0,
    1.0, 1.0,-1.0,
    -1.0, 1.0,-1.0,
    1.0, 1.0, 1.0,
    -1.0, 1.0,-1.0,
    -1.0, 1.0, 1.0,
    1.0, 1.0, 1.0,
    -1.0, 1.0, 1.0,
    1.0,-1.0, 1.0
]

g_color_buffer_data = [
    0.583,  0.771,  0.014,
    0.609,  0.115,  0.436,
    0.327,  0.483,  0.844,
    0.822,  0.569,  0.201,
    0.435,  0.602,  0.223,
    0.310,  0.747,  0.185,
    0.597,  0.770,  0.761,
    0.559,  0.436,  0.730,
    0.359,  0.583,  0.152,
    0.483,  0.596,  0.789,
    0.559,  0.861,  0.639,
    0.195,  0.548,  0.859,
    0.014,  0.184,  0.576,
    0.771,  0.328,  0.970,
    0.406,  0.615,  0.116,
    0.676,  0.977,  0.133,
    0.971,  0.572,  0.833,
    0.140,  0.616,  0.489,
    0.997,  0.513,  0.064,
    0.945,  0.719,  0.592,
    0.543,  0.021,  0.978,
    0.279,  0.317,  0.505,
    0.167,  0.620,  0.077,
    0.347,  0.857,  0.137,
    0.055,  0.953,  0.042,
    0.714,  0.505,  0.345,
    0.783,  0.290,  0.734,
    0.722,  0.645,  0.174,
    0.302,  0.455,  0.848,
    0.225,  0.587,  0.040,
    0.517,  0.713,  0.338,
    0.053,  0.959,  0.120,
    0.393,  0.621,  0.362,
    0.673,  0.211,  0.457,
    0.820,  0.883,  0.371,
    0.982,  0.099,  0.879
]

MvpID = None
MVP = None

def display(program):

	vertexbuffer = glvbo.VBO(np.array(g_vertex_buffer_data))
	colorbuffer = glvbo.VBO(np.array(g_color_buffer_data))

	# Clear the screen
	gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

	# Use our shader
	gl.glUseProgram(program)

	# Send our transformation to the currently bound shader, 
	# in the "MVP" uniform
	print MVP
	gl.glUniformMatrix4fv(MvpID, 1, gl.GL_FALSE, list(MVP))

	# 1rst attribute buffer : vertices
	gl.glEnableVertexAttribArray(0);
	vertexbuffer.bind()

	# 2nd attribute buffer : colors
	gl.glEnableVertexAttribArray(1);
	colorbuffer.bind()

	# Draw the triangle !
	gl.glDrawArrays(gl.GL_TRIANGLES, 0, 12*3); # 12*3 indices starting at 0 -> 12 triangles

	gl.glDisableVertexAttribArray(0);
	gl.glDisableVertexAttribArray(1);

def compile_vertex_shader(source):
	"""Compile a vertex shader from source."""
	vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
	gl.glShaderSource(vertex_shader, source)
	gl.glCompileShader(vertex_shader)
	# check compilation error
	result = gl.glGetShaderiv(vertex_shader, gl.GL_COMPILE_STATUS)
	if not(result):
		raise RuntimeError(gl.glGetShaderInfoLog(vertex_shader))
	return vertex_shader

def compile_fragment_shader(source):
	"""Compile a fragment shader from source."""
	fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
	gl.glShaderSource(fragment_shader, source)
	gl.glCompileShader(fragment_shader)
	# check compilation error
	result = gl.glGetShaderiv(fragment_shader, gl.GL_COMPILE_STATUS)
	if not(result):
		raise RuntimeError(gl.glGetShaderInfoLog(fragment_shader))
	return fragment_shader

def link_shader_program(vertex_shader, fragment_shader):
	"""Create a shader program with from compiled shaders."""
	program = gl.glCreateProgram()
	gl.glAttachShader(program, vertex_shader)
	gl.glAttachShader(program, fragment_shader)
	gl.glLinkProgram(program)
	# check linking error
	result = gl.glGetProgramiv(program, gl.GL_LINK_STATUS)
	if not(result):
		raise RuntimeError(gl.glGetProgramInfoLog(program))
	return program

def init_shader_program():
	# background color
	gl.glClearColor(0, 0, 0, 0)
	# create a Vertex Buffer Object with the specified data

	vertex_shader = compile_vertex_shader(VS)
	fragment_shader = compile_fragment_shader(FS)

	program = link_shader_program(vertex_shader, fragment_shader)

	# Enable depth test
	gl.glEnable(gl.GL_DEPTH_TEST)
	# Accept fragment if it closer to the camera than the former one
	gl.glDepthFunc(gl.GL_LESS)

	global MvpID
	MvpID = gl.glGetUniformLocation(program, "MVP")

	#Projection matrix : 45° Field of View, 4:3 ratio, display range : 0.1 unit <-> 100 units
	Projection = glm.mat4x4.perspective(45.0, 4.0 / 3.0, 0.1, 100.0)
	# Camera matrix
	View       = glm.mat4x4.look_at(
								glm.vec3(4,3,-3), # Camera is at (4,3,-3), in World Space
								glm.vec3(0,0,0), # and looks at the origin
								glm.vec3(0,1,0)  # Head is up (set to 0,-1,0 to look upside-down)
						   )
	# Model matrix : an identity matrix (model will be at the origin)
	Model      = glm.mat4x4.identity()
	# Our ModelViewProjection : multiplication of our 3 matrices
	global MVP
	tmp = Projection.mul_mat4(View)
	MVP = tmp.mul_mat4(Model) # Remember, matrix multiplication is the other way around

	return program

