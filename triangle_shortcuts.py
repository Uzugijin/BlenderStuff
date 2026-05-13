bl_info = {
    "name": "Triangle Mesh Macros",
    "version": (2, 0, 0),
    "blender": (5, 00, 0),
    "category": "3D",
    "location": "3D View > Sidebar > Tris",
    "description": "Shortcuts for triangle based modelling",
    "author": "Uzugijin"
}     

import bpy
import bmesh

class MESH_OT_smart_subdivide_or_poke_or_rotate(bpy.types.Operator):
    """Smart operation based on selection:
    - 1 boundary vertex: Extend corner
    - 1 vertex: Triangle fan subdivision
    - 1 edge: Edge subdivision
    - 2 close parallel edges: Quad cut
    - Face(s): Make face and poke"""  

    bl_idname = "mesh.smart_edit_operation"
    bl_label = "Smart Edit Operation"
    bl_options = {'REGISTER', 'UNDO'}
       
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        selected_edges = [e for e in bm.edges if e.select]
        selected_faces = [f for f in bm.faces if f.select]
        selected_verts = [v for v in bm.verts if v.select]
        
        # MODE 1: Single edge
        if len(selected_edges) == 1:
            bpy.ops.mesh.select_mode(type='EDGE')
            edge = selected_edges[0]
            affected_faces = set()
            for face in edge.link_faces:  # Original faces connected to the edge
                affected_faces.add(face)
            # Subdivide the edge (resulting edges will be auto-selected by Blender)
            bmesh.ops.subdivide_edges(
                bm,
                edges=[edge],
                cuts=1,
                use_grid_fill=False,
                use_single_edge=False,
                use_only_quads=False
            )
            # Triangulate only the affected faces
            for face in list(affected_faces):
                # Check if face still exists (it might have been split)
                if face.is_valid:
                    bmesh.ops.triangulate(bm, faces=[face])
            # Now the two new edges should be selected
            # Find the shared vertex between them
            new_selected_edges = [e for e in bm.edges if e.select]
            
            if len(new_selected_edges) >= 2:
                # Get the shared vertex of the first two selected edges
                shared_verts = set(new_selected_edges[0].verts).intersection(set(new_selected_edges[1].verts))
                
                if shared_verts:
                    middle_vert = shared_verts.pop()
                    # Deselect edges, select the middle vertex
                    for e in new_selected_edges:
                        e.select = False
                    middle_vert.select = True
                    self.report({'INFO'}, f"Edge subdivided - Middle vertex selected")
                else:
                    self.report({'WARNING'}, "Could not find middle vertex")
            else:
                self.report({'WARNING'}, "Expected 2 new edges after subdivision")

            bpy.ops.mesh.select_mode(type='VERT')

        # MODE 2: Two edges (test if they form a quad-like pair)
        elif len(selected_edges) == 2 and len(selected_faces) == 0:
            edge1, edge2 = selected_edges[0], selected_edges[1]
            
            # Check if they share a vertex
            if set(edge1.verts) & set(edge2.verts):
                self.report({'WARNING'}, "Edges share a vertex - cannot rotate")
                bm.free()
                return {'CANCELLED'}
            
            # Store vertex positions BEFORE any modifications
            edge1_verts = {(edge1.verts[0].co.x, edge1.verts[0].co.y, edge1.verts[0].co.z),
                          (edge1.verts[1].co.x, edge1.verts[1].co.y, edge1.verts[1].co.z)}
            edge2_verts = {(edge2.verts[0].co.x, edge2.verts[0].co.y, edge2.verts[0].co.z),
                          (edge2.verts[1].co.x, edge2.verts[1].co.y, edge2.verts[1].co.z)}
            
            # Clear selection and select just the two edges
            bpy.ops.mesh.select_all(action='DESELECT')
            edge1.select = True
            edge2.select = True
            
            # Run shortest_path_select to select the faces/edges between them
            try:
                bpy.ops.mesh.shortest_path_select(
                    edge_mode='SELECT',
                    use_face_step=False,
                    use_topology_distance=True,
                    use_fill=True
                )
            except:
                self.report({'WARNING'}, "Could not find path between edges")
                bm.free()
                return {'CANCELLED'}
            
            # Refresh BMesh
            bm = bmesh.from_edit_mesh(mesh)
            bm.faces.ensure_lookup_table()
            
            # Check how many faces are selected
            selected_faces_count = len([f for f in bm.faces if f.select])
            
            if selected_faces_count != 2:
                self.report({'WARNING'}, f"Selected edges are too far!")
                bpy.ops.mesh.select_all(action='DESELECT')
                edge1.select = True
                edge2.select = True
                bm.free()
                return {'CANCELLED'}
           
            # Valid! Now reselect ONLY the original two edges
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # Find and select the original edges using stored vertex positions
            for e in bm.edges:
                e_verts = {(e.verts[0].co.x, e.verts[0].co.y, e.verts[0].co.z),
                          (e.verts[1].co.x, e.verts[1].co.y, e.verts[1].co.z)}
                if e_verts == edge1_verts or e_verts == edge2_verts:
                    e.select = True
            
            # Subdivide with no ngons (tris only)
            bpy.ops.mesh.subdivide(
                number_cuts=1,
                smoothness=0,
                ngon=False,
                quadcorner='INNERVERT'
            )
            
            bpy.ops.mesh.edge_rotate(use_ccw=False)
            bpy.ops.mesh.select_all(action='DESELECT')

        # MODE 3: Face(s) selected (one or more)
        elif len(selected_faces) >= 1:
            # Store original face count for reporting
            original_face_count = len(selected_faces)
            
            # If multiple faces selected, dissolve them into one face
            if len(selected_faces) > 1:
                # Dissolve the selected faces
                bpy.ops.mesh.dissolve_faces()
                
                # Refresh BMesh after dissolve operation
                bm = bmesh.from_edit_mesh(mesh)
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                
                # Get the newly created face (should be the only selected face now)
                selected_faces = [f for f in bm.faces if f.select]
                
                if not selected_faces:
                    self.report({'WARNING'}, "Failed to create single face from selection")
                    bm.free()
                    return {'CANCELLED'}
                
                self.report({'INFO'}, f"Dissolved {original_face_count} faces into 1 face")
            
            # Now handle the single face (either originally single or after dissolving)
            face = selected_faces[0]
            
            # Clear selection
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # Store original face's vertices for verification
            original_verts = set(face.verts)
            
            # Poke the face
            poke_result = bmesh.ops.poke(
                bm,
                faces=[face],
                offset=0.0,
                use_relative_offset=False
            )
            
            # The poke operation returns the new center vertex directly
            new_center_verts = [v for v in poke_result.get('verts', []) if isinstance(v, bmesh.types.BMVert)]
            
            if new_center_verts:
                center_vert = new_center_verts[0]
                
                # Verify it's not one of the original vertices
                if center_vert not in original_verts:
                    # Clear all selection
                    bpy.ops.mesh.select_all(action='DESELECT')
                    
                    # Select just the center vertex
                    center_vert.select = True
                    self.report({'INFO'}, "Face poked - Center vertex selected")
                else:
                    self.report({'WARNING'}, "Center vertex is original vertex - something wrong")
            else:
                self.report({'WARNING'}, "Poke operation didn't create new vertices")

            bpy.ops.mesh.select_mode(type='VERT')

        # MODE 4: Single boundary vertex - extrude and create triangle
        elif len(selected_verts) == 1 and len(selected_edges) == 0 and len(selected_faces) == 0:
            vert = selected_verts[0]
            
            # Check if the vertex is on a boundary
            is_boundary = False
            for edge in vert.link_edges:
                if len(edge.link_faces) == 1:
                    is_boundary = True
                    break

            if not is_boundary:
                # self.report({'WARNING'}, "Selected vertex is not on a boundary")
                # return {'CANCELLED'}

                #MODE 5: Single vert, select its edges, subdivide, triangulate
                def subdivide_selected_edges_no_ngons():
                    obj = bpy.context.active_object
                    
                    if not obj or obj.type != 'MESH':
                        print("Please select a mesh object")
                        return
                    
                    # Switch to edit mode
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    # Get bmesh
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    bm.edges.ensure_lookup_table()
                    
                    # Store the original vertex coordinates if a single vertex is selected
                    selected_verts = [v for v in bm.verts if v.select]
                    if len(selected_verts) != 1:
                        print("Please select exactly one vertex")
                        return
                    
                    # Store the vertex coordinates
                    original_vert_co = selected_verts[0].co.copy()
                    
                    # Select all edges connected to the selected vertex
                    for edge in selected_verts[0].link_edges:
                        edge.select = True
                    
                    # Update the mesh
                    bmesh.update_edit_mesh(obj.data)
                    
                    # Subdivide the selected edges
                    bpy.ops.mesh.subdivide(
                        number_cuts=1,
                        smoothness=0,
                        ngon=False
                    )
                    
                    # Triangulate
                    bpy.ops.mesh.quads_convert_to_tris()
                    
                    # Clear ALL selections (vertices, edges, faces)
                    bpy.ops.mesh.select_all(action='DESELECT')
                    
                    # Find and select the vertex by its coordinates
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    
                    # Find the vertex closest to the original coordinates
                    closest_vert = min(bm.verts, key=lambda v: (v.co - original_vert_co).length)
                    tolerance = 0.0001  # Small tolerance for floating point comparison
                    
                    if (closest_vert.co - original_vert_co).length < tolerance:
                        closest_vert.select = True
                        print(f"Original vertex selected by coordinates")
                    else:
                        print("Could not find original vertex by coordinates")
                    
                    bmesh.update_edit_mesh(obj.data)
                    
                    print("Triangle fan subdivided and triangulated")

                # Run the script
                subdivide_selected_edges_no_ngons()
                self.report({'INFO'}, "Triangle fan subdivided.")
                return {'FINISHED'}

            # Find the two boundary neighbors
            boundary_edges = [e for e in vert.link_edges if len(e.link_faces) == 1]
            
            if len(boundary_edges) != 2:
                self.report({'WARNING'}, f"Vertex has {len(boundary_edges)} boundary edges (need exactly 2)")
                bm.free()
                return {'CANCELLED'}
            
            # Get the two neighboring vertices along the boundary
            neighbor1 = boundary_edges[0].other_vert(vert)
            neighbor2 = boundary_edges[1].other_vert(vert)
            
            # Store original position
            original_pos = vert.co.copy()

            # Calculate outward direction
            dir1 = (vert.co - neighbor1.co).normalized()
            dir2 = (vert.co - neighbor2.co).normalized()
            extrude_dir = (dir1 + dir2).normalized()
            
            # Get BMesh
            bm = bmesh.from_edit_mesh(mesh)
            
            # Extrude the vertex using extrude_vert_indiv
            extrude_result = bmesh.ops.extrude_vert_indiv(bm, verts=[vert])
            new_vert = extrude_result['verts'][0]
            
            # Move the new vertex outward slightly (0.1 units)
            new_vert.co = original_pos + (extrude_dir * 0.1)
            
            bmesh.update_edit_mesh(mesh)
            
            # Create first triangle (new_vert, vert, neighbor1)
            bpy.ops.mesh.select_all(action='DESELECT')
            new_vert.select = True
            vert.select = True
            neighbor1.select = True
            bpy.ops.mesh.edge_face_add()
            
            # Create second triangle (new_vert, vert, neighbor2)
            bpy.ops.mesh.select_all(action='DESELECT')
            new_vert.select = True
            vert.select = True
            neighbor2.select = True
            bpy.ops.mesh.edge_face_add()
            
            # Move the new vertex back to original position
            new_vert.co = original_pos

            # Select just the new vertex
            bpy.ops.mesh.select_all(action='DESELECT')
            new_vert.select = True
            
            bmesh.update_edit_mesh(mesh)
            bm.free()
            
            self.report({'INFO'}, "Created two triangles - vertex is ready to move")
        elif len(selected_edges) > 2 and len(selected_faces) == 0:
            self.report({'INFO'}, "Only 2 edges should be selected.")
            return {'FINISHED'}
        else:
            self.report({'INFO'}, "No selection.")
            return {'FINISHED'}

        bmesh.update_edit_mesh(mesh)
        bm.free()
        return {'FINISHED'}

