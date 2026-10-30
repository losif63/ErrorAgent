`/input/video.mp4` is a video of a handheld camera moving through an indoor room.
It is {{duration}} s long: {{frames}} frames at {{fps}} fps, {{width}}x{{height}}.

Your task is to reconstruct the room as an animated Blender scene, written as
Blender Python (bpy), and save it to `/workspace/output/result.blend`.

The video may not show the whole room. Reconstruct the entire room: its walls,
floor and ceiling, and every object in it, including the parts the camera never
shows. Where the video gives no evidence, build what is most plausibly there.

## Looking at the video

You cannot watch the video directly. Extract frames with ffmpeg and open the
image files to look at them, for example:

```bash
mkdir -p /workspace/frames
ffmpeg -loglevel error -ss 12.0 -i /input/video.mp4 -frames:v 1 -vf scale=768:-1 /workspace/frames/t012.0.jpg
```

You decide how many frames to look at and when. Look before you build, and come
back to the video to check details. A scene built without looking at the video
is a failure.

## Blender

Blender {{blender_version}} is installed. Run it headless as
`blender_run --python /workspace/scratch/build.py`, which wraps
`xvfb-run -a blender --background`. Keep your scripts and previews in
`/workspace/scratch`. You may render previews and compare them with frames.

## Scene rules

- Save the final scene to `/workspace/output/result.blend`, for example with
  `bpy.ops.wm.save_as_mainfile(filepath="/workspace/output/result.blend")`.
- Build all geometry from basic primitives (cube, plane, cylinder, cone,
  uv_sphere, torus) and assemblies of them. No imported models, no downloaded
  assets, no sculpting or arbitrary meshes, no geometry nodes, particles,
  physics or image textures.
- Put each physical object's parts in its own Collection, named after the
  object (`chair_1`, `chair_2`, `desk`, `wall_north`, ...). A multi-part object
  (a chair is a seat, a back and legs) is one Collection. A complex object may
  nest its sub-objects as child Collections, to any depth: a `couch` Collection
  can hold the primitives of its frame and one child Collection per cushion
  (`couch_cushion_1`, `couch_cushion_2`, ...).
- Every Collection, at every level, is one distinct object. The primitives
  directly inside a Collection may overlap each other, but distinct objects must
  not: no two Collections may intersect, and neither may a Collection's own
  primitives and its child Collections. Objects may touch (a cushion resting on
  the couch seat, a desk standing on the floor) but not interpenetrate.
- Materials are a single Principled BSDF with numeric values only.
- 1 Blender unit = 1 metre, Z up, Unit Scale 1.0. Rotations in radians.
- Include at least one camera and one light.
- Reproduce object counts, sizes, positions and spatial relationships as
  faithfully as you can.
- Make the scene as physically plausible as you can. Do your best to avoid
  physically implausible errors such as overlapping geometry, objects floating
  in the air instead of resting on a support, and detached parts that should be
  connected (a table top hovering above its legs). Fix these without giving up
  fidelity: the scene, seen through the animated camera, should still match the
  input video as closely as possible.

## Camera

Reconstruct the camera's motion as an animation, not a single viewpoint. Insert
keyframes for the camera's `location` and `rotation_euler` over time, so that
Blender frame `f` matches video frame `f - 1`. Set `frame_start = 1`,
`frame_end = {{frames}}`, the scene frame rate to {{fps}} fps and the render
resolution to {{width}}x{{height}}, and make this camera the scene camera.

You are running unattended and no one will answer questions. Make your own
judgement calls and always deliver `/workspace/output/result.blend`. When it is
saved and you are satisfied with it, stop.
