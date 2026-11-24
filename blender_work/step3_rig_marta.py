# Step 3: bind the textured mesh to Marta's native 68-joint skeleton.
#
# Marta's bones are moved/turned onto the joints of the source rig, the mesh is
# skinned with the source weights (renamed to Marta's bones), and then the
# skeleton is returned to Marta's native rest pose, carrying the mesh into
# Marta's bind space. Head and hat are split into a rigid Head-only part.
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
BUILD, SKELETON = args[0], args[1]
OUT = os.path.join(BUILD, 'marta'); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(BUILD, 'prepared.blend'))
mesh = bpy.data.objects['QuevedoBody']
J = {k: {'head': Vector(v['head']), 'tail': Vector(v['tail'])} for k, v in
     json.load(open(os.path.join(BUILD, 'source_joints.json'))).items()}

# --- Marta skeleton (same conversion as the Alatriste build) -----------------
native = json.load(open(SKELETON))
C = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
ad = bpy.data.armatures.new('MartaSkeleton'); arm = bpy.data.objects.new('Armature', ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in native['bones']:
    b = ad.edit_bones.new(n['name']); b.length = .05
    W = Matrix(n['world']); R = C @ W.to_3x3().to_4x4() @ C.inverted(); R.translation = C.to_3x3() @ W.translation
    b.matrix = R
    if n['parent']: b.parent = ad.edit_bones[n['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
original = {b.name: b.matrix_local.copy() for b in ad.bones}
origlen = {b.name: b.length for b in ad.bones}

# --- Fit Marta's joints to the source rig ------------------------------------
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones
def H(n): return eb[n].head.copy()
def apply(n, M):
    for q in [eb[n]] + list(eb[n].children_recursive): q.matrix = M @ q.matrix
def move(n, target): apply(n, Matrix.Translation(Vector(target) - H(n)))
def turn(n, child, target):
    h = H(n); r = (H(child) - h).normalized().rotation_difference((Vector(target) - h).normalized())
    apply(n, Matrix.Translation(h) @ r.to_matrix().to_4x4() @ Matrix.Translation(-h))
def frame(d, l):
    d = d.normalized(); l = (l - d * l.dot(d)).normalized(); return Matrix((d, l, d.cross(l))).transposed()
def align_frame(n, d1, l1, d2, l2):
    h = H(n); R = frame(d2, l2) @ frame(d1, l1).transposed()
    apply(n, Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h))

# The trunk keeps Marta's joint layout, but the whole upper block (chest,
# shoulders, neck, head) is lifted to the model's shoulder height. Marta's head
# sits ~5 cm higher above her shoulders than these models; fitting only the
# shoulders pulled them down and stretched the neck. The height difference is
# shared between the Hips-Spine and Spine-Spine1 spans of the torso instead.
lift = ((J['LeftArm']['head'].z + J['RightArm']['head'].z) / 2 -
        (H('LeftArm').z + H('RightArm').z) / 2)
move('Spine', H('Spine') + Vector((0, 0, lift / 2)))
move('Spine1', H('Spine1') + Vector((0, 0, lift / 2)))
print('UPPER_BODY_LIFT', round(lift, 4), flush=True)
for s in ('Left', 'Right'):
    move(s + 'Shoulder', J[s + 'Shoulder']['head']); turn(s + 'Shoulder', s + 'Arm', J[s + 'Arm']['head'])
    move(s + 'Arm', J[s + 'Arm']['head']); turn(s + 'Arm', s + 'ForeArm', J[s + 'ForeArm']['head'])
    move(s + 'ForeArm', J[s + 'ForeArm']['head']); turn(s + 'ForeArm', s + 'Hand', J[s + 'Hand']['head'])
    move(s + 'Hand', J[s + 'Hand']['head'])
    hn = s + 'Hand'
    align_frame(hn, H(hn + 'Middle1') - H(hn), H(hn + 'Index1') - H(hn + 'Pinky1'),
                J[hn + 'Middle1']['head'] - J[hn]['head'], J[hn + 'Index1']['head'] - J[hn + 'Pinky1']['head'])
    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        for k in (1, 2, 3):
            n = f'{hn}{f}{k}'; tgt = J[f'{hn}{f}{k+1}']['head'] if k < 3 else J[n]['tail']
            move(n, J[n]['head']); turn(n, f'{hn}{f}{k+1}', tgt)
    move(s + 'UpLeg', J[s + 'UpLeg']['head']); turn(s + 'UpLeg', s + 'Leg', J[s + 'Leg']['head'])
    move(s + 'Leg', J[s + 'Leg']['head']); turn(s + 'Leg', s + 'Foot', J[s + 'Foot']['head'])
    move(s + 'Foot', J[s + 'Foot']['head']); turn(s + 'Foot', s + 'ToeBase', J[s + 'ToeBase']['head'])
    move(s + 'ToeBase', J[s + 'ToeBase']['head']); turn(s + 'ToeBase', s + 'ToeBase_END', J[s + 'ToeBase']['tail'])
fit_head = {b.name: b.head.copy() for b in ad.edit_bones}
bpy.ops.object.mode_set(mode='OBJECT')

# --- Weights: source names -> Marta names ------------------------------------
RENAME = {'Spine1': 'Spine', 'Spine2': 'Spine1'}
bone_names = {b.name for b in ad.bones}
names = [g.name for g in mesh.vertex_groups]
per_vertex = []
for v in mesh.data.vertices:
    w = {}
    for g in v.groups:
        n = RENAME.get(names[g.group], names[g.group])
        if n not in bone_names: raise RuntimeError('Unmapped bone ' + n)
        w[n] = w.get(n, 0) + g.weight
    per_vertex.append(w)
V0 = np.array([tuple(v.co) for v in mesh.data.vertices])

# Rigid head: faces fully owned by the head (face, hair, hat).
head_faces = set()
for p in mesh.data.polygons:
    if p.center.z > 1.45 and all(per_vertex[i].get('Head', 0) >= .5 for i in p.vertices):
        head_faces.add(p.index)
head_verts = {i for f in head_faces for i in mesh.data.polygons[f].vertices}
body_verts = {i for p in mesh.data.polygons if p.index not in head_faces for i in p.vertices}
seam = head_verts & body_verts
for i in head_verts: per_vertex[i] = {'Head': 1.}

while mesh.vertex_groups: mesh.vertex_groups.remove(mesh.vertex_groups[0])
groups = {}
for i, w in enumerate(per_vertex):
    top = sorted(((n, x) for n, x in w.items() if x > 1e-4), key=lambda t: -t[1])[:4]
    tot = sum(x for _, x in top)
    if tot <= 0: top, tot = [('Hips', 1.)], 1.
    for n, x in top:
        g = groups.get(n) or mesh.vertex_groups.new(name=n); groups[n] = g
        g.add([i], x / tot, 'REPLACE')

# --- Carry the mesh into Marta's native bind pose ----------------------------
# Limb segments are stretched along their bones while carrying the mesh into
# the target skeleton. The source arms are much shorter than the fighter's bones
# (upper arm ~0.19 vs 0.27 m, forearm ~0.19 vs 0.30 m) and the legs differ too.
# Moving each bone to its target joint without stretching left the whole length
# difference in the blend zones (elbow, wrist, shoulder), which pinched and
# twisted the shoulders and arms in game. Each clavicle, upper arm, forearm, thigh and shin is
# scaled along its own axis from its joint, so every joint lands on the target
# skeleton and the segment between keeps its shape. Linear blend done by hand:
# a stretch along an arbitrary axis is not representable as a pose bone matrix.
mesh.parent = arm
SEGMENTS = [(s + a, s + b) for s in ('Left', 'Right') for a, b in
            (('Shoulder', 'Arm'), ('Arm', 'ForeArm'), ('ForeArm', 'Hand'), ('UpLeg', 'Leg'), ('Leg', 'Foot'))]
stretch = {}
for a, c in SEGMENTS:
    nh = original[a].translation; d = original[c].translation - nh
    r = d.length / max(1e-6, (fit_head[c] - fit_head[a]).length); dn = d.normalized()
    Sm = Matrix.Identity(3) + (r - 1) * Matrix(((dn.x * dn.x, dn.x * dn.y, dn.x * dn.z), (dn.y * dn.x, dn.y * dn.y, dn.y * dn.z), (dn.z * dn.x, dn.z * dn.y, dn.z * dn.z)))
    stretch[a] = Matrix.Translation(nh) @ Sm.to_4x4() @ Matrix.Translation(-nh)
    print('SEGMENT_STRETCH', a, round(r, 3), flush=True)
# The game snaps every skin bone onto the fighter's bone (SetParent with local
# position and rotation reset), so the fighter's joint positions rule. When the
# model's hips sit higher or lower than the fighter's, the hip area had to
# stretch or squash between pelvis and thighs and the arms lost proportion. The lower trunk (Hips and Spine weights) is
# therefore stretched vertically below the chest joint (Spine1), so the mesh hip
# joint lands on the fighter's; the thighs then start right there.
z0 = original['Spine1'].translation.z
mesh_hip = (fit_head['LeftUpLeg'].z + fit_head['RightUpLeg'].z) / 2
native_hip = (original['LeftUpLeg'].translation.z + original['RightUpLeg'].translation.z) / 2
r_trunk = (z0 - native_hip) / max(1e-6, z0 - mesh_hip)
St = Matrix.Translation((0, 0, z0)) @ Matrix.Diagonal((1., 1., r_trunk, 1.)) @ Matrix.Translation((0, 0, -z0))
for n in ('Hips', 'Spine'): stretch[n] = St
print('TRUNK_STRETCH', round(r_trunk, 3), 'mesh_hip', round(mesh_hip, 3), 'native_hip', round(native_hip, 3), flush=True)
Mb = {}
for b in ad.bones:
    M = original[b.name] @ b.matrix_local.inverted()
    Mb[b.name] = stretch[b.name] @ M if b.name in stretch else M
gname = {g.index: g.name for g in mesh.vertex_groups}
coords = []
for v in mesh.data.vertices:
    acc = Vector((0., 0., 0.)); tw = 0.
    for g in v.groups:
        acc += g.weight * (Mb[gname[g.group]] @ v.co); tw += g.weight
    coords.append(acc / tw if tw > 0 else v.co.copy())
for v, c in zip(mesh.data.vertices, coords): v.co = c
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for b in ad.edit_bones: b.matrix = original[b.name]; b.length = origlen[b.name]
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
mod = mesh.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

# --- Materials, split body/head ----------------------------------------------
img = bpy.data.images.load(os.path.join(BUILD, 'Quevedo_BaseColor.png'))
def material(name):
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    tx = mt.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Roughness'].default_value = .85
    mt.node_tree.links.new(tx.outputs['Color'], bs.inputs['Base Color']); return mt
mesh.data.materials.clear()
mesh.data.materials.append(material('QuevedoMaterial')); mesh.data.materials.append(material('HeadMaterial'))
for p in mesh.data.polygons: p.material_index = 1 if p.index in head_faces else 0
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.data.objects if o.type == 'MESH']
for o in parts:
    used = {o.data.materials[p.material_index].name for p in o.data.polygons}
    o.name = 'QuevedoHead' if any(n.startswith('HeadMaterial') for n in used) else 'QuevedoBody'
    o.data.name = o.name
    # Separating by material can leave stray vertices without faces in a part.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    stray = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=stray, context='VERTS'); bm.to_mesh(o.data); bm.free()
    print('STRAY_VERTICES_REMOVED', o.name, len(stray), flush=True)

# --- QA renders ---------------------------------------------------------------
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 1000; sc.render.resolution_y = 1200
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3
def render(n, pos, tgt=(0, 0, 1)):
    cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, n + '.png'); bpy.ops.render.render(write_still=True)
