import bpy, base64
from . import swg_types
from . import support
from bpy.props import *
from bpy_extras.io_utils import unpack_list, unpack_face_list
from mathutils import Vector, Quaternion, Matrix
import math

def swg_quat_to_blender_quat(r):
    q = Quaternion((r[0], r[1], r[3], r[2]))
    return q

def rotate_point(point: Vector, pivot: Vector, rotation: Quaternion):
    point -= pivot
    point.rotate(rotation)
    point += pivot
    return point

def import_skt(context, filepath):
    #s = context.preferences.addons[__package__].preferences.swg_root
    skt = swg_types.SktFile(filepath)
    skt.load()

    # Create armature
    arm_name = filepath.split('\\')[-1].split('.')[0]
    arm = bpy.data.armatures.new(arm_name)
    arm_obj = bpy.data.objects.new(arm_name, arm)
    arm_obj.data.display_type = 'STICK'
    arm_obj.data.show_names = True
    arm_obj.show_in_front = True
    #arm_obj.show_names = True

    context.scene.collection.objects.link(arm_obj)
    arm_obj.select_set(True)
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode = 'EDIT')

    bones = []

    # Create bones
    for i in range(skt.joint_count):
        bone = arm.edit_bones.new(skt.joint_names[i])
        bones.append(bone)
        bone.use_deform = True
        bone.use_inherit_rotation = True
        t = skt.joint_translations[i]
        bone.head = Vector((-t[0], t[1], t[2]))

    # Parent bones and translate
    for i in range(skt.joint_count):
        bone = bones[i]
        parent_id = skt.joint_parents[i]
        if parent_id > -1:
            bone.parent = bones[parent_id]
            bone.head += bone.parent.head

    # Connect tails to children
    for i in range(skt.joint_count):
        bone = bones[i]
        rpre = swg_quat_to_blender_quat(skt.joint_pre_rotations[i])
        rpst = swg_quat_to_blender_quat(skt.joint_post_rotations[i])
        bpro = swg_quat_to_blender_quat(skt.joint_bind_rotations[i])
        r = rpst @ bpro @ rpre
        children = bone.children
        for c in bone.children_recursive:
            c.head = rotate_point(c.head, bone.head, r)
        ct = len(children)
        if ct > 0:
            tail_pos = Vector((0.0, 0.0, 0.0))
            for c in children:
                tail_pos += c.head
            tail_pos /= ct
            bone.tail = tail_pos
            if ct == 1:
                c.use_connect = True
        elif bone.parent:
            bone.tail = bone.head + (bone.parent.vector * len(bone.head - bone.parent.head) * 0.25)
            bone.tail = rotate_point(bone.tail, bone.head, r)
        else:
            bone.tail = bone.head + Vector((0.0, 0.1, 0.0))
            bone.tail = rotate_point(bone.tail, bone.head, r)
    
    # Apply rotations
    bpy.ops.object.mode_set(mode = 'OBJECT')
    context.view_layer.objects.active = arm_obj
    arm_obj.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    bpy.ops.object.transform_apply()