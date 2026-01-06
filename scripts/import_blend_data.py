"""
Script Blender pour importer un fichier .blend_data
A executer dans Blender: File > Scripting > Run Script

Usage:
    1. Ouvrir Blender
    2. Aller dans l'onglet Scripting
    3. Ouvrir ce fichier
    4. Modifier BLEND_DATA_PATH avec le chemin de votre fichier
    5. Executer le script
"""

import json
import math
from typing import Any

# MODIFIER CE CHEMIN avec votre fichier .blend_data
BLEND_DATA_PATH = r"C:\Users\jerem\Desktop\scrt\Enoptron\poly_spinor_nexus_7d\vault_storage\keys\complete_key_alice.blend_data"

# Blender Python API (optionnel)
bpy: Any = None
BLENDER_AVAILABLE = False

try:
    import bpy as _bpy
    bpy = _bpy
    BLENDER_AVAILABLE = True
except ImportError:
    print("Ce script doit etre execute dans Blender!")


def clean_scene():
    """Nettoie la scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for collection in bpy.data.collections:
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def create_material(name: str, base_color: list, metallic: float = 0.5,
                   roughness: float = 0.2, emission: float = 0.5):
    """Cree un materiau PBR"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    principled.inputs['Base Color'].default_value = (*base_color, 1.0)
    principled.inputs['Metallic'].default_value = metallic
    principled.inputs['Roughness'].default_value = roughness
    principled.inputs['Emission Strength'].default_value = emission
    principled.inputs['Emission Color'].default_value = (*base_color, 1.0)
    
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    return mat


def create_mesh(mesh_type: str, location: tuple, scale: tuple = (1, 1, 1)):
    """Cree un mesh selon le type"""
    if mesh_type == 'tetrahedron':
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.3, depth=0.4, location=location)
    elif mesh_type == 'cube':
        bpy.ops.mesh.primitive_cube_add(size=0.4, location=location)
    elif mesh_type == 'octahedron':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.25, location=location)
    elif mesh_type == 'dodecahedron':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.25, location=location)
    elif mesh_type == 'icosahedron':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.3, location=location)
    elif mesh_type == 'pentagonal_trapezohedron':
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.25, location=location)
    else:  # sphere
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=location)
    
    obj = bpy.context.active_object
    obj.scale = scale
    return obj


