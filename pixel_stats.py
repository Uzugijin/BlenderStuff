
bl_info = {
    "name": "Image Pixel Counter",
    "category": "UV",
    "description": "Count black and transparent pixels in images",
    "author": "DeepSeek AI",
    "location": "UV/Image Editor > Tools > Pixel Stats",
    "version": (1, 0, 0),
    "blender": (4, 0, 0)
}

import bpy

class CountBlackTransparentPixels(bpy.types.Operator):
    """Count Black and Transparent Pixels"""
    bl_idname = "image.count_black_transparent"
    bl_label = "Count Black & Transparent Pixels"
    bl_description = "Count fully black and fully transparent pixels in the active image"

    @classmethod
    def poll(cls, context):
        # Check if we have an active image in the image editor
        space = cls.get_image_editor_space(context)
        return space and space.image

    @staticmethod
    def get_image_editor_space(context):
        """Get the image editor space data"""
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                return area.spaces.active
        return None

    def execute(self, context):
        space = self.get_image_editor_space(context)
        if not space or not space.image:
            self.report({'ERROR'}, "No active image in Image Editor")
            return {'CANCELLED'}
        
        image = space.image
        
        # Ensure image is loaded and has pixels
        if image.size[0] == 0 or image.size[1] == 0:
            self.report({'ERROR'}, "Image has no pixels or is not loaded")
            return {'CANCELLED'}
        
        # Ensure the image is updated
        if image.is_dirty:
            image.update()
        
        try:
            # Get image pixels (returns flat list of RGBA values)
            pixels = list(image.pixels)
            total_pixels = image.size[0] * image.size[1]
            
            if len(pixels) != total_pixels * 4:
                self.report({'ERROR'}, "Image pixel data is incomplete")
                return {'CANCELLED'}
            
            # Count statistics
            black_pixels = 0
            transparent_pixels = 0
            
            # Analyze pixels in chunks of 4 (RGBA)
            for i in range(0, len(pixels), 4):
                r, g, b, a = pixels[i], pixels[i+1], pixels[i+2], pixels[i+3]
                
                # Count fully black pixels (RGB all exactly 0)
                if r == 0.0 and g == 0.0 and b == 0.0:
                    black_pixels += 1
                
                # Count fully transparent pixels (Alpha exactly 0)
                if a == 0.0:
                    transparent_pixels += 1
            
            # Store results
            context.scene.black_pixel_count = black_pixels
            context.scene.transparent_pixel_count = transparent_pixels
            context.scene.total_pixel_count = total_pixels
            
            # Calculate percentages
            black_percentage = (black_pixels / total_pixels) * 100
            transparent_percentage = (transparent_pixels / total_pixels) * 100
            
            # Print results
            print(f"\n=== Pixel Analysis: {image.name} ===")
            print(f"Image Size: {image.size[0]} x {image.size[1]}")
            print(f"Total Pixels: {total_pixels:,}")
            print(f"Black Pixels: {black_pixels:,} ({black_percentage:.1f}%)")
            print(f"Transparent Pixels: {transparent_pixels:,} ({transparent_percentage:.1f}%)")
            print("=================================\n")
            
            self.report({'INFO'}, 
                       f"Black: {black_pixels:,} | Transparent: {transparent_pixels:,}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error analyzing image: {str(e)}")
            print(f"Pixel Analysis Error: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class PixelStatsPanel(bpy.types.Panel):
    """Pixel Statistics Panel"""
    bl_label = "Pixel Stats"
    bl_idname = "UV_PT_pixel_stats"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Image"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        
        # Current image info
        space = CountBlackTransparentPixels.get_image_editor_space(context)
        if space and space.image:
            box = layout.box()
            box.label(text=f"Image: {space.image.name}", icon='IMAGE_DATA')
            box.label(text=f"Size: {space.image.size[0]} x {space.image.size[1]}")
            
            # Analysis button
            row = layout.row()
            row.scale_y = 1.5
            row.operator("image.count_black_transparent", text="Count Pixels", icon='SEQ_CHROMA_SCOPE')
            
            # Display results if available
            if hasattr(context.scene, 'black_pixel_count'):
                box = layout.box()
                box.label(text="Pixel Counts", icon='TEXT')
                
                total_pixels = getattr(context.scene, 'total_pixel_count', 0)
                black_pixels = context.scene.black_pixel_count
                transparent_pixels = context.scene.transparent_pixel_count
                
                if total_pixels > 0:
                    black_percent = (black_pixels / total_pixels) * 100
                    transparent_percent = (transparent_pixels / total_pixels) * 100
                    
                    # Black pixels
                    row = box.row()
                    row.label(text="Black Pixels:")
                    row.label(text=f"{black_pixels:,} ({black_percent:.1f}%)")
                    
                    # Transparent pixels  
                    row = box.row()
                    row.label(text="Transparent Pixels:")
                    row.label(text=f"{transparent_pixels:,} ({transparent_percent:.1f}%)")
                    
                    # Total pixels
                    row = box.row()
                    row.label(text="Total Pixels:")
                    row.label(text=f"{total_pixels:,}")
                else:
                    box.label(text="No analysis data", icon='INFO')
        else:
            box = layout.box()
            box.label(text="No image open", icon='INFO')
            box.label(text="Open an image in this editor")

def register():
    bpy.utils.register_class(CountBlackTransparentPixels)
    bpy.utils.register_class(PixelStatsPanel)

    # Scene properties for storing results
    bpy.types.Scene.black_pixel_count = bpy.props.IntProperty(
        name="Black Pixels",
        description="Number of fully black pixels",
        default=0
    )

    bpy.types.Scene.transparent_pixel_count = bpy.props.IntProperty(
        name="Transparent Pixels", 
        description="Number of fully transparent pixels",
        default=0
    )
    
    bpy.types.Scene.total_pixel_count = bpy.props.IntProperty(
        name="Total Pixels",
        description="Total number of pixels in the image",
        default=0
    )

def unregister():
    bpy.utils.unregister_class(CountBlackTransparentPixels)
    bpy.utils.unregister_class(PixelStatsPanel)
    
    # Clean up properties
    del bpy.types.Scene.black_pixel_count
    del bpy.types.Scene.transparent_pixel_count
    del bpy.types.Scene.total_pixel_count

if __name__ == "__main__":
    register()