render('rest_front', (0, -4, 1)); render('rest_back', (0, 4, 1)); render('rest_side', (4, 0, 1))
def point(n, child, d):
    bpy.context.view_layer.update(); pb = arm.pose.bones[n]; m = pb.matrix; h = m.translation
    v = arm.pose.bones[child].matrix.translation - h
    r = v.normalized().rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m; bpy.context.view_layer.update()
for s, sg in (('Left', 1), ('Right', -1)):
    point(s + 'Arm', s + 'ForeArm', (sg * .7, 0, .7)); point(s + 'ForeArm', s + 'Hand', (sg * .5, -.3, .7))
render('test_arms_up', (0, -4, 1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
point('RightArm', 'RightForeArm', (-.25, -.7, -.25)); point('RightForeArm', 'RightHand', (.15, -.8, .15))
point('LeftArm', 'LeftForeArm', (.4, .2, -.4))
render('test_guard', (2, -4, 1.1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
cam.data.ortho_scale = .55; render('head_closeup', (0, -4, 1.62), (0, 0, 1.62)); render('head_side', (4, 0, 1.62), (0, 0, 1.62))

# --- Save and export ------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Quevedo_Marta.blend'))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
for o in parts: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Skin.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         add_leaf_bones=False, bake_anim=False, path_mode='COPY', embed_textures=False,
                         use_mesh_modifiers=False, apply_scale_options='FBX_SCALE_NONE')
report = {'parts': {o.name: {'verts': len(o.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in o.data.polygons)} for o in parts},
          'seam_vertices': len(seam), 'bones': len(ad.bones)}
json.dump(report, open(os.path.join(OUT, 'rig_report.json'), 'w'), indent=1)
print('MARTA_RIG_OK', report, flush=True)
