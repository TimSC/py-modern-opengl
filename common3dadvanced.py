#Quake II style 3D shaders in python: the gl3 renderer's shaders from Yamagi Quake II
#(src/client/refresh/gl3/gl3_shaders.c) with the C code that feeds them, drawing
#a row of cubes floating in space, one cube per shader.
#
#Run it with glut_example3dadvanced.py or pygame_example3dadvanced.py.
#
#Licence: the GLSL sources and the functions marked "from Yamagi" are copied or
#ported from Yamagi Quake II, Copyright (C) 1997-2001 Id Software, Inc. and
#Copyright (C) 2016-2017 Daniel Gibson, under the GNU General Public License
#version 2 or later. So this file is GPL v2+ as well, unlike the BSD-style
#examples next to it.
#
#=============================================================================
#The approach
#=============================================================================
#
#This only looks at the shaders: what each one expects as input and how q2 sets
#that up. The scene is deliberately simple. q2 gets its geometry from BSP maps
#and md2 models; here every object is a cube, and all lighting data is
#generated at start up. The lighting is static (lightmaps are baked once and the
#dynamic lights don't move); only the cubes turn.
#
#  cube              shader (gl3state.*)   what it shows
#  ----              -------------------   -------------
#  top row
#   lightmapped      si3Dlm                texture * (4 lightmaps * lmScales)
#                                          + dynamic lights, overbrightbits
#   flowing          si3DlmFlow            the same, texture scrolling (SURF_FLOWING)
#   water            si3Dturb              warping texture coordinates
#                                          (SURF_WARP), translucent (SURF_TRANS66)
#   glass            si3Dtrans             plain texture, translucent (SURF_TRANS33)
#  bottom row
#   model            si3Dalias             md2-style model: per-vertex light colour,
#                                          frames interpolated on the CPU
#   shell            si3DaliasColor        a powerup shell: flat colour, translucent
#   beam             si3DcolorOnly         a laser beam's flat colour (uniCommon.color)
#   sprite           si3DspriteAlpha       alpha tested texture (discard at <= 0.666)
#  everything else
#   sky              si3Dsky               a sky box around the viewer
#   particles        siParticle            round point sprites (gl_PointSize,
#                                          gl_PointCoord), two of them mark where
#                                          the dynamic lights are
#
#The C structure is kept where it matters for the shaders, under the C names:
#
#  CompileShader, CreateShaderProgram, initShader3D, initUBOs, updateUBO
#      (gl3_shaders.c): how the programs, attribute locations, samplers and
#      uniform blocks are set up. Every 3D shader is two sources glued together,
#      vertexCommon3D + vertexSrc3D... and fragmentCommon3D + fragmentSrc3D...
#  GL3_SurfInit (gl3_surf.c): the three vertex layouts (VAOs) the 3D shaders use.
#  GL3_SetPerspective, rotAroundAxisXYZ, rotAroundAxisZYX, the view matrix part
#      of SetupGL, GL3_RotateForEntity (gl3_main.c): q2's matrices.
#  The draw order of GL3_RenderView: world, entities (opaque, then translucent),
#      particles, alpha surfaces.
#
#Simplified compared with Yamagi:
#  - No binding cache (GL3_UseProgram, GL3_Bind, GL3_BindVAO...). Yamagi skips
#    redundant binds; here every bind is done directly.
#  - No 3D batching. At the pinned Yamagi commit brush polygons are collected
#    into one vertex/index buffer per frame (GL3_Add3DdrawCmdToBatch,
#    GL3_Draw3DBatchesNow) and drawn as GL_TRIANGLES. Here each cube is
#    uploaded into the same vbo3D/ebo3D and drawn on its own.
#  - A tiny lightmap atlas (BLOCK_WIDTH x BLOCK_HEIGHT luxels) instead of 1024x512.
#  - Model shading uses a formula instead of the r_avertexnormal_dots table
#    (anorm_dots.h). That table is precomputed from much the same formula.
#
#=============================================================================
#Quirks and gotchas (most of them are silent: no GL error, just wrong pixels)
#=============================================================================
#
#PyOpenGL
#  * glVertexAttribPointer's last argument is a byte offset into the VBO, and it
#    must be ctypes.c_void_p(offset). A plain python int, even 0, is turned
#    into a pointer to a temporary array holding that int, so the attribute
#    reads garbage. None works for offset 0 only.
#  * The same goes for glVertexAttribIPointer and the index offset of
#    glDrawElements.
#  * glGetActiveUniformBlockiv needs a ctypes array to write into. A python
#    list is accepted and silently left at 0.
#  * OpenGL.GL.shaders.compileProgram validates the program after linking. In
#    a core profile, validation fails if no VAO is bound yet, so this file
#    links programs itself (CreateShaderProgram), as q2 does.
#  * glShaderSource takes a list of strings, like the C call with several
#    sources. q2 relies on this to put "#version 150" and the common
#    declarations in front of each shader. Compile errors then count lines
#    across all the pieces.
#  * Structured numpy arrays (a dtype with named fields, standing in for a C
#    struct) are uploaded as raw bytes: buffer.view(np.uint8).
#
#Context
#  * The shaders are "#version 150", i.e. OpenGL 3.2. q2 asks SDL for a 3.2
#    core profile and so do the two runner scripts. In a core profile
#    nothing draws unless a VAO is bound, GL_CLAMP and GL_QUADS are gone, and
#    the fixed function calls (glBegin, glMatrixMode...) are errors.
#  * The window needs a depth buffer (GLUT_DEPTH; SDL gives one by default).
#    Without it GL_DEPTH_TEST does nothing, and you see the back of the cubes
#    through the front.
#  * gl_PointCoord: some compatibility profiles (NVIDIA's for one) only give it
#    a value with glEnable(GL_POINT_SPRITE). That enum does not exist in a core
#    profile, where it is always on. With a compatibility context and square,
#    flat particles, this is the cause.
#  * gl_PointSize written by the vertex shader is ignored unless
#    GL_PROGRAM_POINT_SIZE is enabled. Then every particle is 1 pixel.
#
#q2 conventions
#  * The world is Z up, X forward, Y left. The view matrix in SetupGL first
#    turns that into GL's eye space (X right, Y up, looking down -Z). Then it
#    rotates by the view angles and moves by -vieworg.
#  * hmm_mat4 is column-major: Elements[column][row]. This file keeps that
#    layout in numpy arrays (m[column][row]), so the C initialisers can be copied
#    as they are, and the bytes go to GL (or a std140 block) unchanged. The catch:
#    numpy's @ then works on the transposes, so HMM_MultiplyMat4(a, b) is
#    b @ a.
#  * Polygons are clockwise seen from the front, and q2 culls with
#    glCullFace(GL_FRONT). Build faces counter-clockwise (the GL default) and
#    q2 culls exactly the faces you wanted to see.
#  * Brush texture coordinates are in "texture repeats" (world units / texture
#    size). The water shader is different: it wants them in world units and
#    divides by 64 itself, after warping ("tc *= 1.0/64.0; // do this last").
#  * Lightmap texture coordinates point at luxel centres: one luxel covers 16
#    world units, and +8 moves to the middle of it (see BuildLightmappedCube).
#  * The sky box is 2300 units from the viewer in every direction. Its corners
#    are then 2300*sqrt(3) = 3984 away, inside zFar = 4096. A bigger box loses
#    its corners to the far plane.
#
#The shaders
#  * Fixed attribute locations: CreateShaderProgram calls glBindAttribLocation
#    for all six GL3_ATTRIB_* names before linking. So any VAO works with any
#    shader, and nothing calls glGetAttribLocation.
#  * lightFlags is an "in uint". Its VAO entry must be set up with
#    glVertexAttribIPointer (I for integer). glVertexAttribPointer would turn
#    the bits into a float, and the "flags & (1u << i)" test sees nonsense. An
#    integer must also be passed to the fragment shader as "flat".
#  * Uniform blocks are std140, and the C structs (uniCommon, uni3D, uniLights)
#    have to match the GLSL byte for byte:
#      - a vec3 is padded to 16 bytes (DynLight is vec3 + float + vec4);
#      - uniCommon has a padding float after intensity2D, so that "color"
#        starts at 16;
#      - uni3D has two padding floats at the end.
#    initShader3D checks GL_UNIFORM_BLOCK_DATA_SIZE against the C size and
#    refuses the shader if they differ. Keep that check; a size mismatch is
#    otherwise silent.
#  * Two steps connect a block to a buffer: glUniformBlockBinding (block ->
#    binding point, per program) and glBindBufferBase (binding point -> buffer,
#    global). q2 uses binding points 0 uniCommon, 1 uni2D, 2 uni3D, 3 uniLights.
#  * uniLights mixes floats and uints in one buffer. Here it is a float32 array,
#    and numDynLights is written through a uint32 view of the same memory.
#  * Samplers are plain uniforms and must be set with the program in use: "tex"
#    is texture unit 0 and lightmap0..3 are units 1..4. lmScales (one RGBA scale
#    per light style) is also a plain uniform, so it is per program: si3Dlm and
#    si3DlmFlow each keep their own copy (gl3ShaderInfo_t.lmScales).
#  * The lightmap shaders always sample all four lightmaps. Unused slots must
#    still have a complete texture bound, scaled to 0 by lmScales. An
#    incomplete texture reads as black, which is harmless only when its scale
#    is 0.
#  * The 3D shaders do their own gamma: outColor = pow(colour, 1/vid_gamma), and
#    intensity (gl3_intensity) multiplies textures. Lightmaps get overbrightbits
#    (gl3_overbrightbits) instead. With Yamagi's defaults (vid_gamma 1.2,
#    intensity 1.5, overbrightbits 1.3) everything is brighter than the
#    textures.
#  * uniCommon.color is shared with the 2D shaders (Draw_Fill etc.). Set it back
#    to (1, 1, 1, 1) after using it for a beam.
#  * Everything in the uni3D block (transModel, alpha, scroll...) keeps its
#    value until something writes it again, across draws and shaders. Reset
#    transModel to the identity after drawing entities and alpha to 1.0 after
#    a translucent thing, as Yamagi does. Otherwise the next draw quietly
#    inherits them: world-space particles turn with the last model.
#  * uni3D.alpha only matters with GL_BLEND on. q2 draws translucent things
#    after the opaque ones with glDepthMask(GL_FALSE), so they don't hide what
#    is behind them.
#
#Based on the examples in this directory and
#https://github.com/yquake2/yquake2/blob/master/src/client/refresh/gl3/gl3_shaders.c