class MESH_OT_triangulate_preserve_selection(bpy.types.Operator):
    """Triangulate the entire mesh while preserving the current selection"""
    bl_idname = "mesh.triangulate_preserve_selection"
    bl_label = "Triangulate Preserve Selection"
    bl_options = {'REGISTER', 'UNDO'}
        
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        # Get BMesh
        bm = bmesh.from_edit_mesh(mesh)
        
        # Save current selection state
        # Store indices of selected vertices, edges, and faces
        selected_verts = [v.index for v in bm.verts if v.select]
        selected_edges = [e.index for e in bm.edges if e.select]
        selected_faces = [f.index for f in bm.faces if f.select]
              
        # Select everything
        for vert in bm.verts:
            vert.select = True
        for edge in bm.edges:
            edge.select = True
        for face in bm.faces:
            face.select = True
        
        # Update mesh to ensure BMesh is synchronized
        bmesh.update_edit_mesh(mesh)
        
        # Triangulate using bmesh operator
        try:
            # Use BMesh triangulate operator
            bmesh.ops.triangulate(
                bm,
                faces=bm.faces[:],
                quad_method='FIXED',
                ngon_method='BEAUTY'
            )
        except Exception as e:
            self.report({'ERROR'}, f"Triangulation failed: {str(e)}")
            return {'CANCELLED'}
        
        # Restore selection
        # First clear all selections
        for vert in bm.verts:
            vert.select = False
        for edge in bm.edges:
            edge.select = False
        for face in bm.faces:
            face.select = False
        
        # Restore vertex selection by index
        # Note: After triangulation, indices might change, so we need to be careful
        # We'll use a mapping approach for vertices (they should mostly stay the same)
        # But edges and faces will be completely different after triangulation
        
        # For vertices: restore by index (indices usually preserved)
        for vert in bm.verts:
            if vert.index in selected_verts:
                vert.select = True
        
        # For edges and faces: we can't reliably restore by index because triangulation
        # creates new edges and faces. Instead, we'll select based on original selection
        # of vertices - select all edges/faces that are made from selected vertices
        
        # Alternative approach: Select edges where both vertices are selected
        for edge in bm.edges:
            if edge.verts[0].select and edge.verts[1].select:
                edge.select = True
        
        # Select faces where all vertices are selected (or at least 3 vertices if it's a triangle)
        for face in bm.faces:
            # Count how many vertices of this face are selected
            selected_vert_count = sum(1 for vert in face.verts if vert.select)
            # For a triangle, if all 3 vertices are selected, select the face
            # For quads, if all 4 are selected, select the face
            if selected_vert_count == len(face.verts):
                face.select = True
               
        # Update the mesh view
        bmesh.update_edit_mesh(mesh)
        
        return {'FINISHED'}

