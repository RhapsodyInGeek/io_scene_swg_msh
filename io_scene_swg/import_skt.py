# SKT Import / Export
#
# Authors:
# Tim "RhapsodyInGeek" Maccabe (https://github.com/RhapsodyInGeek)
# Vera "sinewavey" Lux (https://github.com/sinewavey)
# Nick "NoStyleGuy" Rafalski (https://github.com/nostyleguy)
# (c) 2025
#
# SWG's skeletons use joints instead of bones, which are just positional pivot points.
# Blender bones have a head and a tail, so any bones without children to connect to 
# require their tail positions to be guessed. This can lead to some strange looking 
# bone orientations and may require manual post work to clean up.

import bpy
from . import swg_types
from bpy.props import *
from mathutils import Vector, Quaternion, Matrix
import math

def swg_quat_to_blender_quat(r):
    q = Quaternion((-r[0], -r[1], r[2], r[3]))
    return q

def import_skt(context, filepath):
    skt = swg_types.SktFile(filepath)
    skt.load()
    
    arm_name = filepath.split('\\')[-1].split('.')[0]
    arm = bpy.data.armatures.new(arm_name)
    arm_obj = bpy.data.objects.new(arm_name, arm)
    arm_obj.data.display_type = 'STICK'
    arm_obj.data.show_names = True
    arm_obj.show_in_front = True
    
    context.scene.collection.objects.link(arm_obj)
    arm_obj.select_set(True)
    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones = []
    
    # Create bones with initial positions
    for i in range(skt.joint_count):
        bone = arm.edit_bones.new(skt.joint_names[i])
        bones.append(bone)
        bone.use_deform = True
        bone.use_inherit_rotation = True
        t = skt.joint_translations[i]
        bone.head = Vector((-t[0], t[1], t[2]))
        bone.tail = bone.head + Vector((0.0, 0.0, 0.1))
        
    def process_bone_hierarchy(bone_index, parent_transform=Matrix.Identity(4)):
        if bone_index < 0 or bone_index >= skt.joint_count:
            return
            
        bone = bones[bone_index]

        rpre = swg_quat_to_blender_quat(skt.joint_pre_rotations[bone_index])
        rbind = swg_quat_to_blender_quat(skt.joint_bind_rotations[bone_index])
        rpost = swg_quat_to_blender_quat(skt.joint_post_rotations[bone_index])
        
        t = skt.joint_translations[bone_index]
        local_translation = Vector((-t[0], t[1], t[2]))
        
        # Create transformation matrix
        rotation_matrix = (rpost @ rbind @ rpre).to_matrix().to_4x4()
        translation_matrix = Matrix.Translation(local_translation)
        local_transform = translation_matrix @ rotation_matrix
        
        # Combine with parent transform
        world_transform = parent_transform @ local_transform
        
        bone.head = world_transform.translation
    
        parent_id = skt.joint_parents[bone_index]
        if parent_id >= 0:
            bone.parent = bones[parent_id]
        
        for i in range(skt.joint_count):
            if skt.joint_parents[i] == bone_index:
                process_bone_hierarchy(i, world_transform)
    
    for i in range(skt.joint_count):
        if skt.joint_parents[i] < 0:
            process_bone_hierarchy(i)
    
    # Set bone tails
    for i in range(skt.joint_count):
        bone = bones[i]
        children = bone.children
        ct = len(children)
        
        if ct > 0:
            tail_pos = Vector((0.0, 0.0, 0.0))
            for child in children:
                tail_pos += child.head
            tail_pos /= ct
            bone.tail = tail_pos
            if ct == 1:
                children[0].use_connect = True
        elif bone.parent:
            v = bone.head - bone.parent.head
            d = v / len(v)
            bone.tail = bone.head + d * len(v) * 0.5
        else:
            bone.tail = bone.head + Vector((0.0, 0.0, 0.05))

    bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.objects.active = arm_obj
    arm_obj.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    bpy.ops.object.transform_apply(rotation=True)