import ctypes
import math
import os
import time

import numpy as np
import OpenGL.GL as gl
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

# q2 (gl3 header/local.h): attribute locations and uniform block binding points
GL3_ATTRIB_POSITION   = 0
GL3_ATTRIB_TEXCOORD   = 1 # for normal texture
GL3_ATTRIB_LMTEXCOORD = 2 # for lightmap
GL3_ATTRIB_COLOR      = 3 # per-vertex color
GL3_ATTRIB_NORMAL     = 4 # vertex normal
GL3_ATTRIB_LIGHTFLAGS = 5 # uint, each set bit means "dyn light i affects this surface"

GL3_BINDINGPOINT_UNICOMMON = 0
GL3_BINDINGPOINT_UNI2D     = 1
GL3_BINDINGPOINT_UNI3D     = 2
GL3_BINDINGPOINT_UNILIGHTS = 3

MAX_DLIGHTS = 32
MAX_LIGHTMAPS_PER_SURFACE = 4 # MAXLIGHTMAPS, light styles per surface
# Yamagi's lightmap atlas is 1024x512 luxels; a few cubes need far less
BLOCK_WIDTH, BLOCK_HEIGHT = 64, 16

# Yamagi's default cvars
vid_gamma = 1.2
gl3_intensity = 1.5
gl3_intensity_2D = 1.5
gl3_overbrightbits = 1.3
gl3_particle_size = 120 # default 40: at the cubes' distance that is a 2 pixel dot
gl3_particle_fade_factor = 1.2
gl_znear = 4
r_farsee = 0
fov = 90 # the client's fov cvar (horizontal)

# light styles as the client sets them: "m" is 1.0 ('a' is 0, 'z' is 2.08).
# A real map animates them ten times a second; here they are fixed.
lightstyles = {0: "m", 5: "j"}

def LightStyleValue(style):
	# CL_RunLightStyles: (map[ofs] - 'a') / ('m' - 'a')
	return (ord(lightstyles[style][0]) - ord('a')) / float(ord('m') - ord('a'))

#=============================================================================
#The shaders, copied from gl3_shaders.c
#=============================================================================
#In the C they are written with a MULTILINE_STRING(...) macro, which turns its
#argument into one long line (the preprocessor removes the // comments first,
#so that is safe). Here they are normal python strings with their newlines.

vertexCommon3D = """
		in vec3 position;   // GL3_ATTRIB_POSITION
		in vec2 texCoord;   // GL3_ATTRIB_TEXCOORD
		in vec2 lmTexCoord; // GL3_ATTRIB_LMTEXCOORD
		in vec4 vertColor;  // GL3_ATTRIB_COLOR
		in vec3 normal;     // GL3_ATTRIB_NORMAL
		in uint lightFlags; // GL3_ATTRIB_LIGHTFLAGS

		out vec2 passTexCoord;

		// for UBO shared between all 3D shaders
		layout (std140) uniform uni3D
		{
			mat4 transProjView;
			mat4 transModel;

			float scroll; // for SURF_FLOWING
			float time;
			float alpha;
			float overbrightbits;
			float particleFadeFactor;
			float lightScaleForTurb; // surfaces with SURF_DRAWTURB (water, lava) don't have lightmaps, use this instead
			float _pad_1; // AMDs legacy windows driver needs this, otherwise uni3D has wrong size
			float _pad_2;
		};
"""

fragmentCommon3D = """
		in vec2 passTexCoord;

		out vec4 outColor;

		// for UBO shared between all shaders (incl. 2D)
		layout (std140) uniform uniCommon
		{
			float gamma; // this is 1.0/vid_gamma
			float intensity;
			float intensity2D; // for HUD, menus etc

			vec4 color; // really?
		};
		// for UBO shared between all 3D shaders
		layout (std140) uniform uni3D
		{
			mat4 transProjView;
			mat4 transModel;

			float scroll; // for SURF_FLOWING
			float time;
			float alpha;
			float overbrightbits;
			float particleFadeFactor;
			float lightScaleForTurb; // surfaces with SURF_DRAWTURB (water, lava) don't have lightmaps, use this instead
			float _pad_1; // AMDs legacy windows driver needs this, otherwise uni3D has wrong size
			float _pad_2;
		};
"""

vertexSrc3D = """
		// it gets attributes and uniforms from vertexCommon3D

		void main()
		{
			passTexCoord = texCoord;
			gl_Position = transProjView * transModel * vec4(position, 1.0);
		}
"""

vertexSrc3Dlm = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec2 passLMcoord;
		out vec3 passWorldCoord;
		out vec3 passNormal;
		flat out uint passLightFlags;

		void main()
		{
			passTexCoord = texCoord;
			passLMcoord = lmTexCoord;
			vec4 worldCoord = transModel * vec4(position, 1.0);
			passWorldCoord = worldCoord.xyz;
			vec4 worldNormal = transModel * vec4(normal, 0.0f);
			passNormal = normalize(worldNormal.xyz);
			passLightFlags = lightFlags;

			gl_Position = transProjView * worldCoord;
		}
"""

vertexSrc3DlmFlow = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec2 passLMcoord;
		out vec3 passWorldCoord;
		out vec3 passNormal;
		flat out uint passLightFlags;

		void main()
		{
			passTexCoord = texCoord + vec2(scroll, 0.0);
			passLMcoord = lmTexCoord;
			vec4 worldCoord = transModel * vec4(position, 1.0);
			passWorldCoord = worldCoord.xyz;
			vec4 worldNormal = transModel * vec4(normal, 0.0f);
			passNormal = normalize(worldNormal.xyz);
			passLightFlags = lightFlags;

			gl_Position = transProjView * worldCoord;
		}
"""

fragmentSrc3D = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply intensity and gamma
			texel.rgb *= intensity;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dwater = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec2 tc = passTexCoord;
			tc.s += sin( passTexCoord.t*0.125 + time ) * 4.0;
			tc.s += scroll;
			tc.t += sin( passTexCoord.s*0.125 + time ) * 4.0;
			tc *= 1.0/64.0; // do this last

			vec4 texel = texture(tex, tc);

			// apply intensity and gamma
			texel.rgb *= intensity * lightScaleForTurb;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dlm = """
		// it gets attributes and uniforms from fragmentCommon3D

		struct DynLight { // gl3UniDynLight in C
			vec3 lightOrigin;
			float _pad;
			//vec3 lightColor;
			//float lightIntensity;
			vec4 lightColor; // .a is intensity; this way it also works on OSX...
			// (otherwise lightIntensity always contained 1 there)
		};

		layout (std140) uniform uniLights
		{
			DynLight dynLights[32];
			uint numDynLights;
			uint _pad1; uint _pad2; uint _pad3; // FFS, AMD!
		};

		uniform sampler2D tex;

		uniform sampler2D lightmap0;
		uniform sampler2D lightmap1;
		uniform sampler2D lightmap2;
		uniform sampler2D lightmap3;

		uniform vec4 lmScales[4];

		in vec2 passLMcoord;
		in vec3 passWorldCoord;
		in vec3 passNormal;
		flat in uint passLightFlags;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply intensity
			texel.rgb *= intensity;

			// apply lightmap
			vec4 lmTex = texture(lightmap0, passLMcoord) * lmScales[0];
			lmTex     += texture(lightmap1, passLMcoord) * lmScales[1];
			lmTex     += texture(lightmap2, passLMcoord) * lmScales[2];
			lmTex     += texture(lightmap3, passLMcoord) * lmScales[3];

			if(passLightFlags != 0u)
			{
				// TODO: or is hardcoding 32 better?
				for(uint i=0u; i<numDynLights; ++i)
				{
					// I made the following up, it's probably not too cool..
					// it basically checks if the light is on the right side of the surface
					// and, if it is, sets intensity according to distance between light and pixel on surface

					// dyn light number i does not affect this plane, just skip it
					if((passLightFlags & (1u << i)) == 0u)  continue;

					float intens = dynLights[i].lightColor.a;

					vec3 lightToPos = dynLights[i].lightOrigin - passWorldCoord;
					float distLightToPos = length(lightToPos);
					float fact = max(0.0, intens - distLightToPos - 52.0);

					// move the light source a bit further above the surface
					// => helps if the lightsource is so close to the surface (e.g. grenades, rockets)
					//    that the dot product below would return 0
					// (light sources that are below the surface are filtered out by lightFlags)
					lightToPos += passNormal*32.0;

					// also factor in angle between light and point on surface
					fact *= max(0.0, dot(passNormal, normalize(lightToPos)));


					lmTex.rgb += dynLights[i].lightColor.rgb * fact * (1.0/256.0);
				}
			}

			lmTex.rgb *= overbrightbits;
			outColor = lmTex*texel;
			outColor.rgb = pow(outColor.rgb, vec3(gamma)); // apply gamma correction to result

			outColor.a = 1.0; // lightmaps aren't used with translucent surfaces
		}
"""
# (fragmentSrc3DlmNoColor, used with gl3_colorlight 0, is the same plus
# "lmTex.rgb = vec3(0.333 * (lmTex.r+lmTex.g+lmTex.b));" before overbrightbits)

