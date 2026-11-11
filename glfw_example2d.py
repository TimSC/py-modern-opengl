#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import glfw, common2d
import selfcheck

def error_callback(error, description):
	print("glfw error", error, description)

def main():
	check = selfcheck.SelfCheck()

	# Initialize the library
	if not glfw.init():
		return
	
	glfw.set_error_callback(error_callback)

	# Ask for a 3.3 core profile, as the shaders are GLSL 3.30 (forward
	# compatible is needed for a core context on macOS)
	glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
	glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
	glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
	glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

	# Create a windowed mode window and its OpenGL context
	window = glfw.create_window(640, 480, "Hello World", None, None)
	if not window:
		glfw.terminate()
		return

	# Make the window's context current
	glfw.make_context_current(window)

	program = common2d.init_shader_program()

	# Loop until the user closes the window
	while not glfw.window_should_close(window):
		# Render here
		common2d.display(program)

		# --frames N [--shot FILE]: check the Nth frame and exit (see selfcheck.py)
		if check.frame():
			glfw.terminate()
			sys.exit(check.status)

		# Swap front and back buffers
		glfw.swap_buffers(window)

		# Poll for and process events
		glfw.poll_events()

	glfw.terminate()

if __name__ == "__main__":
	main()

