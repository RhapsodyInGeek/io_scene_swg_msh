# SKT Import / Export
#
# Authors:
# Tim "RhapsodyInGeek" Maccabe (https://github.com/RhapsodyInGeek)
# Vera "sinewavey" Lux (https://github.com/sinewavey)
# Nick "NoStyleGuy" Rafalski (https://github.com/nostyleguy)
# (c) 2025
#
# In order to export, make sure a collection with armatures is active. 
# No child armatures will be exported.
# Each armature in the collection is exported as an SKTM (LOD skeleton) packaged in the same SKT file.
# SKTMs are added in view layer descending order, allowing for multiple SKT LODs.
# Re-exported SOE skeletons seem to work despite having the rotations set to (0.0, 1.0, 0.0, 0.0).
# The rotations are only important for moving the skeleton's joints to the proper translations: 
#       if the joints are already in the correct positions, there is no need for the rotation values.

import bpy, os, math, time, datetime
from . import nsg_iff
from bpy.props import *
from mathutils import Vector

def save(context, filepath,):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split(".")[0]+".skt")
        return export_skt(context, fullpath, collection)
    else:
        return {'CANCELLED'}

def export_skt(context, filepath, collection):
    starttime = time.time()
    
    skt_name = os.path.basename(filepath).replace('.skt','')
    print(f"Creating SKT: {skt_name}")
    arm_objs = []

    for obj in collection.all_objects:
        # Skip nested objects. We only want ones directly under the collection.
        if obj.parent:
            continue
        if obj.type == 'ARMATURE':
            arm_objs.append(obj)
    
    if len(arm_objs) == 0:
        return {'CANCELLED'}

    iff = nsg_iff.IFF(initial_size=512000)
    iff.insertForm("SLOD")
    iff.insertForm("0000")

    # Skeleton LOD count
    iff.insertChunk("INFO")
    iff.insert_int16(len(arm_objs))
    iff.exitChunk("INFO")

    for arm in arm_objs:
        arm.select_set(True)
        context.view_layer.objects.active = arm
        arm.rotation_euler = (math.pi * -0.5, 0.0, 0.0)
        bpy.ops.object.transform_apply(rotation=True)

        iff.insertForm("SKTM")
        iff.insertForm("0002")

        bones = []
        for b in arm.data.bones:
            # Allow the use of control bones like IK
            if b.use_deform:
                bones.append(b)
        bone_ct = len(bones)
        
        # Joint Count
        iff.insertChunk("INFO")
        iff.insert_int32(bone_ct)
        iff.exitChunk("INFO")

        # Joint Names
        iff.insertChunk("NAME")
        for b in bones:
            iff.insertChunkString(b.name)
        iff.exitChunk("NAME")
        
        # Joint Parents
        iff.insertChunk("PRNT")
        for b in bones:
            if b.parent:
                for i in range(bone_ct):
                    if b.parent == bones[i]:
                        iff.insert_int32(i)
                        break
            else:
                iff.insert_int32(-1)
        iff.exitChunk("PRNT")
        
        identity_quaternion = [1.0, 0.0, 0.0, 0.0] # quat is written as xyzw
        
        # Pre Multiply Rotations
        iff.insertChunk("RPRE")
        for i in range(bone_ct):
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPRE")
        
        # Post Multiply Rotations
        iff.insertChunk("RPST")
        for i in range(bone_ct):
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPST")
        
        # Bind Pose Translations
        iff.insertChunk("BPTR")
        for b in bones:
            t = b.head_local
            if b.parent:
                pt = b.parent.head_local
                t = t - pt
            t = Vector((-t[0], t[1], t[2]))
            iff.insertFloatVector3(t)
        iff.exitChunk("BPTR")

        # Bind Pose Rotations
        iff.insertChunk("BPRO")
        for i in range(bone_ct):
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("BPRO")
        
        # Joint Rotation Order
        iff.insertChunk("JROR")
        for i in range(bone_ct):
            iff.insert_int32(0)
        iff.exitChunk("JROR")

        iff.exitForm("0002")
        iff.exitForm("SKTM")

        arm.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
        bpy.ops.object.transform_apply(rotation=True)
        arm.select_set(False)
    
    iff.exitForm("0000")
    iff.exitForm("SLOD")

    iff.write(filepath)

    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-starttime))))
    return {'FINISHED'}
