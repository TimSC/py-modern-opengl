#Quake II gl3 shaders on cubes floating in space (see common3dadvanced.py), in a
#pygame window, the way the python Quake II port opens its window.
#
#usage: pygame_example3dadvanced.py [--seconds S] [--frames N] [--shot FILE.png]
#  It runs until a key press or the window is closed, or for S seconds if
#  given. --frames N [--shot FILE.png] is the self-check mode of all the
#  runners (see selfcheck.py): check frame N, save it, exit with 0 or 1.
#
#Context notes:
#  * pygame.display.gl_set_attribute must come *before* set_mode, or it has no
#    effect. The attributes ask SDL for a 3.2 core profile, as q2's
#    GL3_PrepareForWindow does. (On macOS a core context also needs the
#    forward-compatible flag, SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, which
#    q2 sets there.)
#  * pygame's OPENGL | DOUBLEBUF window has been seen to report GL_FRONT_LEFT
#    as its draw buffer (a stereo-looking setup). Reading GL_BACK before the
#    flip still gives the frame just drawn.

import sys
import time

import pygame
import OpenGL.GL as gl
import common3dadvanced
import selfcheck

def main():
	check = selfcheck.SelfCheck()
	seconds = float(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else None

	pygame.init()
	width, height = 640, 480
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 2)
	pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
	pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
	pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
	pygame.display.set_caption("Quake II gl3 shaders")
	print("GL_VERSION", gl.glGetString(gl.GL_VERSION).decode(), "| GLSL", gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).decode())

	params = common3dadvanced.init()

	t0 = time.time()
	clock = pygame.time.Clock()
	while True:
		for event in pygame.event.get():
			if event.type in (pygame.QUIT, pygame.KEYDOWN):
				pygame.quit(); return
		common3dadvanced.draw(params, width, height)
		# --frames N [--shot FILE]: check the Nth frame and exit (see selfcheck.py)
		if check.frame():
			pygame.quit()
			sys.exit(check.status)
		pygame.display.flip()
		if seconds is not None and time.time() - t0 >= seconds:
			pygame.quit(); return
		clock.tick(60)

if __name__ == "__main__":
	main()
