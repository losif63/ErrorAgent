"""Summarise a result.blend: scene settings, cameras, and every object's collection and bounds.

    blender --background result.blend --python inspect_blend.py -- summary.json

Run in the image after the agent exits; this checks the delivery and counts nothing.
"""

import json
import sys

import bpy
from mathutils import Vector

scene = bpy.context.scene
objects = []
for obj in scene.objects:
    entry = {"name": obj.name, "type": obj.type, "collections": [c.name for c in obj.users_collection]}
    if obj.type == "MESH":
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        entry["bbox_min"] = [round(min(c[i] for c in corners), 4) for i in range(3)]
        entry["bbox_max"] = [round(max(c[i] for c in corners), 4) for i in range(3)]
        entry["vertices"] = len(obj.data.vertices)
    if obj.animation_data and obj.animation_data.action:
        entry["keyframed"] = sorted({fc.data_path for fc in obj.animation_data.action.fcurves})
    objects.append(entry)

summary = {
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "fps": scene.render.fps / scene.render.fps_base,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "scene_camera": scene.camera.name if scene.camera else None,
    "meshes": sum(o["type"] == "MESH" for o in objects),
    "cameras": sum(o["type"] == "CAMERA" for o in objects),
    "lights": sum(o["type"] == "LIGHT" for o in objects),
    "objects": objects,
}
with open(sys.argv[sys.argv.index("--") + 1], "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)
