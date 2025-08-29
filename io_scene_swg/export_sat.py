import os, bpy
from . import swg_types
from . import nsg_iff
from . import export_lmg
from . import export_skt

def save(context, filepath, *, create_anim_controller = True, export_lmgs = True, export_mgns = True, do_tangents = True, export_skts = True):
    collection = bpy.context.view_layer.active_layer_collection.collection
    if collection != None:
        dirname = os.path.dirname(filepath)
        fullpath = os.path.join(dirname, collection.name.split('.')[0] + ".sat")
        return export_sat(context, fullpath, collection, create_anim_controller, export_lmgs, export_mgns, do_tangents, export_skts)
    else:
        return {'CANCELLED'}

def export_sat(context, filepath, collection, create_anim_controller = True, export_lmgs = True, export_mgns = True, do_tangents = True, export_skts = True):
    sat_name = os.path.basename(filepath).replace('.sat','')
    print(f"Creating SAT: {sat_name}")

    lmgs = []
    skts = []

    for child in collection.children:
        if child.name.endswith(".lmg"):
            lmgs.append(child)
        elif child.name.endswith(".skt"):
            skts.append(child)
    
    iff = nsg_iff.IFF(initial_size=512000)      
    iff.insertForm("SMAT")
    iff.insertForm("0003")

    # LMG and Skeleton counts
    iff.insertChunk("INFO")
    iff.insert_int32(len(lmgs))
    iff.insert_int32(len(skts))
    iff.insert_bool(create_anim_controller)
    iff.exitChunk("INFO")

    dirname = os.path.dirname(filepath)
    print(f"{dirname}")

    # Lod Mesh Generators    
    iff.insertChunk("MSGN")
    for lmg in lmgs:
        if export_lmgs:
            lmg_path = os.path.join(dirname, "mesh/" + lmg.name.split('.')[0] + ".lmg")
            export_lmg.export_lmg(context, lmg_path, lmg, export_mgns, do_tangents)
        iff.insertChunkString("appearance/mesh/" + lmg.name.split('.')[0] + ".lmg")
    iff.exitChunk("MSGN")
    
    # Skeletons
    iff.insertChunk("SKTI")
    for skt in skts:
        if export_skts:
            skt_path = os.path.join(dirname, "skeleton/" + skt.name.split('.')[0] + ".skt")
            export_skt.export_skt(context, skt_path, skt)
        iff.insertChunkString("appearance/skeleton/" + skt.name.split('.')[0] + ".skt")
        iff.insertChunkString("")
    iff.exitChunk("SKTI")

    # Logical Animation Tables
    iff.insertChunk("LATX")
    iff.insert_int16(len(skts))
    for skt in skts:
        iff.insertChunkString("appearance/skeleton/" + skt.name.split('.')[0] + ".skt")
        lat = ""
        for child in skt.children:
            for key in child.keys():
                if key == "LATX":
                    lat = child["LATX"]
                    break
            if lat != "":
                break
        iff.insertChunkString(lat)
    iff.exitChunk("LATX")

    iff.write(filepath)

    return {'FINISHED'}