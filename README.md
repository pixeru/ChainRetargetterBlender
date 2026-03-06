# Animation Importer

This Blender addon adds an N-panel tab named Animation Importer in the 3D View.

Minimum Blender version: 4.0 or above.

What it does:
- Uses the selected armature as the target rig.
- Loads animation from an FBX file.
- Assigns the imported action to the selected rig so it shows up in the Action Editor.
- Tries to handle Blender 4.x action slot assignment when the imported action uses slots.
- Cleans up the temporary FBX objects after extracting the action.
- Removes imported scale and armature object transform keys so the rig keeps its existing size.
- Reports imported bone-name compatibility as `xx of xx bones, xx.x% compatible`.
- Can also compare compatibility against another armature already open in the scene.

Usage:
1. Install the addon by zipping this folder and installing it in Blender, or place the folder in your addons directory.
2. Enable the addon.
3. In the 3D View, press N and open the Animation Importer tab.
4. Select the destination rig.
5. Choose a source .fbx file.
6. Click Load Animation.

Video Docs:
- Walkthrough recording (https://github.com/user-attachments/assets/647cb192-680b-4e01-8e2e-21a624168b9f):

<video controls width="960" src="https://github.com/user-attachments/assets/647cb192-680b-4e01-8e2e-21a624168b9f">
	Your viewer does not support embedded video. Open the direct link below.
</video>

Notes:
- This is intended for the same rig structure. It does not retarget between different skeletons.
- The addon temporarily imports the FBX, grabs the action created by Blender's FBX importer, assigns it to your selected rig, then removes the imported FBX objects.
- After import, the addon compares imported bone names against the selected rig and shows the compatibility result in the panel.
- You can also select the target rig as active plus one other armature in the scene, then use `Check Open Rig Compatibility`.
- If the FBX contains multiple takes in a way Blender turns into multiple actions, this addon currently uses the action attached to the imported armature, or the first new action Blender creates.
- The imported action is sanitized to remove armature object transforms and bone scale curves, so the target rig keeps its current size and placement.
- The imported action is kept with a fake user so it stays saved in the file even if you unassign it.