class MESH_OT_keep_connected_vertex_chain(bpy.types.Operator):
    """Keep only the connected chain of vertices containing the active vertex (or nearest to 3D cursor)"""
    bl_idname = "mesh.keep_connected_vertex_chain"
    bl_label = "Keep Connected Vertex Chain"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')

    def find_nearest_selected_vertex_to_cursor(self, bm, obj):
        """Find the closest SELECTED vertex to the 3D cursor in world space"""
        cursor_loc = bpy.context.scene.cursor.location
        min_dist = float('inf')
        nearest_vert = None
        
        # Transform cursor to object local space
        matrix_world_inv = obj.matrix_world.inverted()
        cursor_local = matrix_world_inv @ cursor_loc
        
        # Only check selected vertices
        selected_verts = [v for v in bm.verts if v.select]
        
        if not selected_verts:
            return None
        
        for vert in selected_verts:
            dist = (vert.co - cursor_local).length
            if dist < min_dist:
                min_dist = dist
                nearest_vert = vert
        
        return nearest_vert

    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object is not a mesh")
            return {'CANCELLED'}
        
        current_mode = context.object.mode
        
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        # Check for active vertex
        active_elem = bm.select_history.active
        start_vert = None
        
        if active_elem and isinstance(active_elem, bmesh.types.BMVert):
            start_vert = active_elem
            self.report({'INFO'}, "Using active vertex")
        else:
            self.report({'WARNING'}, "No active vertex found, using nearest selected vertex to 3D cursor")
            start_vert = self.find_nearest_selected_vertex_to_cursor(bm, obj)
            
            if not start_vert:
                self.report({'ERROR'}, "No selected vertices found near 3D cursor")
                bm.free()
                if current_mode != 'EDIT':
                    bpy.ops.object.mode_set(mode=current_mode)
                return {'CANCELLED'}
        
        # Get all selected vertices
        selected_verts = {v for v in bm.verts if v.select}
        
        if not selected_verts:
            self.report({'WARNING'}, "No selected vertices found")
            bm.free()
            if current_mode != 'EDIT':
                bpy.ops.object.mode_set(mode=current_mode)
            return {'CANCELLED'}
        
        # Find connected vertices using flood fill
        connected_verts = set()
        verts_to_visit = {start_vert}
        
        while verts_to_visit:
            current_vert = verts_to_visit.pop()
            if current_vert in connected_verts:
                continue
                
            connected_verts.add(current_vert)
            
            # Check neighboring vertices through edges
            for edge in current_vert.link_edges:
                other_vert = edge.other_vert(current_vert)
                if other_vert in selected_verts and other_vert not in connected_verts:
                    verts_to_visit.add(other_vert)
        
        # Clear ALL selection and active state first
        bpy.ops.mesh.select_all(action='DESELECT')
        bm.select_history.clear()
        
        # Now select only the connected vertices
        for vert in connected_verts:
            vert.select = True
        
        # Set the active vertex
        bm.select_history.add(start_vert)
       
        # Update the mesh
        bmesh.update_edit_mesh(obj.data)
        bm.free()
        
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=current_mode)
        
        self.report({'INFO'}, f"Kept {len(connected_verts)} connected vertices")
        
        return {'FINISHED'}

