# coding=utf-8

import pyglfw.pyglfw as glfw
import common2d

if __name__ == '__main__':
	glfw.init()

	w = glfw.Window(640, 480, "Hello world!")

	w.make_current()

	program = common2d.init_shader_program()

	while not w.should_close:
		# Render here
		common2d.display(program)

		w.swap_buffers()
		glfw.poll_events()

		if w.keys.escape:
			w.should_close = True

	glfw.terminate()

