bl_info = {
    "name": "Q3-AnimationConfig",
    "blender": (4, 00, 0),
    "category": "Animation",
    "location": "Nonlinear Animation > Side panel (N) > Q3 Animation Config",
    "description": (
        "Writes config file from NLA strips. Add .dead, .loop and .{fps} to name (optional)"
    ),
}

import bpy
import os

class Q3AnimationConfigProperties(bpy.types.PropertyGroup):
    metadata: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    metadata_index: bpy.props.IntProperty(default=-1)
    metadata_item: bpy.props.StringProperty(name="Metadata Item", default="")
    selected_object: bpy.props.PointerProperty(name="Track source object", type=bpy.types.Object, description="Only consider the tracks of selected object (optional)")

class Q3AnimationConfigPanel(bpy.types.Panel):
    bl_label = "Q3 Animation Config"
    bl_idname = "VIEW3D_PT_q3_animation_config"
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Q3 Animation Config'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        q3_props = scene.q3_animation_config

        row = layout.row()
        row.prop(q3_props, "metadata_item")
        row = layout.row()
        row.operator("q3.add_metadata", text="Add")

        row = layout.row()
        row.template_list("UI_UL_list", "metadata_list", q3_props, "metadata", q3_props, "metadata_index")

        row = layout.row()
        row.operator("q3.remove_metadata", text="Delete")
        row = layout.row()
        row.prop(q3_props, "selected_object", text="Source")
        row = layout.row()
        row.operator("q3.save_animation_config", text="Save Animation Config")

        row = layout.row()
        row.operator("q3.open_cheatsheet", text="Open Cheatsheet")

class Q3AddMetadataOperator(bpy.types.Operator):
    bl_idname = "q3.add_metadata"
    bl_label = "Add Metadata"

    def execute(self, context):
        scene = context.scene
        q3_props = scene.q3_animation_config
        item = q3_props.metadata.add()
        item.name = q3_props.metadata_item
        q3_props.metadata_item = ""
        return {'FINISHED'}

class Q3RemoveMetadataOperator(bpy.types.Operator):
    bl_idname = "q3.remove_metadata"
    bl_label = "Remove Metadata"

    def execute(self, context):
        scene = context.scene
        q3_props = scene.q3_animation_config
        if q3_props.metadata_index >= 0 and q3_props.metadata:
            q3_props.metadata.remove(q3_props.metadata_index)
            q3_props.metadata_index = min(max(0, q3_props.metadata_index - 1), len(q3_props.metadata) - 1)
        return {'FINISHED'}

class Q3SaveAnimationConfigOperator(bpy.types.Operator):
    bl_idname = "q3.save_animation_config"
    bl_label = "Save Animation Config"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        q3_props = scene.q3_animation_config

        # Define the output file path
        output_file_path = self.filepath if self.filepath else os.path.join(bpy.path.abspath("//"), "animation.cfg")

        def parse_action_name(action_name):
            parts = action_name.split('.')
            name = parts[0]
            fps = bpy.context.scene.render.fps
            looping_frames = 0
            is_dead = False

            for part in parts[1:]:
                if part.isdigit():
                    fps = int(part)
                elif part == 'loop':
                    looping_frames = -1  # Placeholder to indicate looping frames should match num_frames
                elif part == 'dead':
                    is_dead = True
                    looping_frames = 0  # Ignore loop if dead is specified

            if is_dead:
                looping_frames = 0  # Ensure looping frames are zero if dead is specified

            return name, fps, looping_frames, is_dead

        def rename_to_dead(name):
            parts = name.split('_')
            if len(parts) > 1:
                base = parts[0]
                number = ''.join(filter(str.isdigit, parts[1]))
                return f"{base}_DEAD{number}"
            return name

        # Open a file to write the output
        with open(output_file_path, "w") as file:
            file.write("// animation config file\n\n")
            for item in q3_props.metadata:
                file.write(f"{item.name}\n")
            file.write("\n// first frame, num frames, looping frames, frames per second\n\n")

            # Iterate through all NLA tracks
            objects = [q3_props.selected_object] if q3_props.selected_object else bpy.data.objects
            for obj in objects:
                if obj and obj.animation_data and obj.animation_data.nla_tracks:
                    for track in obj.animation_data.nla_tracks:
                        for strip in track.strips:
                            start_frame = int(strip.frame_start)
                            end_frame = int(strip.frame_end)
                            num_frames = end_frame - start_frame

                            name, fps, looping_frames, is_dead = parse_action_name(strip.name)
                            if looping_frames == -1:
                                looping_frames = num_frames

                            # Write the formatted output to the file
                            file.write(f"{start_frame}\t{num_frames}\t{looping_frames}\t{fps}\t\t// {name}\n")

                            if is_dead:
                                dead_name = rename_to_dead(name)
                                file.write(f"{end_frame - 1}\t1\t0\t{fps}\t\t// {dead_name}\n")

        self.report({'INFO'}, "Animation config file has been created.")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class Q3OpenCheatsheetOperator(bpy.types.Operator):
    bl_idname = "q3.open_cheatsheet"
    bl_label = "Open Cheatsheet"
    bl_description = "https://clover.moe/mm3d_manual/olh_quakemd3.html"

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://clover.moe/mm3d_manual/olh_quakemd3.html")
        return {'FINISHED'}

classes = (
    Q3AnimationConfigProperties,
    Q3AnimationConfigPanel,
    Q3AddMetadataOperator,
    Q3RemoveMetadataOperator,
    Q3SaveAnimationConfigOperator,
    Q3OpenCheatsheetOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.q3_animation_config = bpy.props.PointerProperty(type=Q3AnimationConfigProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.q3_animation_config

if __name__ == "__main__":
    register()
