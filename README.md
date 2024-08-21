uzu nodegroup pack contains:
Modifiers:
  Autotools - simple shade smooth and welding
  EyeOnVertex - instance an eyeball (halved) on a vertex (group or attribute)
  FlowEdgev2 - Wireframe generator from unconnected vertices
  FollowSurface - Used by a triangle mesh that should have a child object parented by the vertex (triangle) method. This ensures the parented object follows the surface more smoothly.
  Fracture - I think it was made for lowpoly explosion (like in Starcraft Intro) when phyisics (cloth) simulation is enabled.
  geouv - simple auto uvunwrap for walls, that aren't closed.
  inverted_hull - simple alternative for Solidify method.
  lightning - simple lightning
  MapBrushCurveTool - Curve to Ground patch converter
  MirrorBreaker - deletes the other side of the geometry that was marked with MirrorMarker, put right after a Mirror Modifer.
  MirrorMarker - marks chosen geometry as mirrored, so MirrorBreaker can delete non-marked faces, even with a Mirror Modifer. Allows for non-symmetry while having the benefit of real time mirroring where it's needed. Put right before Mirror Modifier.
  MountainGenerator - simple mountain generator with unconnected vertices.
  ProximityCulling - auto deletes geometry in a radius of another mesh. 
  VertexLighting_Reciever - used with a Vertex Lamp attribute (Source) and shader.

NodeTools:
  FaceSets (FS)
    Assign - Assign selected faces to a set up to 4 (can be increased)
    Clear - Clears selected faces from all face sets.
    Regenerate - Face sets can be generated to the other side
