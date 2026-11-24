# Francisco de Quevedo: exclusive custom skin for Marta (Hellish Quart)

A fan-made skin that works only for Marta. It runs on Marta's native 68-joint skeleton (Mafra5/Marfa), with her original moves and rapier, and ships with the Marta first-person (FPP) compatibility adjustment.

- **Native proportions.** Quevedo's shoulders sit at Marta's height (1.45 m vs 1.44 m). The trunk keeps Marta's joint layout with a 1 cm lift, so the neck and torso are never stretched.
- **Clean shoulders.** The T-pose source and its own skin weights fit Marta's limbs and hands, including palm orientation.
- **Rigid head, hair and glasses.**
- **No ghost body when hit.** Marta's 17 wound overlay meshes (`DecalBloody`, `DecalSpine1`, ...) are shaped like her own body. The visibility controller keeps them hidden under the skin, together with her stock face.
- **Game budget.** The 2M-triangle source is reduced to 100k triangles. Each part stays under the 65k vertices (counted after Unity splits UV seams) the game's wound decal builder supports.

## Layout

- `model/Quevedo_Marta.blend`: the fitted result on Marta's skeleton (100k triangles, weights, textures), editable in Blender 5.3. `model/references/` holds the four reference views.
- `model/Quevedo_source.glb` (not in the repository: 138 MB, over GitHub's file limit): the 2M-triangle source in T-pose, with PBR textures at 2048 and its own 52-bone rig. Place it there to rebuild from scratch.
- `blender_work/step1_prepare.py`: decimates dense sources, removes loose geometry, transfers the rig weights and exports the textures.
- `blender_work/step3_rig_marta.py`: fits Marta's limbs and hands to the source joints, carries the mesh into Marta's bind pose and splits off the rigid head. It exports `Skin.fbx` and QA renders.
- `blender_work/verify_skeleton.py`: checks that `Skin.fbx` holds exactly Marta's 68 bones and that every vertex has valid weights.
- `unity_project/`: Unity 2019.4.0f1 project (menu **Quevedo → Construir mod**). It builds `skin_marta_quevedo` and `pic_marta_quevedo`. If `model/selector_portrait.png` exists, it becomes the selector picture; otherwise a 3D portrait is rendered.
- `release/`: the installer (`.cmd`/`.ps1`), the FPP patch data and `LEEME.txt`.

## Rebuild

Copy `Hellish Quart_Data/Managed/PlayMaker.dll` from your own installation to `unity_project/Assets/Plugins/`, then run:

```powershell
$blender="C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$skel="unity_project\Assets\QuevedoMod\Editor\MartaSkeleton.json"
& $blender -b --factory-startup -P blender_work\step1_prepare.py -- model\Quevedo_source.glb model\Quevedo_source.glb build
& $blender -b --factory-startup -P blender_work\step3_rig_marta.py -- build $skel
& $blender -b --factory-startup -P blender_work\verify_skeleton.py -- build\marta\Skin.fbx $skel
.\build.ps1
```

`build.ps1` runs the Unity batch build and copies the four bundles into `release/`. It also creates `Quevedo_Marta.zip`.

## FPP adjustment

The installer changes 4 bytes of Marta's skin loader (PlayMaker FSM, path ID 67770) in `resources.assets`. On Steam build 26432078 the true event of `isFPP?` goes from `yes` to `no`, so first person uses the selected custom skin. Before writing anything, it checks the 15,936-byte block by SHA-256. It saves that block to `marta_loader_backup.bin` and verifies the result.
