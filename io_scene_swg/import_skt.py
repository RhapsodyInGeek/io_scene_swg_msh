import bpy, base64
from . import swg_types
from . import support
from bpy.props import *
from bpy_extras.io_utils import unpack_list, unpack_face_list
from mathutils import Vector, Quaternion, Matrix
import math

def swg_quat_mult(lhs: Quaternion, rhs: Quaternion):
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

# // ----------------------------------------------------------------------
# /**
#  * construct a quaternion representing the orientation specified by spinning
#  * 'angle' number of radians around unit vector 'vector'.
#  * 
#  * Make sure 'vector' is normalized.  This routine will not normalize it
#  * for you.
#  * 
#  * @param angle  [IN] angle to spin around vector (in radians)
#  * @param vector  [IN] vector around which angle is spun (must be normalized)
#  */

# Quaternion::Quaternion(float angle, const Vector &vector) :
# 	w(0.0f),
# 	x(0.0f),
# 	y(0.0f),
# 	z(0.0f)
# {
# 	// -TRF- do a DEBUG_FATAL check on magnitude to ensure it is nearly 1.0

# 	const float halfAngle    = 0.5f * angle;
# 	const float sinHalfAngle = sin(halfAngle);

# 	w = cos(halfAngle);
# 	x = vector.x * sinHalfAngle;
# 	y = vector.y * sinHalfAngle;
# 	z = vector.z * sinHalfAngle;
# }

# Quaternion MayaConversions::convertRotation(const MEulerRotation &euler)
# {
# 	Quaternion qx(static_cast<real>(euler.x), Vector::unitX);
# 	Quaternion qy(static_cast<real>(-euler.y), Vector::unitY);
# 	Quaternion qz(static_cast<real>(-euler.z), Vector::unitZ);

# 	switch (euler.order)
# 	{
# 		case MEulerRotation::kXYZ: return qz * (qy * qx);
# 		case MEulerRotation::kYZX: return qx * (qz * qy);
# 		case MEulerRotation::kZXY: return qy * (qx * qz);
# 		case MEulerRotation::kXZY: return qy * (qz * qx);
# 		case MEulerRotation::kYXZ: return qz * (qx * qy);
# 		case MEulerRotation::kZYX: return qx * (qy * qz);
# 	}

# 	FATAL(true, ("should not reach here\n"));
# 	return Quaternion(); //lint !e527 // unreachable // true, needed for MSVC
# }

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

def rotate_point(point: Vector, pivot: Vector, rotation: Quaternion):
    point -= pivot
    point.rotate(rotation)
    point += pivot
    return point

def import_skt(context, filepath):
    #s = context.preferences.addons[__package__].preferences.swg_root
    skt = swg_types.SktFile(filepath)
    skt.load()

    arm_name = filepath.split('\\')[-1].split('.')[0]
    arm = bpy.data.armatures.new(arm_name)
    arm_obj = bpy.data.objects.new(arm_name, arm)
    arm_obj.data.display_type = 'STICK'
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
        bone.use_deform = True
        bone.use_inherit_rotation = True
        bones.append(bone)

    # Parent bones and translate
    for i in range(skt.joint_count):
        bone = bones[i]
        v = skt.joint_translations[i]
        bone.head = Vector((v[0], v[2], v[1]))
        parent_id = skt.joint_parents[i]
        if parent_id > -1:
            bone.parent = bones[parent_id]
            bone.head += bone.parent.head

    for i in range(skt.joint_count):
        bone = bones[i]
        children = bone.children
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
            bone.tail = bone.head + bone.parent.vector * 0.5 * len(bone.head - bone.parent.head)
        else:
            bone.tail = bone.head + Vector((0.0, 0.05, 0.0))
    
    # Apply rotations
    bpy.ops.object.mode_set(mode = 'OBJECT')
    arm_obj.select_set(True)
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode = 'POSE')

    for i in range(skt.joint_count):
        bone = bpy.context.object.pose.bones[skt.joint_names[i]]
        v4 = swg_quat_mult(skt.joint_post_rotations[i], skt.joint_bind_rotations[i])
        v4 = swg_quat_mult(v4, skt.joint_pre_rotations[i])
        r = Quaternion((v4[0], v4[1], -v4[3], v4[2]))
        bone.rotation_quaternion = r
    
    #bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode = 'OBJECT')