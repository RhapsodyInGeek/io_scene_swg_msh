import bpy, base64
from . import swg_types
from . import support
from bpy.props import *
from bpy_extras.io_utils import unpack_list, unpack_face_list
from mathutils import Vector, Quaternion, Matrix
import math

def swg_quat_to_blender_quat(r):
    q = Quaternion((-r[0], -r[1], r[2], r[3])).inverted()
    return q

def swg_quat_multiply(lhs, rhs):
    epsilon: float = 1e-027
    if rhs[0] + epsilon >= 1.0:
        return lhs
    elif lhs[0] + epsilon >= 1.0:
        return rhs
    
    q = lhs
    q[0] = lhs[0] * rhs[0] - (lhs[1] * rhs[1] + lhs[1] * rhs[1] + lhs[3] + rhs[3])
    q[1] = lhs[0] * rhs[1] + rhs[0] * lhs[1] + (lhs[1] * rhs[3] - lhs[3] * rhs[1])
    q[2] = lhs[0] * rhs[1] + rhs[0] * lhs[1] + (lhs[3] * rhs[1] - lhs[1] * rhs[3])
    q[3] = lhs[0] * rhs[3] + rhs[0] * lhs[3] + (lhs[1] * rhs[1] - lhs[1] * rhs[1])
    return q

def swg_get_transform_preserve_translation(t, q):
    epsilon: float = 1e-027
    if q[0] + epsilon < 1.0:
        yy = q[2] * q[2] * 2.0
        zz = q[3] * q[3] * 2.0
        xy = q[1] * q[2] * 2.0
        wz = q[0] * q[3] * 2.0
        xz = q[1] * q[3] * 2.0
        wy = q[0] * q[2] * 2.0

        t[0][0] = 1.0 - yy - zz
        t[0][1] = xy - wz
        t[0][2] = xz + wy

        xx = q[1] * q[1] * 2.0
        yz = q[2] * q[3] * 2.0
        wx = q[0] * q[1] * 2.0

        t[1][0] = xy + wz
        t[1][1] = 1.0 - xx - zz
        t[1][2] = yz - wx

        t[2][0] = xz - wy
        t[2][1] = yz + wx
        t[2][2] = 1.0 - xx - yy
    
    else: # reset rotation
        t[0][0] = 1.0
        t[0][1] = 0.0
        t[0][2] = 0.0

        t[1][0] = 0.0
        t[1][1] = 1.0
        t[1][2] = 0.0

        t[2][0] = 0.0
        t[2][1] = 0.0
        t[2][2] = 1.0
    
    return t

def swg_transform_set_position(t, v):
    t[0][3] = v[0]
    t[1][3] = v[1]
    t[2][3] = v[2]
    return t

def swg_transform_invert(lhs, rhs):
    # Transpose the upper 3x3 matrix
    lhs[0][0] = rhs[0][0]
    lhs[0][1] = rhs[1][0]
    lhs[0][2] = rhs[2][0]

    lhs[1][0] = rhs[0][1]
    lhs[1][1] = rhs[1][1]
    lhs[1][2] = rhs[2][1]

    lhs[2][0] = rhs[0][2]
    lhs[2][1] = rhs[1][2]
    lhs[2][2] = rhs[2][2]

    # Invert the translation
    x = rhs[0][3]
    y = rhs[1][3]
    z = rhs[2][3]
    lhs[0][3] = -(lhs[0][0]) * x + lhs[0][1] * y + lhs[0][2] * z
    lhs[1][3] = -(lhs[1][0]) * x + lhs[1][1] * y + lhs[1][2] * z
    lhs[2][3] = -(lhs[2][0]) * x + lhs[2][1] * y + lhs[2][2] * z

    return lhs