class MESH_OT_select_faces_from_edges(bpy.types.Operator):
    """Select faces that contain the selected edges"""
    bl_idname = "mesh.select_faces_from_edges"
    bl_label = "Select Faces from Edges"
    bl_options = {'REGISTER', 'UNDO'}
       
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and 
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
    
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        # Get BMesh
        bm = bmesh.from_edit_mesh(mesh)
        
        # Get currently selected edges
        selected_edges = [e for e in bm.edges if e.select]
        
        if not selected_edges:
            self.report({'WARNING'}, "No selected edges")
            return {'CANCELLED'}
        
        # Clear current face selection only if NOT adding to selection

        for face in bm.faces:
            face.select = False
        
        # Select faces that contain any of the selected edges
        faces_selected = 0
        for edge in selected_edges:
            for face in edge.link_faces:
                if not face.select:
                    faces_selected += 1
                face.select = True
        
        # Update the mesh view
        bmesh.update_edit_mesh(mesh)
        
        return {'FINISHED'}

class MESH_OT_dissolve_triangulate(bpy.types.Operator):
    """Simplify"""
    bl_idname = "mesh.dissolve_triangulate"
    bl_label = "Dissolve Triangulate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Check if we're in edit mode and have mesh
        if context.mode != 'EDIT_MESH':
            return False
        
        # Get active object and mesh data
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        
        # Get mesh data
        mesh = obj.data
        
        # Check if we have selected faces
        bm = bmesh.from_edit_mesh(mesh)
        has_selected_faces = any(f.select for f in bm.faces)
        
        bm.free()
        
        return has_selected_faces

    def execute(self, context):

        bpy.ops.mesh.dissolve_limited(angle_limit=3.14159) 
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')       
         
        return {'FINISHED'}