fragmentSrc3Dcolor = """
		// it gets attributes and uniforms from fragmentCommon3D

		void main()
		{
			vec4 texel = color;

			// apply gamma correction and intensity
			// texel.rgb *= intensity; TODO: use intensity here? (this is used for beams)
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3Dsky = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// TODO: something about GL_BLEND vs GL_ALPHATEST etc

			// apply gamma correction
			// texel.rgb *= intensity; // TODO: really no intensity for sky?
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrc3DspriteAlpha = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			if(texel.a <= 0.666)
				discard;

			// apply gamma correction and intensity
			texel.rgb *= intensity;
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			//outColor.a = texel.a*alpha; // I think alpha shouldn't be modified by gamma and intensity
			outColor.a = texel.a; // I think in this case alpha from uni3d shouldn't be used
		}
"""

vertexSrc3Dwater = """
		// it gets attributes and uniforms from vertexCommon3D
		void main()
		{
			passTexCoord = texCoord;

			gl_Position = transProjView * transModel * vec4(position, 1.0);
		}
"""

vertexSrcAlias = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec4 passColor;

		void main()
		{
			passColor = vertColor*overbrightbits;
			passTexCoord = texCoord;
			gl_Position = transProjView* transModel * vec4(position, 1.0);
		}
"""

fragmentSrcAlias = """
		// it gets attributes and uniforms from fragmentCommon3D

		uniform sampler2D tex;

		in vec4 passColor;

		void main()
		{
			vec4 texel = texture(tex, passTexCoord);

			// apply gamma correction and intensity
			texel.rgb *= intensity;
			texel.a *= alpha; // is alpha even used here?
			texel *= min(vec4(1.5), passColor);

			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

fragmentSrcAliasColor = """
		// it gets attributes and uniforms from fragmentCommon3D

		in vec4 passColor;

		void main()
		{
			vec4 texel = passColor;

			// apply gamma correction and intensity
			// texel.rgb *= intensity; // TODO: color-only rendering probably shouldn't use intensity?
			texel.a *= alpha; // is alpha even used here?
			outColor.rgb = pow(texel.rgb, vec3(gamma));
			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

vertexSrcParticles = """
		// it gets attributes and uniforms from vertexCommon3D

		out vec4 passColor;

		void main()
		{
			passColor = vertColor;
			gl_Position = transProjView * transModel * vec4(position, 1.0);

			// abusing texCoord for pointSize, pointDist for particles
			float pointDist = texCoord.y*0.1; // with factor 0.1 it looks good.

			gl_PointSize = texCoord.x/pointDist;
		}
"""

fragmentSrcParticles = """
		// it gets attributes and uniforms from fragmentCommon3D

		in vec4 passColor;

		void main()
		{
			vec2 offsetFromCenter = 2.0*(gl_PointCoord - vec2(0.5, 0.5)); // normalize so offset is between 0 and 1 instead 0 and 0.5
			float distSquared = dot(offsetFromCenter, offsetFromCenter);
			if(distSquared > 1.0) // this makes sure the particle is round
				discard;

			vec4 texel = passColor;

			// apply gamma correction and intensity
			//texel.rgb *= intensity; TODO: intensity? Probably not?
			outColor.rgb = pow(texel.rgb, vec3(gamma));

			// I want the particles to fade out towards the edge, the following seems to look nice
			texel.a *= min(1.0, particleFadeFactor*(1.0 - distSquared));

			outColor.a = texel.a; // I think alpha shouldn't be modified by gamma and intensity
		}
"""

#=============================================================================
#The C structs the shaders read
#=============================================================================

# gl3_3D_vtx_t (header/model.h): brush surfaces, sky, sprites. A numpy
# structured dtype is the closest thing to a C struct: it has the same layout
# (44 bytes, no padding) and dtype.fields gives offsetof() for the VAO setup.
gl3_3D_vtx_t = np.dtype([
	("pos", "<f4", 3),
	("texCoord", "<f4", 2),
	("lmTexCoord", "<f4", 2), # lightmap texture coordinate (sometimes unused)
	("normal", "<f4", 3),
	("lightFlags", "<u4"), # bit i set means: dynlight i affects surface
])

# gl3_alias_vtx_t: models. Particles use the same 9 floats, with texCoord
# holding (point size, distance to the viewer) and color the particle colour.
gl3_alias_vtx_t = np.dtype([
	("pos", "<f4", 3),
	("texCoord", "<f4", 2),
	("color", "<f4", 4),
])

def offsetof(dtype, field):
	return ctypes.c_void_p(dtype.fields[field][1])

class gl3ShaderInfo_t(object):

	def __init__(self):

		self.shaderProgram = 0 #GLuint
		self.uniLmScalesOrTime = -1 #GLint, for 3D: lmScales (pointless for 2D)
		self.uniVblend = -1 #GLint, for 2D postprocess: v_blend
		self.lmScales = np.zeros((4, 4), dtype=np.float32) #hmm_vec4[4]

class gl3state_t(object):

	def __init__(self):

		# the programs
		self.si3Dlm = gl3ShaderInfo_t() # a regular opaque face (e.g. from brush) with lightmap
		self.si3Dtrans = gl3ShaderInfo_t() # transparent is always w/o lightmap
		self.si3DcolorOnly = gl3ShaderInfo_t() # used for beams - no lightmaps
		self.si3Dturb = gl3ShaderInfo_t() # for water etc - always without lightmap
		self.si3DlmFlow = gl3ShaderInfo_t() # for flowing/scrolling things with lightmap (conveyor belts etc)
		self.si3Dsky = gl3ShaderInfo_t() # guess what..
		self.si3DspriteAlpha = gl3ShaderInfo_t() # for sprites that need alpha testing
		self.si3Dalias = gl3ShaderInfo_t() # for models
		self.si3DaliasColor = gl3ShaderInfo_t() # for models w/ flat colors
		self.siParticle = gl3ShaderInfo_t() # for particles. surprising, right?

		# the vertex layouts (GL3_SurfInit)
		self.vao3D, self.vbo3D, self.ebo3D = 0, 0, 0 #GLuint, for brushes etc, using 10 floats and one uint as vertex input
		self.vaoAlias, self.vboAlias, self.eboAlias = 0, 0, 0 #GLuint, for models, using 9 floats as (x,y,z, s,t, r,g,b,a)
		self.vaoParticle, self.vboParticle = 0, 0 #GLuint, for particles, using 9 floats (x,y,z, size,distance, r,g,b,a)

		# gl3UniCommon_t (std140, 32 bytes): gamma, intensity, intensity2D,
		# _padding, then vec4 color
		self.uniCommonData = np.zeros(8, dtype=np.float32)
		# gl3Uni3D_t (std140, 160 bytes): mat4 transProjViewMat4, mat4 transModelMat4,
		# scroll, time, alpha, overbrightbits, particleFadeFactor,
		# lightScaleForTurb, _padding[2]
		self.uni3DData = np.zeros(40, dtype=np.float32)
		# gl3UniLights_t (std140, 1040 bytes): MAX_DLIGHTS times
		# gl3UniDynLight {vec3 origin; float _padding; vec3 color; float intensity;}
		# then GLuint numDynLights and _padding[3]
		self.uniLightsData = np.zeros(MAX_DLIGHTS * 8 + 4, dtype=np.float32)
		self.uniCommonUBO, self.uni3DUBO, self.uniLightsUBO = 0, 0, 0 #GLuint
		self.currentUBO = 0 #GLuint

		self.projMat3D = None #hmm_mat4
		self.viewMat3D = None #hmm_mat4

gl3state = gl3state_t()

# where the fields of gl3Uni3D_t are in uni3DData
U3D_TRANSPROJVIEW, U3D_TRANSMODEL = slice(0, 16), slice(16, 32)
U3D_SCROLL, U3D_TIME, U3D_ALPHA, U3D_OVERBRIGHTBITS, U3D_PARTICLEFADEFACTOR, U3D_LIGHTSCALEFORTURB = range(32, 38)

def SetTransMat(index, mat):
	# hmm_mat4 Elements[col][row] -> 16 floats, column after column
	gl3state.uni3DData[index] = mat.reshape(16)

#=============================================================================
#Matrices (HandmadeMath's hmm_mat4 and the q2 helpers in gl3_main.c)
#=============================================================================
#A matrix is a 4x4 float32 array indexed m[column][row], like
#hmm_mat4.Elements, so the C initialisers below are written column by column
#exactly as in the C. That array, read row after row, *is* GL's column-major
#order, so it goes into the UBO unchanged (no transpose).

def HMM_Mat4d(diagonal):
	return np.eye(4, dtype=np.float32) * diagonal

gl3_identityMat4 = HMM_Mat4d(1.0)

def HMM_MultiplyMat4(left, right):
	# The arrays hold the transposed matrices (rows of the array are columns),
	# and (L*R)^T = R^T * L^T, so numpy's product goes the other way round.
	return (right @ left).astype(np.float32)

def HMM_Translate(translation):
	ret = HMM_Mat4d(1.0)
	ret[3][0:3] = translation # the 4th column
	return ret

def rotAroundAxisZYX(aroundZdeg, aroundYdeg, aroundXdeg): # from Yamagi
	# Yaw-Pitch-Roll
	# equivalent to R_z * R_y * R_x where R_x is the trans matrix for rotating around X axis for aroundXdeg
	alpha = math.radians(aroundZdeg)
	beta = math.radians(aroundYdeg)
	gamma = math.radians(aroundXdeg)

	sinA, cosA = math.sin(alpha), math.cos(alpha)
	sinB, cosB = math.sin(beta), math.cos(beta)
	sinG, cosG = math.sin(gamma), math.cos(gamma)

	return np.array([
		[ cosA*cosB,                  sinA*cosB,                   -sinB,    0 ], # first *column*
		[ cosA*sinB*sinG - sinA*cosG, sinA*sinB*sinG + cosA*cosG, cosB*sinG, 0 ],
		[ cosA*sinB*cosG + sinA*sinG, sinA*sinB*cosG - cosA*sinG, cosB*cosG, 0 ],
		[  0,                          0,                          0,        1 ]
	], dtype=np.float32)

def rotAroundAxisXYZ(aroundXdeg, aroundYdeg, aroundZdeg): # from Yamagi
	# equivalent to R_x * R_y * R_z where R_x is the trans matrix for rotating around X axis for aroundXdeg
	alpha = math.radians(aroundXdeg)
	beta = math.radians(aroundYdeg)
	gamma = math.radians(aroundZdeg)

	sinA, cosA = math.sin(alpha), math.cos(alpha)
	sinB, cosB = math.sin(beta), math.cos(beta)
	sinG, cosG = math.sin(gamma), math.cos(gamma)

	return np.array([
		[  cosB*cosG,  sinA*sinB*cosG + cosA*sinG, -cosA*sinB*cosG + sinA*sinG, 0 ], # first *column*
		[ -cosB*sinG, -sinA*sinB*sinG + cosA*cosG,  cosA*sinB*sinG + sinA*cosG, 0 ],
		[  sinB,      -sinA*cosB,                   cosA*cosB,                  0 ],
		[  0,          0,                           0,                          1 ]
	], dtype=np.float32)

def GL3_SetPerspective(fovy, width, height): # from Yamagi
	# equivalent to R_SetPerspective() but returning a matrix instead of setting internal OpenGL state

	# gluPerspective() / R_MYgluPerspective() style parameters
	zNear = max(gl_znear, 0.1)
	zFar = 8192.0 if r_farsee else 4096.0
	aspect = width / float(height)

	# calculation of left, right, bottom, top is from R_MYgluPerspective() of old gl backend
	# which seems to be slightly different from the real gluPerspective()
	# and thus also from HMM_Perspective()
	top = zNear * math.tan(fovy * math.pi / 360.0)
	right = top * aspect

	bottom = -top
	left = -right

	# the following emulates glFrustum(left, right, bottom, top, zNear, zFar)
	A = (right+left)/(right-left)
	B = (top+bottom)/(top-bottom)
	C = -(zFar+zNear)/(zFar-zNear)
	D = -(2.0*zFar*zNear)/(zFar-zNear)

	return np.array([
		[ (2.0*zNear)/(right-left), 0, 0, 0 ], # first *column*
		[ 0, (2.0*zNear)/(top-bottom), 0, 0 ],
		[ A, B, C, -1.0 ],
		[ 0, 0, D, 0 ]
	], dtype=np.float32)

def CalcFov(fov_x, width, height):
	# the client's CalcFov (cl_view.c): q2's fov cvar is horizontal, GL wants vertical
	x = width / math.tan(fov_x / 360.0 * math.pi)
	a = math.atan(height / x)
	return a * 360.0 / math.pi

def GL3_RotateForEntity(angles, origin): # from Yamagi, returns the matrix
	# angles: pitch (around y), yaw (around z), roll (around x)
	# rot matrices to be multiplied in order Z, Y, X (yaw, pitch, roll)
	transMat = rotAroundAxisZYX(angles[1], -angles[0], -angles[2])

	for i in range(3):
		transMat[3][i] = origin[i] # set translation

	return transMat

#=============================================================================
#Shader setup, from gl3_shaders.c
#=============================================================================

def CompileShader(shaderType, shaderSrc, shaderSrc2=None): # from Yamagi
	shader = gl.glCreateShader(shaderType)

	version = "#version 150\n" # Desktop GL ("#version 300 es\nprecision highp float;\n" for GLES3)
	sources = [version, shaderSrc]
	if shaderSrc2 is not None:
		sources.append(shaderSrc2)

	# like the C, several strings in one call; GL compiles them as one
	gl.glShaderSource(shader, sources)
	gl.glCompileShader(shader)
	if gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS) != gl.GL_TRUE:
		log = gl.glGetShaderInfoLog(shader)
		shaderTypeStr = {gl.GL_VERTEX_SHADER: "Vertex", gl.GL_FRAGMENT_SHADER: "Fragment"}.get(shaderType, "")
		print("ERROR: Compiling {} Shader failed: {}".format(shaderTypeStr, log.decode(errors="replace")))
		gl.glDeleteShader(shader)
		return 0

	return shader

def CreateShaderProgram(shaders): # from Yamagi
	shaderProgram = gl.glCreateProgram()
	if shaderProgram == 0:
		print("ERROR: Couldn't create a new Shader Program!")
		return 0

	for s in shaders:
		gl.glAttachShader(shaderProgram, s)

	# make sure all shaders use the same attribute locations for common attributes
	# (so the same VAO can easily be used with different shaders)
	# (this has to happen before glLinkProgram to have any effect)
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_POSITION, "position")
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_TEXCOORD, "texCoord")
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_LMTEXCOORD, "lmTexCoord")
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_COLOR, "vertColor")
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_NORMAL, "normal")
	gl.glBindAttribLocation(shaderProgram, GL3_ATTRIB_LIGHTFLAGS, "lightFlags")

	# the following line is not necessary/implicit (as there's only one output)
	# glBindFragDataLocation(shaderProgram, 0, "outColor"); XXX would this even be here?

	gl.glLinkProgram(shaderProgram)

	if gl.glGetProgramiv(shaderProgram, gl.GL_LINK_STATUS) != gl.GL_TRUE:
		log = gl.glGetProgramInfoLog(shaderProgram)
		print("ERROR: Linking shader program failed: {}".format(log.decode(errors="replace")))
		gl.glDeleteProgram(shaderProgram)
		return 0

	for s in shaders:
		# after linking, they don't need to be attached anymore.
		# no idea  why they even are, if they don't have to..
		gl.glDetachShader(shaderProgram, s)

	return shaderProgram

def BlockSize(prog, blockIndex):
	# a ctypes array, not [0]: PyOpenGL accepts a list and leaves it at 0
	blockSize = (ctypes.c_int * 1)()
	gl.glGetActiveUniformBlockiv(prog, blockIndex, gl.GL_UNIFORM_BLOCK_DATA_SIZE, blockSize)
	return blockSize[0]

def initShader3D(shaderInfo, vertSrc, fragSrc): # from Yamagi

	shaderInfo.shaderProgram = 0
	shaderInfo.uniLmScalesOrTime = -1
	shaderInfo.uniVblend = -1

	# each 3D shader is the common part (attributes, uni3D) plus its own main()
	vs = CompileShader(gl.GL_VERTEX_SHADER, vertexCommon3D, vertSrc)
	if vs == 0:
		return False

	fs = CompileShader(gl.GL_FRAGMENT_SHADER, fragmentCommon3D, fragSrc)
	if fs == 0:
		gl.glDeleteShader(vs)
		return False

	prog = CreateShaderProgram([vs, fs])
	gl.glDeleteShader(vs)
	gl.glDeleteShader(fs)
	if prog == 0:
		return False

	gl.glUseProgram(prog)

	# Bind the buffer object to the uniform blocks. The size check matters:
	# if the C struct and the std140 layout disagree, nothing else complains.
	for name, size, bindingPoint, required in (
			("uniCommon", gl3state.uniCommonData.nbytes, GL3_BINDINGPOINT_UNICOMMON, True),
			("uni3D", gl3state.uni3DData.nbytes, GL3_BINDINGPOINT_UNI3D, True),
			# as uniLights is only used in the LM shaders, it's ok if it's missing
			("uniLights", gl3state.uniLightsData.nbytes, GL3_BINDINGPOINT_UNILIGHTS, False)):
		blockIndex = gl.glGetUniformBlockIndex(prog, name)
		if blockIndex != gl.GL_INVALID_INDEX:
			blockSize = BlockSize(prog, blockIndex)
			if blockSize != size:
				print("WARNING: OpenGL driver disagrees with us about UBO size of '{}'".format(name))
				print("         driver says {}, we expect {}".format(blockSize, size))
				gl.glDeleteProgram(prog)
				return False

			gl.glUniformBlockBinding(prog, blockIndex, bindingPoint)
		elif required:
			print("WARNING: Couldn't find uniform block index '{}'".format(name))
			gl.glDeleteProgram(prog)
			return False

	# make sure texture is GL_TEXTURE0
	# (glUniform* sets a value in the program that is in use, hence the
	# glUseProgram above)
	texLoc = gl.glGetUniformLocation(prog, "tex")
	if texLoc != -1:
		gl.glUniform1i(texLoc, 0)

	# ..  and the 4 lightmap texture use GL_TEXTURE1..4
	for i in range(4):
		lmLoc = gl.glGetUniformLocation(prog, "lightmap{}".format(i))
		if lmLoc != -1:
			gl.glUniform1i(lmLoc, i+1) # lightmap0 belongs to GL_TEXTURE1, lightmap1 to GL_TEXTURE2 etc

	lmScalesLoc = gl.glGetUniformLocation(prog, "lmScales")
	shaderInfo.uniLmScalesOrTime = lmScalesLoc
	if lmScalesLoc != -1:
		shaderInfo.lmScales[:] = 0.0
		shaderInfo.lmScales[0] = (1.0, 1.0, 1.0, 1.0)

		gl.glUniform4fv(lmScalesLoc, 4, shaderInfo.lmScales)

	shaderInfo.shaderProgram = prog

	return True

def initUBOs(): # from Yamagi
	gl3state.uniCommonData[0] = 1.0/vid_gamma # gamma
	gl3state.uniCommonData[1] = gl3_intensity # intensity
	gl3state.uniCommonData[2] = gl3_intensity_2D # intensity2D
	gl3state.uniCommonData[4:8] = (1, 1, 1, 1) # color (after the padding float)

	gl3state.uniCommonUBO = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, gl3state.uniCommonUBO)
	gl.glBindBufferBase(gl.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNICOMMON, gl3state.uniCommonUBO)
	gl.glBufferData(gl.GL_UNIFORM_BUFFER, gl3state.uniCommonData.nbytes, gl3state.uniCommonData, gl.GL_DYNAMIC_DRAW)

	# (uni2D, binding point 1, is only used by the 2D shaders, which this example leaves out)

	# the matrices will be set to something more useful later, before being used
	SetTransMat(U3D_TRANSPROJVIEW, HMM_Mat4d(0.0))
	SetTransMat(U3D_TRANSMODEL, gl3_identityMat4)
	gl3state.uni3DData[U3D_SCROLL] = 0.0
	gl3state.uni3DData[U3D_TIME] = 0.0
	gl3state.uni3DData[U3D_ALPHA] = 1.0
	# gl3_overbrightbits 0 means "no scaling" which is equivalent to multiplying with 1
	gl3state.uni3DData[U3D_OVERBRIGHTBITS] = 1.0 if gl3_overbrightbits <= 0.0 else gl3_overbrightbits
	gl3state.uni3DData[U3D_PARTICLEFADEFACTOR] = gl3_particle_fade_factor
	gl3state.uni3DData[U3D_LIGHTSCALEFORTURB] = 1.0

	gl3state.uni3DUBO = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, gl3state.uni3DUBO)
	gl.glBindBufferBase(gl.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNI3D, gl3state.uni3DUBO)
	gl.glBufferData(gl.GL_UNIFORM_BUFFER, gl3state.uni3DData.nbytes, gl3state.uni3DData, gl.GL_DYNAMIC_DRAW)

	gl3state.uniLightsUBO = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, gl3state.uniLightsUBO)
	gl.glBindBufferBase(gl.GL_UNIFORM_BUFFER, GL3_BINDINGPOINT_UNILIGHTS, gl3state.uniLightsUBO)
	gl.glBufferData(gl.GL_UNIFORM_BUFFER, gl3state.uniLightsData.nbytes, gl3state.uniLightsData, gl.GL_DYNAMIC_DRAW)

	gl3state.currentUBO = gl3state.uniLightsUBO

def updateUBO(ubo, data): # from Yamagi
	# glBindBuffer(GL_UNIFORM_BUFFER) is only needed to name the buffer
	# glBufferData writes to; the shaders read through glBindBufferBase above
	if gl3state.currentUBO != ubo:
		gl3state.currentUBO = ubo
		gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, ubo)

	gl.glBufferData(gl.GL_UNIFORM_BUFFER, data.nbytes, data, gl.GL_DYNAMIC_DRAW)

def GL3_UpdateUBOCommon():
	updateUBO(gl3state.uniCommonUBO, gl3state.uniCommonData)

def GL3_UpdateUBO3D():
	updateUBO(gl3state.uni3DUBO, gl3state.uni3DData)

def GL3_UpdateUBOLights():
	updateUBO(gl3state.uniLightsUBO, gl3state.uniLightsData)

def UpdateLMscales(lmScales, si): # from Yamagi (gl3_main.c)
	# lmScales is a plain uniform, so each program keeps its own copy, and
	# glUniform4fv only reaches the program that is in use
	if not np.array_equal(si.lmScales, lmScales):
		si.lmScales[:] = lmScales
		gl.glUniform4fv(si.uniLmScalesOrTime, MAX_LIGHTMAPS_PER_SURFACE, si.lmScales)

def createShaders(): # from Yamagi, the 3D part
	for si, vs, fs, what in (
			(gl3state.si3Dlm, vertexSrc3Dlm, fragmentSrc3Dlm, "textured 3D rendering with lightmap"),
			(gl3state.si3Dtrans, vertexSrc3D, fragmentSrc3D, "rendering translucent 3D things"),
			(gl3state.si3DcolorOnly, vertexSrc3D, fragmentSrc3Dcolor, "flat-colored 3D rendering"),
			(gl3state.si3Dturb, vertexSrc3Dwater, fragmentSrc3Dwater, "water rendering"),
			(gl3state.si3DlmFlow, vertexSrc3DlmFlow, fragmentSrc3Dlm, "scrolling textured 3D rendering with lightmap"),
			(gl3state.si3Dsky, vertexSrc3D, fragmentSrc3Dsky, "sky rendering"),
			(gl3state.si3DspriteAlpha, vertexSrc3D, fragmentSrc3DspriteAlpha, "alpha-tested sprite rendering"),
			(gl3state.si3Dalias, vertexSrcAlias, fragmentSrcAlias, "rendering textured models"),
			(gl3state.si3DaliasColor, vertexSrcAlias, fragmentSrcAliasColor, "rendering flat-colored models"),
			(gl3state.siParticle, vertexSrcParticles, fragmentSrcParticles, "rendering particles")):
		if not initShader3D(si, vs, fs):
			raise RuntimeError("Failed to create shader program for {}!".format(what))

#=============================================================================
#Vertex layouts, from GL3_SurfInit (gl3_surf.c)
#=============================================================================
#A VAO remembers which attributes are enabled, which VBO each one reads, its
#format and its offset. It is set up once and only bound later. The element
#(index) buffer binding is part of the VAO too.

def GL3_SurfInit():
	# init the VAO and VBO for the standard vertexdata: 10 floats and 1 uint
	# (X, Y, Z), (S, T), (LMS, LMT), (normX, normY, normZ) ; lightFlags - last two groups for lightmap/dynlights
	gl3state.vao3D = gl.glGenVertexArrays(1)
	gl.glBindVertexArray(gl3state.vao3D)

	gl3state.vbo3D = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vbo3D)

	stride = gl3_3D_vtx_t.itemsize # 44
	gl.glEnableVertexAttribArray(GL3_ATTRIB_POSITION)
	gl.glVertexAttribPointer(GL3_ATTRIB_POSITION, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, offsetof(gl3_3D_vtx_t, "pos"))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_TEXCOORD)
	gl.glVertexAttribPointer(GL3_ATTRIB_TEXCOORD, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, offsetof(gl3_3D_vtx_t, "texCoord"))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_LMTEXCOORD)
	gl.glVertexAttribPointer(GL3_ATTRIB_LMTEXCOORD, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, offsetof(gl3_3D_vtx_t, "lmTexCoord"))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_NORMAL)
	gl.glVertexAttribPointer(GL3_ATTRIB_NORMAL, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, offsetof(gl3_3D_vtx_t, "normal"))

	# "in uint lightFlags": the I variant keeps it an integer
	gl.glEnableVertexAttribArray(GL3_ATTRIB_LIGHTFLAGS)
	gl.glVertexAttribIPointer(GL3_ATTRIB_LIGHTFLAGS, 1, gl.GL_UNSIGNED_INT, stride, offsetof(gl3_3D_vtx_t, "lightFlags"))

	gl3state.ebo3D = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, gl3state.ebo3D) # (stored in vao3D)

	# init VAO and VBO for model vertexdata: 9 floats
	# (X,Y,Z), (S,T), (R,G,B,A)
	gl3state.vaoAlias = gl.glGenVertexArrays(1)
	gl.glBindVertexArray(gl3state.vaoAlias)

	gl3state.vboAlias = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vboAlias)

	gl.glEnableVertexAttribArray(GL3_ATTRIB_POSITION)
	gl.glVertexAttribPointer(GL3_ATTRIB_POSITION, 3, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(0))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_TEXCOORD)
	gl.glVertexAttribPointer(GL3_ATTRIB_TEXCOORD, 2, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(3*4))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_COLOR)
	gl.glVertexAttribPointer(GL3_ATTRIB_COLOR, 4, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(5*4))

	gl3state.eboAlias = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, gl3state.eboAlias) # (stored in vaoAlias)

	# init VAO and VBO for particle vertexdata: 9 floats
	# (X,Y,Z), (point_size,distace_to_camera), (R,G,B,A)
	gl3state.vaoParticle = gl.glGenVertexArrays(1)
	gl.glBindVertexArray(gl3state.vaoParticle)

	gl3state.vboParticle = gl.glGenBuffers(1)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vboParticle)

	gl.glEnableVertexAttribArray(GL3_ATTRIB_POSITION)
	gl.glVertexAttribPointer(GL3_ATTRIB_POSITION, 3, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(0))

	# TODO: maybe move point size and camera origin to UBO and calculate distance in vertex shader
	gl.glEnableVertexAttribArray(GL3_ATTRIB_TEXCOORD) # it's abused for (point_size, distance) here..
	gl.glVertexAttribPointer(GL3_ATTRIB_TEXCOORD, 2, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(3*4))

	gl.glEnableVertexAttribArray(GL3_ATTRIB_COLOR)
	gl.glVertexAttribPointer(GL3_ATTRIB_COLOR, 4, gl.GL_FLOAT, gl.GL_FALSE, 9*4, ctypes.c_void_p(5*4))

	gl.glBindVertexArray(0)

#=============================================================================
#Textures (all RGBA, like GL3_Upload32)
#=============================================================================

def UploadTexture(rgba, mipmap=True, clamp=False, nearest=False):
	# rgba: (height, width, 4) uint8, first row at the top (as q2 images are,
	# so t = 0 is the top of the image)
	h, w = rgba.shape[:2]
	texnum = gl.glGenTextures(1)
	gl.glBindTexture(gl.GL_TEXTURE_2D, texnum)
	# RGBA rows are always a multiple of 4 bytes. With GL_RGB data the default
	# GL_UNPACK_ALIGNMENT of 4 would skew any image whose width*3 isn't.
	gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, np.ascontiguousarray(rgba))
	if mipmap:
		gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
		# gl_texturemode's default; a mipmapped filter on a texture without
		# mipmaps would read as black
		gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_NEAREST)
	else:
		gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR)
	gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR)
	# GL_CLAMP is not in a core profile; GL_CLAMP_TO_EDGE is what q2 uses for the sky
	wrap = gl.GL_CLAMP_TO_EDGE if clamp else gl.GL_REPEAT
	gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap)
	gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap)
	return texnum

def LoadImage(name, size):
	img = Image.open(os.path.join(HERE, name)).convert("RGBA").resize((size, size), Image.LANCZOS)
	return np.array(img, dtype=np.uint8)

def MakeWaterImage():
	# 64x64, like a q2 water texture (the water shader assumes 64 world units
	# per texture)
	y, x = np.mgrid[0:64, 0:64] / 64.0 * 2.0 * math.pi
	v = 0.5 + 0.25 * np.sin(x * 2 + np.sin(y * 3)) + 0.25 * np.sin(y * 2 + np.sin(x))
	rgba = np.zeros((64, 64, 4), dtype=np.uint8)
	rgba[..., 0] = 20 + 40 * v
	rgba[..., 1] = 60 + 70 * v
	rgba[..., 2] = 110 + 100 * v
	rgba[..., 3] = 255
	return rgba

def MakeStarsImage():
	rng = np.random.RandomState(1)
	rgba = np.zeros((256, 256, 4), dtype=np.uint8)
	rgba[..., 2] = 12 # a little blue in the black
	rgba[..., 3] = 255
	for _ in range(220):
		x, y = rng.randint(0, 256, 2)
		b = rng.randint(90, 256)
		rgba[y, x, 0:3] = (b, b, min(255, b + 30))
	return rgba

def MakeHolesImage(rgba):
	# for the alpha tested cube: a grid of round holes with alpha 0
	h, w = rgba.shape[:2]
	y, x = np.mgrid[0:h, 0:w]
	cell = w // 4
	dx = (x % cell) - cell / 2.0
	dy = (y % cell) - cell / 2.0
	out = rgba.copy()
	out[..., 3] = np.where(dx * dx + dy * dy < (cell * 0.3) ** 2, 0, 255)
	return out

#=============================================================================
#Geometry: cubes
#=============================================================================

CUBE_HALF = 24 # 48 units wide, about the size of a q2 crate

def CubeFaces(half):
	# Returns the 6 faces as (normal, 4 corners, s axis, t axis). The corners
	# are clockwise seen from outside, because q2 culls with
	# glCullFace(GL_FRONT): in q2 the front face is the clockwise one. s goes
	# to the right and t downwards when you look at the face, as on a q2 wall.
	faces = []
	up = np.array((0.0, 0.0, 1.0))
	for axis in range(3):
		for sign in (1.0, -1.0):
			n = np.zeros(3)
			n[axis] = sign
			if axis == 2:
				s_axis = np.array((0.0, -sign, 0.0)) # any axis in the face plane
				t_axis = np.array((-1.0, 0.0, 0.0))
			else:
				s_axis = np.cross(n, up)
				t_axis = -up
			c = n * half
			corners = [c + (-s_axis - t_axis) * half, c + (s_axis - t_axis) * half,
				c + (s_axis + t_axis) * half, c + (-s_axis + t_axis) * half]
			# clockwise seen from outside means the cross product points inwards
			if np.dot(np.cross(corners[1] - corners[0], corners[2] - corners[0]), n) > 0:
				corners.reverse()
			faces.append((n, corners, s_axis, t_axis))
	return faces

class Lightmap(object):
	# the lightmap atlas, one texture per light style slot
	# (gl3state.lightmap_textureIDs[lmtex][0..3] in Yamagi)

	def __init__(self):
		self.data = np.zeros((MAX_LIGHTMAPS_PER_SURFACE, BLOCK_HEIGHT, BLOCK_WIDTH, 4), dtype=np.uint8)
		self.data[..., 3] = 255
		self.next_s, self.next_t, self.row_height = 0, 0, 0
		self.texnums = []

	def AllocBlock(self, smax, tmax):
		# a shelf allocator standing in for LM_AllocBlock: left to right, then
		# a new row (with a luxel of space around each block)
		if self.next_s + smax > BLOCK_WIDTH:
			self.next_s = 0
			self.next_t += self.row_height + 1
			self.row_height = 0
		if self.next_t + tmax > BLOCK_HEIGHT:
			raise RuntimeError("lightmap atlas full")
		s, t = self.next_s, self.next_t
		self.next_s += smax + 1
		self.row_height = max(self.row_height, tmax)
		return s, t

	def Upload(self):
		for slot in range(MAX_LIGHTMAPS_PER_SURFACE):
			# lightmaps are GL_LINEAR without mipmaps, so the luxels blend
			self.texnums.append(UploadTexture(self.data[slot], mipmap=False, clamp=True))

# static lights, baked into the lightmaps as qrad would (much simplified):
# (position in the cube's own coordinates, value, colour, light style)
STATIC_LIGHTS = [
	(np.array((60.0, 50.0, 70.0)), 150.0, np.array((1.0, 1.0, 1.0)), 0),
	(np.array((-40.0, -70.0, -30.0)), 130.0, np.array((1.0, 0.55, 0.2)), 5),
]
AMBIENT = 0.1

def BakeLuxel(p, n, style):
	v = AMBIENT * np.ones(3) if style == 0 else np.zeros(3)
	for origin, value, colour, lstyle in STATIC_LIGHTS:
		if lstyle != style:
			continue
		d = origin - p
		dist = np.linalg.norm(d)
		angle = max(0.0, np.dot(n, d / dist))
		v += colour * max(0.0, value - dist) / 128.0 * angle
	return np.clip(v, 0.0, 1.0)

def BuildLightmappedCube(lm, styles, lightFlags):
	# Brush-style vertices (gl3_3D_vtx_t) for a cube, with a lightmap block per
	# face. styles are the light styles of the face's 4 lightmap slots (255 =
	# unused), as msurface_t.styles.
	verts = []
	for n, corners, s_axis, t_axis in CubeFaces(CUBE_HALF):
		# GL3_CalcSurfaceExtents: s and t of the corners, in world units
		st = [(np.dot(c, s_axis), np.dot(c, t_axis)) for c in corners]
		texturemins = [math.floor(min(x[i] for x in st) / 16) * 16 for i in range(2)]
		extents = [math.ceil(max(x[i] for x in st) / 16) * 16 - texturemins[i] for i in range(2)]
		smax, tmax = extents[0] // 16 + 1, extents[1] // 16 + 1 # one luxel per 16 units, plus one
		light_s, light_t = lm.AllocBlock(smax, tmax)

		# the lightmap data, one block per style slot (q2 reads it from the BSP)
		for slot, style in enumerate(styles):
			if style == 255:
				continue
			for j in range(tmax):
				for i in range(smax):
					p = (texturemins[0] + i * 16) * s_axis + (texturemins[1] + j * 16) * t_axis + CUBE_HALF * n
					lm.data[slot, light_t + j, light_s + i, 0:3] = BakeLuxel(p, n, style) * 255

		for c, (s, t) in zip(corners, st):
			v = np.zeros((), dtype=gl3_3D_vtx_t)
			v["pos"] = c
			# brush texture coordinates are in texture repeats (here one
			# texture across each face)
			v["texCoord"] = ((s - texturemins[0]) / extents[0], (t - texturemins[1]) / extents[1])
			# GL3_LM_BuildPolygonFromSurface: lightmap coordinates hit luxel centres
			v["lmTexCoord"] = ((s - texturemins[0] + light_s * 16 + 8) / (BLOCK_WIDTH * 16),
				(t - texturemins[1] + light_t * 16 + 8) / (BLOCK_HEIGHT * 16))
			v["normal"] = n
			v["lightFlags"] = lightFlags
			verts.append(v)
	return np.array(verts, dtype=gl3_3D_vtx_t)

def BuildCube3D(texscale=1.0, half=CUBE_HALF):
	# gl3_3D_vtx_t vertices for a cube without lightmap. texscale 64 gives the
	# water shader the world-unit texture coordinates it expects.
	verts = []
	for n, corners, s_axis, t_axis in CubeFaces(half):
		for c in corners:
			v = np.zeros((), dtype=gl3_3D_vtx_t)
			v["pos"] = c
			v["texCoord"] = ((np.dot(c, s_axis) / half + 1) / 2 * texscale, (np.dot(c, t_axis) / half + 1) / 2 * texscale)
			v["normal"] = n
			verts.append(v)
	return np.array(verts, dtype=gl3_3D_vtx_t)

def FanIndices(numfaces):
	# each face is a 4 vertex GL_TRIANGLE_FAN; as GL_TRIANGLES that is
	# (0,1,2) (0,2,3), the same as Yamagi's batching makes of fans
	idx = []
	for f in range(numfaces):
		b = f * 4
		idx += [b, b + 1, b + 2, b, b + 2, b + 3]
	return np.array(idx, dtype=np.uint16)

def ModelFrames():
	# two "md2 frames" of a 24 vertex cube: a cube and a squashed one. q2
	# stores frame vertices as bytes with a per-frame scale and translate, and
	# a normal index into a table of 162 normals; here they are plain floats.
	frames = []
	for scale in ((1.0, 1.0, 1.0), (1.3, 1.3, 0.6)):
		pos, normals, st = [], [], []
		for n, corners, s_axis, t_axis in CubeFaces(CUBE_HALF):
			for c in corners:
				pos.append(c * scale)
				normals.append(n)
				st.append(((np.dot(c, s_axis) / CUBE_HALF + 1) / 2, (np.dot(c, t_axis) / CUBE_HALF + 1) / 2))
		frames.append((np.array(pos, dtype=np.float32), np.array(normals, dtype=np.float32)))
	return frames, np.array(st, dtype=np.float32)

#=============================================================================
#The scene
#=============================================================================

class entity_t(object):

	def __init__(self, name, origin, shader):

		self.name = name
		self.origin = np.array(origin, dtype=np.float32) #vec3_t
		self.angles = np.zeros(3, dtype=np.float32) #vec3_t, pitch yaw roll
		self.shader = shader #gl3ShaderInfo_t
		self.texnum = 0
		self.verts = None # gl3_3D_vtx_t array
		self.indices = None # GLushort array, for GL_TRIANGLES
		self.styles = (255, 255, 255, 255)

# the viewer, in q2 coordinates (X forward, Y left, Z up)
vieworg = np.array((0.0, 0.0, 0.0), dtype=np.float32)
viewangles = np.array((0.0, 0.0, 0.0), dtype=np.float32) # pitch, yaw, roll

# two dynamic lights (dlight_t: origin, color, intensity), placed between the
# lightmapped cubes. They don't move.
dlights = [
	(np.array((180.0, 130.0, 85.0)), np.array((1.0, 0.25, 0.1)), 200.0),
	(np.array((180.0, 0.0, 45.0)), np.array((0.2, 0.4, 1.0)), 200.0),
]

def init():
	versionString = gl.glGetString(gl.GL_VERSION).split(b" ")
	openglVersionNums = list(map(int, versionString[0].split(b".")[:2]))
	if openglVersionNums < [3, 2]:
		exit("Requires opengl 3.2 or better, you have {0}".format(versionString[0]))

	# GL3_SetDefaultState, the parts that matter here
	gl.glClearColor(1, 0, 0.5, 0.5) # GL3_ResetClearColor: pink, so gaps show
	gl.glDepthFunc(gl.GL_LEQUAL)
	gl.glDepthRange(0.0, 1.0)
	gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

	GL3_SurfInit()
	initUBOs()
	createShaders()

	# light styles for each surface slot and the dlights, as the client sends them
	lightsData = gl3state.uniLightsData
	for i, (origin, color, intensity) in enumerate(dlights):
		lightsData[i * 8:i * 8 + 3] = origin
		lightsData[i * 8 + 4:i * 8 + 7] = color
		lightsData[i * 8 + 7] = intensity
	# numDynLights is a GLuint in the middle of the floats
	lightsData.view(np.uint32)[MAX_DLIGHTS * 8] = len(dlights)
	GL3_UpdateUBOLights()

	brick = LoadImage("brick-texture.jpg", 128)
	brick_tex = UploadTexture(brick)
	water_tex = UploadTexture(MakeWaterImage())
	skin_tex = UploadTexture(LoadImage("butterfly.JPG", 128))
	# alpha tested: no mipmaps (they would smear the holes' alpha), like
	# q2's 2D pics and sprites with GL_LINEAR
	holes_tex = UploadTexture(MakeHolesImage(LoadImage("butterfly.JPG", 128)), mipmap=False)
	stars_tex = UploadTexture(MakeStarsImage(), clamp=True)

	lm = Lightmap()
	ents = []
	top, bottom = 45.0, -45.0
	columns = (150.0, 50.0, -50.0, -150.0) # y, from left to right
	dist = 220.0 # x

	e = entity_t("lightmapped", (dist, columns[0], top), gl3state.si3Dlm)
	e.styles = (0, 5, 255, 255)
	e.verts, e.indices = BuildLightmappedCube(lm, e.styles, (1 << len(dlights)) - 1), FanIndices(6)
	e.texnum = brick_tex
	ents.append(e)

	e = entity_t("flowing", (dist, columns[1], top), gl3state.si3DlmFlow)
	e.styles = (0, 255, 255, 255)
	e.verts, e.indices = BuildLightmappedCube(lm, e.styles, (1 << len(dlights)) - 1), FanIndices(6)
	e.texnum = brick_tex
	ents.append(e)

	e = entity_t("water", (dist, columns[2], top), gl3state.si3Dturb)
	e.verts, e.indices = BuildCube3D(texscale=CUBE_HALF * 2), FanIndices(6)
	e.texnum = water_tex
	ents.append(e)

	e = entity_t("glass", (dist, columns[3], top), gl3state.si3Dtrans)
	e.verts, e.indices = BuildCube3D(), FanIndices(6)
	e.texnum = brick_tex
	ents.append(e)

	e = entity_t("model", (dist, columns[0], bottom), gl3state.si3Dalias)
	e.texnum = skin_tex
	ents.append(e)

	e = entity_t("shell", (dist, columns[1], bottom), gl3state.si3DaliasColor)
	ents.append(e)

	e = entity_t("beam", (dist, columns[2], bottom), gl3state.si3DcolorOnly)
	e.verts, e.indices = BuildCube3D(half=CUBE_HALF * 0.6), FanIndices(6)
	ents.append(e)

	e = entity_t("sprite", (dist, columns[3], bottom), gl3state.si3DspriteAlpha)
	e.verts, e.indices = BuildCube3D(), FanIndices(6)
	e.texnum = holes_tex
	ents.append(e)

	lm.Upload()

	# the sky box: GL3_DrawSkyBox puts its faces 2300 units from the viewer
	sky = entity_t("sky", (0, 0, 0), gl3state.si3Dsky)
	sky_verts = BuildCube3D(half=2300)
	# seen from inside, so the winding must be reversed (clockwise seen from
	# the viewer)
	sky_verts = sky_verts.reshape(6, 4)[:, ::-1].reshape(24).copy()
	sky.verts, sky.indices = sky_verts, FanIndices(6)
	sky.texnum = stars_tex

	frames, st = ModelFrames()

	gl.glBindVertexArray(0)

	return {"ents": ents, "sky": sky, "lightmap": lm, "frames": frames, "st": st,
		"t0": time.time()}

#=============================================================================
#Drawing
#=============================================================================

def SetupGL(width, height, t): # from Yamagi, the parts for the 3D view
	gl.glViewport(0, 0, width, height)

	# set up projection matrix (eye coordinates -> clip coordinates)
	gl3state.projMat3D = GL3_SetPerspective(CalcFov(fov, width, height), width, height)

	gl.glCullFace(gl.GL_FRONT)

	# set up view matrix (world coordinates -> eye coordinates)
	# first put Z axis going up
	viewMat = np.array([
		[  0, 0, -1, 0 ], # first *column* (the matrix is column-major)
		[ -1, 0,  0, 0 ],
		[  0, 1,  0, 0 ],
		[  0, 0,  0, 1 ]
	], dtype=np.float32)

	# now rotate by view angles
	rotMat = rotAroundAxisXYZ(-viewangles[2], -viewangles[0], -viewangles[1])

	viewMat = HMM_MultiplyMat4(viewMat, rotMat)

	# .. and apply translation for current position
	trans = -vieworg
	viewMat = HMM_MultiplyMat4(viewMat, HMM_Translate(trans))

	gl3state.viewMat3D = viewMat

	# just use one projection-view-matrix (premultiplied here)
	# so we have one less mat4 multiplication in the 3D shaders
	SetTransMat(U3D_TRANSPROJVIEW, HMM_MultiplyMat4(gl3state.projMat3D, gl3state.viewMat3D))

	SetTransMat(U3D_TRANSMODEL, gl3_identityMat4)

	gl3state.uni3DData[U3D_TIME] = t # r_newrefdef.time, in seconds

	GL3_UpdateUBO3D()

	# set drawing parms (r_cull 1)
	gl.glEnable(gl.GL_CULL_FACE)
	gl.glEnable(gl.GL_DEPTH_TEST)

def BindLightmaps(lm):
	# GL3_BindLightmap: the four style slots on texture units 1..4
	for i in range(MAX_LIGHTMAPS_PER_SURFACE):
		gl.glActiveTexture(gl.GL_TEXTURE1 + i)
		gl.glBindTexture(gl.GL_TEXTURE_2D, lm.texnums[i])
	gl.glActiveTexture(gl.GL_TEXTURE0)

def DrawStatic(e):
	# GL3_Draw3DBatchesNow, for one cube: the vertices go into the one vbo3D
	# with GL_STREAM_DRAW every time they are drawn, the indices into ebo3D
	# (whose binding is stored in vao3D), then one glDrawElements
	gl.glBindVertexArray(gl3state.vao3D)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vbo3D)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, e.verts.nbytes, e.verts.view(np.uint8), gl.GL_STREAM_DRAW)
	gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, e.indices.nbytes, e.indices, gl.GL_STREAM_DRAW)
	# the index offset is a pointer too: c_void_p, not 0
	gl.glDrawElements(gl.GL_TRIANGLES, len(e.indices), gl.GL_UNSIGNED_SHORT, ctypes.c_void_p(0))

def SetModel(e):
	SetTransMat(U3D_TRANSMODEL, GL3_RotateForEntity(e.angles, e.origin))
	GL3_UpdateUBO3D()

def DrawBrushCube(e, lm, t):
	# a brush entity (like a rotating door): its own model matrix, the
	# world's shaders
	gl.glUseProgram(e.shader.shaderProgram)
	SetModel(e)

	if e.shader is gl3state.si3DlmFlow:
		# GL3_DrawGLFlowingPoly: one texture width every 40/64 seconds
		scroll = -64.0 * ((t / 40.0) - int(t / 40.0))
		if scroll == 0.0:
			scroll = -64.0
		gl3state.uni3DData[U3D_SCROLL] = scroll
		GL3_UpdateUBO3D()

	# lmScales from the light styles of the surface's 4 slots
	lmScales = np.zeros((4, 4), dtype=np.float32)
	lmScales[0] = (1.0, 1.0, 1.0, 1.0)
	for slot, style in enumerate(e.styles):
		if style == 255:
			break
		v = LightStyleValue(style)
		lmScales[slot] = (v, v, v, 1.0)
	UpdateLMscales(lmScales, e.shader)

	gl.glActiveTexture(gl.GL_TEXTURE0)
	gl.glBindTexture(gl.GL_TEXTURE_2D, e.texnum)
	BindLightmaps(lm)
	DrawStatic(e)

def DrawAliasCube(e, frames, st, backlerp, shadelight, colorOnly=False, alpha=1.0):
	# DrawAliasFrameLerp: q2 lerps model vertices on the CPU every frame and
	# streams them with GL_STREAM_DRAW; the shader only gets the result
	frontlerp = 1.0 - backlerp
	(newpos, newnormals), (oldpos, _) = frames[1], frames[0]
	pos = backlerp * oldpos + frontlerp * newpos

	# shadedots: q2 uses r_avertexnormal_dots[yaw quantised to 16 steps][normal
	# index]. That table holds about this: a light coming from a fixed side
	# relative to the model's yaw, back faces darker.
	yaw = math.radians(int(e.angles[1] * (16 / 360.0)) * (360.0 / 16))
	shadevector = np.array((math.cos(-yaw), math.sin(-yaw), 1.0))
	shadevector /= np.linalg.norm(shadevector)
	dots = newnormals @ shadevector
	dots = np.where(dots < 0, dots * 0.3, dots) + 1.0

	verts = np.zeros(len(pos), dtype=gl3_alias_vtx_t)
	verts["pos"] = pos
	verts["texCoord"] = st
	if colorOnly:
		# shells (RF_SHELL_*) are flat: just shadelight, no shadedots
		verts["color"][:, 0:3] = shadelight
	else:
		verts["color"][:, 0:3] = dots[:, None] * shadelight
	verts["color"][:, 3] = alpha

	shader = gl3state.si3DaliasColor if colorOnly else gl3state.si3Dalias
	gl.glUseProgram(shader.shaderProgram)
	SetModel(e)
	if alpha < 1.0:
		gl3state.uni3DData[U3D_ALPHA] = alpha
		GL3_UpdateUBO3D()

	gl.glActiveTexture(gl.GL_TEXTURE0)
	gl.glBindTexture(gl.GL_TEXTURE_2D, e.texnum)

	gl.glBindVertexArray(gl3state.vaoAlias)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vboAlias)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, verts.nbytes, verts.view(np.uint8), gl.GL_STREAM_DRAW)
	indices = FanIndices(6)
	gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STREAM_DRAW) # eboAlias, bound in the VAO
	gl.glDrawElements(gl.GL_TRIANGLES, len(indices), gl.GL_UNSIGNED_SHORT, ctypes.c_void_p(0))

	if alpha < 1.0:
		gl3state.uni3DData[U3D_ALPHA] = 1.0
		GL3_UpdateUBO3D()

def DrawParticles(height, t):
	# GL3_DrawParticles. A ring of particles around the cubes, and one at each
	# dynamic light so you can see where they are.
	n = 96
	a = np.arange(n) * (2 * math.pi / n) + t * 0.4
	origins = np.zeros((n + len(dlights), 3), dtype=np.float32)
	origins[:n, 0] = 220 + 110 * np.cos(a)
	origins[:n, 1] = 200 * np.sin(a)
	origins[:n, 2] = -70 * np.cos(a) # tilted, so the ring is not seen edge on
	colors = np.zeros((len(origins), 4), dtype=np.float32)
	colors[:n] = (1.0, 0.85, 0.3, 1.0) # in q2: d_8to24table[p->color]
	colors[:n, 3] = 0.6 + 0.4 * np.sin(a * 3) # p->alpha
	for i, (origin, color, intensity) in enumerate(dlights):
		origins[n + i] = origin
		colors[n + i, 0:3] = color
		colors[n + i, 3] = 1.0

	# assume the size looks good with window height 480px and scale according to real resolution
	pointSize = gl3_particle_size * height / 480.0

	buf = np.zeros(len(origins), dtype=gl3_alias_vtx_t) # part_vtx has the same 9 floats
	buf["pos"] = origins
	buf["texCoord"][:, 0] = pointSize # cur->size
	buf["texCoord"][:, 1] = np.linalg.norm(vieworg - origins, axis=1) # cur->dist
	buf["color"] = colors

	gl.glDepthMask(gl.GL_FALSE)
	gl.glEnable(gl.GL_BLEND)
	# luckily we don't use glPointSize() but set gl_PointSize in shader anyway
	gl.glEnable(gl.GL_PROGRAM_POINT_SIZE)

	gl.glUseProgram(gl3state.siParticle.shaderProgram)

	gl.glBindVertexArray(gl3state.vaoParticle)
	gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl3state.vboParticle)
	gl.glBufferData(gl.GL_ARRAY_BUFFER, buf.nbytes, buf.view(np.uint8), gl.GL_STREAM_DRAW)
	gl.glDrawArrays(gl.GL_POINTS, 0, len(buf))

	gl.glDisable(gl.GL_BLEND)
	gl.glDepthMask(gl.GL_TRUE)
	gl.glDisable(gl.GL_PROGRAM_POINT_SIZE)

def draw(params, width, height):
	t = time.time() - params["t0"]
	ents = {e.name: e for e in params["ents"]}
	lm = params["lightmap"]

	# the cubes turn; the lighting stays put
	for i, e in enumerate(params["ents"]):
		e.angles[:] = (20.0 * math.sin(t * 0.5 + i), t * 30.0 + i * 40.0, 0.0)

	# GL3_Clear (r_clear 0 would only clear depth: the world covers the screen;
	# here the sky does)
	gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

	SetupGL(width, height, t)

	# GL3_DrawWorld: the sky first (GL3_DrawSkyBox), moved with the viewer
	sky = params["sky"]
	gl.glUseProgram(sky.shader.shaderProgram)
	SetTransMat(U3D_TRANSMODEL, HMM_Translate(vieworg))
	GL3_UpdateUBO3D()
	gl.glActiveTexture(gl.GL_TEXTURE0)
	gl.glBindTexture(gl.GL_TEXTURE_2D, sky.texnum)
	DrawStatic(sky)

	# opaque brush surfaces with lightmaps
	DrawBrushCube(ents["lightmapped"], lm, t)
	DrawBrushCube(ents["flowing"], lm, t)

	# GL3_DrawEntitiesOnList, opaque entities first
	backlerp = 0.5 + 0.5 * math.sin(t * 2.0) # between two frames, as the client lerps them
	DrawAliasCube(ents["model"], params["frames"], params["st"], backlerp, np.array((0.8, 0.75, 0.7)))

	e = ents["sprite"]
	gl.glUseProgram(e.shader.shaderProgram)
	SetModel(e)
	gl.glActiveTexture(gl.GL_TEXTURE0)
	gl.glBindTexture(gl.GL_TEXTURE_2D, e.texnum)
	gl.glDisable(gl.GL_CULL_FACE) # so the inside shows through the holes
	DrawStatic(e)
	gl.glEnable(gl.GL_CULL_FACE)

	# .. then the translucent ones, without writing depth
	gl.glDepthMask(gl.GL_FALSE)
	gl.glEnable(gl.GL_BLEND)

	# a red shell (RF_SHELL_RED | RF_TRANSLUCENT), alpha 0.33 as q2 uses for shells
	DrawAliasCube(ents["shell"], params["frames"], params["st"], backlerp, np.array((1.0, 0.0, 0.0)),
		colorOnly=True, alpha=0.33)

	# a beam: si3DcolorOnly takes its colour from uniCommon.color
	e = ents["beam"]
	gl.glUseProgram(e.shader.shaderProgram)
	SetModel(e)
	gl3state.uniCommonData[4:8] = (0.2, 1.0, 0.3, 1.0)
	gl3state.uni3DData[U3D_ALPHA] = 0.5
	GL3_UpdateUBOCommon()
	GL3_UpdateUBO3D()
	DrawStatic(e)
	# uniCommon.color is shared with the 2D shaders: put it back
	gl3state.uniCommonData[4:8] = (1, 1, 1, 1)
	gl3state.uni3DData[U3D_ALPHA] = 1.0
	GL3_UpdateUBOCommon()

	gl.glDisable(gl.GL_BLEND)
	gl.glDepthMask(gl.GL_TRUE)

	# transModel stays in uni3D until something changes it. Particles have
	# their positions in world coordinates, so it must be the identity again
	# (as Yamagi restores it after each batch), or the particles are moved and
	# turned along with the last cube drawn
	SetTransMat(U3D_TRANSMODEL, gl3_identityMat4)
	GL3_UpdateUBO3D()

	# GL3_DrawParticles
	DrawParticles(height, t)

	# GL3_DrawAlphaSurfaces: translucent brush surfaces, last, blended
	gl.glEnable(gl.GL_BLEND)

	e = ents["glass"] # SURF_TRANS33
	gl.glUseProgram(e.shader.shaderProgram)
	SetModel(e)
	gl3state.uni3DData[U3D_ALPHA] = 0.333
	GL3_UpdateUBO3D()
	gl.glBindTexture(gl.GL_TEXTURE_2D, e.texnum)
	DrawStatic(e)

	e = ents["water"] # SURF_WARP | SURF_TRANS66
	gl.glUseProgram(e.shader.shaderProgram)
	SetModel(e)
	gl3state.uni3DData[U3D_ALPHA] = 0.666
	# turbulent surfaces have no lightmap; this stands in for it (1 for lava)
	gl3state.uni3DData[U3D_LIGHTSCALEFORTURB] = 0.5
	gl3state.uni3DData[U3D_SCROLL] = 0.0 # (SURF_FLOWING water would scroll too)
	GL3_UpdateUBO3D()
	gl.glBindTexture(gl.GL_TEXTURE_2D, e.texnum)
	DrawStatic(e)

	gl3state.uni3DData[U3D_ALPHA] = 1.0
	gl3state.uni3DData[U3D_LIGHTSCALEFORTURB] = 1.0
	SetTransMat(U3D_TRANSMODEL, gl3_identityMat4)
	GL3_UpdateUBO3D()
	gl.glDisable(gl.GL_BLEND)

	gl.glBindVertexArray(0)