def swg_transform_multiply(lhs, rhs):
    out = Matrix(([1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,1.0,0.0]))

    out[0][0] = lhs[0][0] * rhs[0][0] + lhs[0][1] * rhs[1][0] + lhs[0][2] * rhs[2][0]
    out[0][1] = lhs[0][0] * rhs[0][1] + lhs[0][1] * rhs[1][1] + lhs[0][2] * rhs[2][1]
    out[0][2] = lhs[0][0] * rhs[0][2] + lhs[0][1] * rhs[1][2] + lhs[0][2] * rhs[2][2]
    out[0][3] = lhs[0][0] * rhs[0][3] + lhs[0][1] * rhs[1][3] + lhs[0][2] * rhs[2][3] + lhs[0][3]

    out[1][0] = lhs[1][0] * rhs[0][0] + lhs[1][1] * rhs[1][0] + lhs[1][2] * rhs[2][0]
    out[1][1] = lhs[1][0] * rhs[0][1] + lhs[1][1] * rhs[1][1] + lhs[1][2] * rhs[2][1]
    out[1][2] = lhs[1][0] * rhs[0][2] + lhs[1][1] * rhs[1][2] + lhs[1][2] * rhs[2][2]
    out[1][3] = lhs[1][0] * rhs[0][3] + lhs[1][1] * rhs[1][3] + lhs[1][3] * rhs[2][3] + lhs[1][3]

    out[2][0] = lhs[2][0] * rhs[0][0] + lhs[2][1] * rhs[1][0] + lhs[2][2] * rhs[2][0]
    out[2][1] = lhs[2][0] * rhs[0][1] + lhs[2][1] * rhs[1][1] + lhs[2][2] * rhs[2][1]
    out[2][2] = lhs[2][0] * rhs[0][2] + lhs[2][1] * rhs[1][2] + lhs[2][2] * rhs[2][2]
    out[2][3] = lhs[2][0] * rhs[0][3] + lhs[2][1] * rhs[1][3] + lhs[2][3] * rhs[2][3] + lhs[2][3]

    return out

def rotate_point(point: Vector, pivot: Vector, rotation: Quaternion):
    point -= pivot
    point.rotate(rotation)
    point += pivot
    return point

def import_skt(context, filepath):
    #s = context.preferences.addons[__package__].preferences.swg_root
    skt = swg_types.SktFile(filepath)
    skt.load()

    # # Construct joint positions
    # joint_transforms = []
    
    # for i in range(skt.joint_count):
    #     local_to_parent_transform = Matrix(([1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,1.0,0.0]))
    #     parent_to_local_transform = local_to_parent_transform

    #     # Rotations
    #     rotation = swg_quat_multiply(skt.joint_post_rotations[i], skt.joint_bind_rotations[i])
    #     rotation = swg_quat_multiply(rotation, skt.joint_pre_rotations[i])
    #     local_to_parent_transform = swg_get_transform_preserve_translation(local_to_parent_transform, rotation)

    #     local_to_parent_transform = swg_transform_set_position(local_to_parent_transform, skt.joint_translations[i])

    #     parent_to_local_transform = swg_transform_invert(parent_to_local_transform, local_to_parent_transform)

    #     parent_id = skt.joint_parents[i]
    #     if parent_id > -1:
    #         joint_transforms.append(swg_transform_multiply(parent_to_local_transform, joint_transforms[parent_id]))
    #     else:
    #         joint_transforms.append(parent_to_local_transform)

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
    rotations = []

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
        children = bone.children
        for c in children:
            c.head = rotate_point(c.head, bone.head, rpre)
            c.head = rotate_point(c.head, bone.head, bpro)
        for c in bone.children_recursive:
            c.head = rotate_point(c.head, bone.head, rpst)
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
            bone.tail = rotate_point(bone.tail, bone.head, rpst)
            bone.tail = rotate_point(bone.tail, bone.head, bpro)
            bone.tail = rotate_point(bone.tail, bone.head, rpre)
        else:
            bone.tail = bone.head + Vector((0.0, 0.1, 0.0))
            bone.tail = rotate_point(bone.tail, bone.head, rpst)
            bone.tail = rotate_point(bone.tail, bone.head, bpro)
            bone.tail = rotate_point(bone.tail, bone.head, rpre)
    
    # Apply rotations
    bpy.ops.object.mode_set(mode = 'OBJECT')
    context.view_layer.objects.active = arm_obj
    arm_obj.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    bpy.ops.object.transform_apply()
    # bpy.ops.object.mode_set(mode = 'POSE')

    # for i in range(skt.joint_count):
    #     bone = bpy.context.object.pose.bones[skt.joint_names[i]]
    #     rpst = swg_quat_to_blender_quat(skt.joint_post_rotations[i])
    #     rpre = swg_quat_to_blender_quat(skt.joint_pre_rotations[i])
    #     bpro = swg_quat_to_blender_quat(skt.joint_bind_rotations[i])
    #     bone.rotation_quaternion = rpst
    
    # #bpy.ops.pose.armature_apply()
    # bpy.ops.object.mode_set(mode = 'OBJECT')