class MESH_OT_tris_to_quads_subdivide_super(bpy.types.Operator):
    """Convert Tris to Quads, then Subdivide Edge Ring and Convert back to Tris"""
    bl_idname = "mesh.tris_to_quads_subdivide_super"
    bl_label = "Tris to Quads Subdivide"
    bl_options = {'REGISTER', 'UNDO'}

    use_3d_cursor: bpy.props.BoolProperty(
        name="Use 3D Cursor",
        description="Use 3D cursor to select edge (if disabled, uses active edge)",
        default=True,
        options={'SKIP_SAVE'}  # Don't save between sessions
    )
    
    topo_inf: bpy.props.BoolProperty(
        name="Topology Influence",
        description="Use topology influence",
        default=True,
        options={'SKIP_SAVE'}  # Don't save between sessions
    )    

    @classmethod
    def poll(cls, context):
        # Check if we're in edit mode and have mesh
        if context.mode != 'EDIT_MESH':
            return False
        
        # Get active object and mesh data
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        
        # Get mesh data
        mesh = obj.data
        
        # Check if we have selected faces
        bm = bmesh.from_edit_mesh(mesh)
        has_selected_faces = any(f.select for f in bm.faces)
        bm.free()
        
        return has_selected_faces

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        # Store edge location based on selected method
        if self.use_3d_cursor:
            # Method 1: Use 3D cursor
            edge_location = context.scene.cursor.location.copy()
            self.report({'INFO'}, "Using 3D cursor for edge selection")
        else:
            # Method 2: Use active edge
            bm = bmesh.from_edit_mesh(mesh)
            if not (bm.select_history and isinstance(bm.select_history.active, bmesh.types.BMEdge)):
                self.report({'ERROR'}, "No active edge found. Please select an edge as active element.")
                bm.free()
                return {'CANCELLED'}
            
            active_edge = bm.select_history.active
            # Store the edge's center position in world space
            v1 = active_edge.verts[0].co
            v2 = active_edge.verts[1].co
            edge_center_obj = (v1 + v2) / 2
            edge_location = obj.matrix_world @ edge_center_obj
            bm.free()
            self.report({'INFO'}, "Using active edge for edge selection")
        
        # Step 1: Convert tris to quads on selected faces
        if self.topo_inf:
            bpy.ops.mesh.tris_convert_to_quads(face_threshold=3.14159, shape_threshold=3.14159, topology_influence=0)
        else:
            bpy.ops.mesh.tris_convert_to_quads(face_threshold=3.14159, shape_threshold=3.14159, topology_influence=2)

        # Store the selected faces after tris to quads
        bm = bmesh.from_edit_mesh(mesh)
        selected_face_indices = [f.index for f in bm.faces if f.select]
        bm.free()

        bpy.ops.mesh.select_all(action='DESELECT')
        
        # Step 2: Find the closest edge to the stored location
        # Convert location to object space (current object transform)
        location_obj = obj.matrix_world.inverted() @ edge_location
        
        bm = bmesh.from_edit_mesh(mesh)
        
        closest_edge = None
        closest_dist = float('inf')
        
        for edge in bm.edges:
            # Get edge center
            edge_center = (edge.verts[0].co + edge.verts[1].co) / 2
            
            # Calculate distance from stored location to edge center
            dist = (location_obj - edge_center).length
            
            if dist < closest_dist:
                closest_dist = dist
                closest_edge = edge
        
        if not closest_edge:
            self.report({'ERROR'}, "No edge found near stored location after tris to quads")
            bm.free()
            return {'CANCELLED'}
        
        # Store the new edge index
        new_edge_index = closest_edge.index
        bm.free()
        
        # Step 3: Reselect the closest edge to the stored location
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.edges[new_edge_index].select = True
        bpy.ops.object.mode_set(mode='EDIT')

        # Step 4: Select edge ring
        bpy.ops.mesh.select_edge_ring_multi()
        
        # Step 5: Subdivide
        bpy.ops.mesh.subdivide(ngon=False)
        
        # Step 6: Convert quads back to tris
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        
        # Step 7: Restore the original face selection
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for face_idx in selected_face_indices:
            if face_idx < len(mesh.polygons):  # Check if face still exists
                mesh.polygons[face_idx].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Step 8: Deselect any triangles from the selection
        bm = bmesh.from_edit_mesh(mesh)
        for face in bm.faces:
            if face.select and len(face.verts) == 3:  # If it's a selected triangle
                face.select = False  # Deselect it
        bmesh.update_edit_mesh(mesh)
        bm.free()
        
        return {'FINISHED'}

