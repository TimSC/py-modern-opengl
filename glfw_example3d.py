#! /usr/bin/env python
# -*- coding: utf-8 -*-
import glfw, common3d
import OpenGL.GL as gl
import numpy as np

def error_callback():
	print "error_callback"

def main():
	# Initialize the library
	if not glfw.init():
		return
	
	glfw.set_error_callback(error_callback)

	# Create a windowed mode window and its OpenGL context
	window = glfw.create_window(640, 480, "Hello World", None, None)
	if not window:
		glfw.terminate()
		return

	# Make the window's context current
	glfw.make_context_current(window)

	program = common3d.init_shader_program()

	# Loop until the user closes the window
	while not glfw.window_should_close(window):
		# Render here
		common3d.display(program)

		# Swap front and back buffers
		glfw.swap_buffers(window)

		# Poll for and process events
		glfw.poll_events()

	glfw.terminate()

if __name__ == "__main__":
	main()

