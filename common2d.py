#! /usr/bin/env python
# -*- coding: utf-8 -*-
#Based on http://cyrille.rossant.net/shaders-opengl/

import numpy as np
import OpenGL.GL as gl
import OpenGL.arrays.vbo as glvbo

# Vertex shader
VS = """
#version 330
// Attribute variable that contains coordinates of the vertices.
layout(location = 0) in vec2 position;

// Main function, which needs to set `gl_Position`.
void main()
{
    // The final position is transformed from a null signal to a sinewave here.
    // We pass the position to gl_Position, by converting it into
    // a 4D vector. The last coordinate should be 0 when rendering 2D figures.
    gl_Position = vec4(position.x, .2 * sin(20 * position.x), 0., 1.);
}
"""

# Fragment shader
FS = """
#version 330
// Output variable of the fragment shader, which is a 4D vector containing the
// RGBA components of the pixel color.
out vec4 out_color;

// Main fragment shader function.
void main()
{
    // We simply set the pixel color to yellow.
    out_color = vec4(1., 1., 0., 1.);
}
"""

def display(program):
	#This time consuming function should not normally be in the main loop,
	#but it is here for simplicity
	data = np.zeros((10000, 2), dtype=np.float32)
	data[:,0] = np.linspace(-1., 1., len(data))
	vbo = glvbo.VBO(data)

	# clear the buffer
	gl.glClear(gl.GL_COLOR_BUFFER_BIT)
	# bind the VBO 
	vbo.bind()
	# tell OpenGL that the VBO contains an array of vertices
	# prepare the shader		
	gl.glEnableVertexAttribArray(0)
	# these vertices contain 2 single precision coordinates
	gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
	gl.glUseProgram(program)
	# draw "count" points from the VBO
	gl.glDrawArrays(gl.GL_LINE_STRIP, 0, len(data))

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
	return program