def import_blend_data(filepath: str):
    """Importe un fichier .blend_data"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Import de: {data['key_id']}")
    print(f"Utilisateur: {data['user_name']}")
    print(f"Version: {data['version']}")
    
    # Nettoyer la scene
    clean_scene()
    
    # Configurer la scene
    scene = bpy.context.scene
    scene.name = data['scene']['name']
    scene.frame_end = data['scene']['frame_end']
    
    # World color
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    bpy.context.scene.world.use_nodes = True
    bg_node = bpy.context.scene.world.node_tree.nodes.get('Background')
    if bg_node:
        bg_node.inputs['Color'].default_value = (*data['scene']['world_color'], 1.0)
    
    # Creer les materiaux
    materials = {}
    for mat_name, mat_data in data['materials'].items():
        materials[mat_name] = create_material(
            mat_name,
            mat_data['base_color'],
            mat_data['metallic'],
            mat_data['roughness'],
            mat_data['emission_strength']
        )
    
    print(f"Materiaux crees: {len(materials)}")
    
    # Creer les clusters
    for cluster_data in data['clusters']:
        # Creer la collection
        collection = bpy.data.collections.new(cluster_data['name'])
        bpy.context.scene.collection.children.link(collection)
        
        # Materiau pour ce cluster
        cluster_mat = create_material(
            f"Mat_{cluster_data['name']}",
            cluster_data['color'],
            metallic=0.3,
            roughness=0.4,
            emission=0.3
        )
        
        # Creer les objets
        for obj_data in cluster_data['objects']:
            obj = create_mesh(
                cluster_data['mesh_type'],
                tuple(obj_data['location']),
                tuple(obj_data['scale'])
            )
            obj.name = obj_data['name']
            obj.rotation_euler = tuple(obj_data['rotation'])
            
            # Appliquer le materiau
            if obj.data.materials:
                obj.data.materials[0] = cluster_mat
            else:
                obj.data.materials.append(cluster_mat)
            
            # Proprietes custom
            for prop_name, prop_value in obj_data['properties'].items():
                obj[prop_name] = prop_value
            
            # Deplacer dans la collection
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            collection.objects.link(obj)
    
    print(f"Clusters crees: {len(data['clusters'])}")
    
    # Creer les polyedres-cles
    key_collection = bpy.data.collections.new("KeyPolyhedra")
    bpy.context.scene.collection.children.link(key_collection)
    
    mesh_types_key = {
        'D4': 'tetrahedron',
        'D6': 'cube',
        'D8': 'octahedron',
        'D10': 'pentagonal_trapezohedron',
        'D12': 'dodecahedron',
        'D20': 'icosahedron',
        'D100': 'sphere'
    }
    
    for poly_data in data['key_polyhedra']:
        mesh_type = mesh_types_key.get(poly_data['die_type'], 'cube')
        obj = create_mesh(
            mesh_type,
            tuple(poly_data['location']),
            tuple(poly_data['scale'])
        )
        obj.name = poly_data['name']
        
        # Trouver le materiau correspondant
        mat_key = f"{poly_data['die_type']}_{poly_data['material']}"
        if mat_key in materials:
            if obj.data.materials:
                obj.data.materials[0] = materials[mat_key]
            else:
                obj.data.materials.append(materials[mat_key])
        
        # Proprietes
        for prop_name, prop_value in poly_data['properties'].items():
            obj[prop_name] = prop_value
        
        # Animation de rotation
        obj.rotation_mode = 'XYZ'
        obj.keyframe_insert(data_path='rotation_euler', frame=1)
        
        rot_speed = poly_data['animation']['rotation_speed']
        obj.rotation_euler.z = rot_speed * 120 * 2 * math.pi
        obj.keyframe_insert(data_path='rotation_euler', frame=120)
        
        # Deplacer dans la collection
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        key_collection.objects.link(obj)
    
    print(f"Polyedres-cles crees: {len(data['key_polyhedra'])}")
    
    # Camera
    cam_data = data['camera']
    bpy.ops.object.camera_add(location=tuple(cam_data['location']))
    camera = bpy.context.active_object
    camera.rotation_euler = tuple(cam_data['rotation'])
    camera.data.lens = cam_data['lens']
    bpy.context.scene.camera = camera
    
    # Lumieres
    for light_data in data['lights']:
        if light_data['type'] == 'SUN':
            bpy.ops.object.light_add(type='SUN', location=(10, 10, 20))
            light = bpy.context.active_object
            light.data.energy = light_data['energy']
            light.rotation_euler = tuple(light_data['rotation'])
        elif light_data['type'] == 'AREA':
            bpy.ops.object.light_add(type='AREA', location=tuple(light_data['location']))
            light = bpy.context.active_object
            light.data.energy = light_data['energy']
            light.data.size = light_data['size']
    
    # Stocker les proprietes crypto dans la scene
    for prop_name, prop_value in data['crypto_properties'].items():
        scene[prop_name] = prop_value
    
    print("\n=== IMPORT COMPLETE ===")
    print(f"Key ID: {data['crypto_properties']['psnx_key_id']}")
    print(f"Entropie: {data['crypto_properties']['psnx_entropy_bits']} bits")
    print(f"Bell quantique: {data['crypto_properties']['psnx_is_quantum']}")
    print(f"Violations Bell: {data['crypto_properties']['psnx_bell_violations']}")
    

if __name__ == "__main__":
    if BLENDER_AVAILABLE:
        import_blend_data(BLEND_DATA_PATH)
    else:
        print("Executer ce script dans Blender!")