class TriangleModelling(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""    
    bl_idname = "3D_PT_STC"
    bl_label = "Triangle Mesh Macros"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tris'  

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.box()
        row.operator("mesh.smart_edit_operation", text="Multitool", icon='SCULPTMODE_HLT')

        row2 = row.row()
        row2.operator("mesh.edge_rotate", text="Turn Edge", icon='MOD_SIMPLIFY').use_ccw=False

        row = layout.box()
        row.operator("mesh.dissolve_triangulate", text="Simplify", icon='MOD_DECIM')

        # row2 = row.row()
        # row2.operator("mesh.tris_to_quads_subdivide_super", text="Loopcut (Active Edge)", icon='UV_EDGESEL').use_3d_cursor = False
      
        row2 = row.row()
        row2.operator("mesh.tris_to_quads_subdivide_super", text="Loopcut (at 3D Cursor)", icon='UV_EDGESEL').use_3d_cursor = True

        row = layout.box()
        row.operator("transform.vert_slide", text="Slide", icon='MOD_HUE_SATURATION')

        row2 = row.row()
        row2.operator("mesh.vertices_smooth", text="Smooth", icon='MOD_FLUIDSIM').factor=0.5

        box = layout.box()
        row = box.row()
        row.operator("mesh.shortest_path_select", text="Select Shortest Path", icon='CON_TRACKTO').edge_mode='SELECT'

        row = box.row()
        row.operator("mesh.select_more", text="Expand Selection", icon='FULLSCREEN_ENTER')

        row = box.row()
        row.operator("mesh.select_faces_from_edges", text="Select Faces of Edge", icon='MOD_BEVEL')

        row = box.row()
        row.operator("mesh.keep_connected_vertex_chain", text="Chain of Active Vertex", icon='LINKED')

        row = box.row()
        row.operator("mesh.loop_to_region", text="Region from Loop", icon="RADIOBUT_ON").select_bigger=False

        row = box.row()
        row.operator("mesh.region_to_loop", text="Loop from Region", icon="RADIOBUT_OFF")

        row = layout.box()
        row.box().operator("mesh.triangulate_preserve_selection", text="Triangulate Mesh", icon='MOD_TRIANGULATE')
        
classes = [

TriangleModelling,
MESH_OT_tris_to_quads_subdivide_super,
MESH_OT_dissolve_triangulate,
MESH_OT_select_faces_from_edges,
MESH_OT_triangulate_preserve_selection,
MESH_OT_smart_subdivide_or_poke_or_rotate,
MESH_OT_keep_connected_vertex_chain

]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
