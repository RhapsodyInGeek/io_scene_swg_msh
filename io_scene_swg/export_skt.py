import os
import bpy
import time, datetime
from . import nsg_iff
from bpy.props import *
from mathutils import Vector

def save(context, filepath,):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split(".")[0]+".skt")
        extract_dir=context.preferences.addons[__package__].preferences.swg_root
        return export_skt(fullpath, extract_dir, collection)
    else:
        return {'CANCELLED'}

def export_skt(context, filepath, collection):
    starttime = time.time()

    skt_name = os.path.basename(filepath).replace('.skt','')
    arm_objs = []

    for obj in collection.all_objects:
        # Skip nested objects. We only want ones directly under the collection.
        if obj.parent:
            continue
        if obj.type == "ARMATURE":
            arm_objs.append(obj)

    iff = nsg_iff.IFF(initial_size=512000)
    iff.insertForm("SLOD")
    iff.insertForm("0000")

    # Skeleton LOD count
    iff.insertChunk("INFO")
    iff.insert_int16(arm_objs.count)
    iff.exitChunk("INFO")

    for arm in arm_objs:
        iff.insertForm("SKTM")
        iff.insertForm("0002")

        bones = []
        for b in arm.bones:
            # Allow the use of control bones like IK
            if b.use_deform:
                bones.append(b)
        
        # Joint Count
        iff.insertChunk("INFO")
        iff.insert_int32(bones.count)
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
                for i in bones.count:
                    if b.parent == bones[i]:
                        iff.insert_int32(i)
                        break
            else:
                iff.insert_int32(-1)
        iff.exitChunk("PRNT")
        
        identity_quaternion = [0.0, 1.0, 0.0, 0.0]
        
        # Pre Multiply Rotations
        iff.insertChunk("RPRE")
        for i in bones.count:
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPRE")
        
        # Post Multiply Rotations
        iff.insertChunk("RPST")
        for i in bones.count:
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("RPST")
        
        # Bind Pose Translations
        iff.insertChunk("BPTR")
        for b in bones:
            t = b.head_local
            t = Vector((t[0], t[2], t[1]))
            iff.insertFloatVector3(t)
        iff.exitChunk("BPTR")

        # Bind Pose Rotations
        iff.insertChunk("BPRO")
        for i in bones.count:
            iff.insertFloatVector4(identity_quaternion)
        iff.exitChunk("BPRO")
        
        # Joint Rotation Order
        iff.insertChunk("JROR")
        iff.insert_int32(0)
        iff.exitChunk("JROR")

        iff.exitForm("0002")
        iff.exitForm("SKTM")
    
    iff.exitForm("0000")
    iff.exitForm("SLOD")

    iff.write(filepath)
    
    now = time.time()
    print(f"Successfully wrote: {filepath} Duration: " + str(datetime.timedelta(seconds=(now-starttime))))
    return {'FINISHED'}
