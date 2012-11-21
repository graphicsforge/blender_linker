import bpy
import os
import sys
import re
import json
import math
from mathutils import *

# These are the input variables
# TODO change the tolerance depending on your printer/filament
linkThickness = 3
tolerance = .45
centerLength = 0

femaleWidth = 2
femaleLength = linkThickness+tolerance/2

maleWidth = 2
maleLength = linkThickness+tolerance/2

insetDiameter = .5*linkThickness
epsilon = 0.01

# clear out the arena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# the boolean modifier
def booleanObjects(parent, child, mode):
  bpy.ops.object.select_all(action='DESELECT')
  bpy.context.scene.objects.active=parent
  # add modifier
  mod = bpy.ops.object.modifier_add(type='BOOLEAN')
  parent.modifiers[0].object = child 
  parent.modifiers[0].operation = mode 
  # apply modifier
  bpy.ops.object.modifier_apply(apply_as='DATA', modifier=parent.modifiers[0].name)
  # clean up child
  bpy.ops.object.select_all(action='DESELECT')
  child.select=True
  bpy.ops.object.delete(use_global=False)

# make a cylinder and throw it on its side
def makeCylinder():
  bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=.5, depth=1)
  cylinder = bpy.data.objects['Cylinder']
  bpy.ops.object.select_all(action='DESELECT')
  cylinder.select=True
  bpy.ops.transform.rotate(value=(1.5708,), axis=(1,0,0))
  bpy.ops.object.transform_apply(rotation=True)
  return cylinder

def cleanup():
  bpy.ops.object.mode_set(mode='EDIT')
  bpy.ops.mesh.remove_doubles(mergedist=epsilon)
  bpy.ops.object.mode_set(mode='OBJECT')

# make a rectangle that is rounded on both ends
def makeRoundedBox(length, width, inset, outset, adapterWidth):
  frontCap=makeCylinder()
  frontCap.name='frontCap'
  bpy.ops.transform.resize(value=(linkThickness, width, linkThickness))
  bpy.ops.object.transform_apply(scale=True)

  backCap=makeCylinder()
  backCap.name='backCap'
  bpy.ops.transform.resize(value=(linkThickness, width+abs(adapterWidth), linkThickness))
  bpy.ops.object.transform_apply(scale=True)
  for vertex in backCap.data.vertices:
    vertex.co[1]+=adapterWidth/2
    vertex.co[0]-=length
  booleanObjects( frontCap, backCap, 'UNION' )

  if length>1:
    bpy.ops.mesh.primitive_cube_add(location=(0,0,0))
    body = bpy.data.objects['Cube']
    body.name='body'
    bpy.ops.object.select_all(action='DESELECT')
    body.select=True
    bpy.ops.transform.resize(value=(length/2, width/2, linkThickness/2))
    bpy.ops.object.transform_apply(scale=True)
    for vertex in body.data.vertices:
      vertex.co[0]-=length/2
    booleanObjects( body, frontCap, 'UNION' )
  else:
    body = frontCap;
    body.name='body'

  if inset:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, size=.5, location=(0, 0, 0))
    bpy.ops.transform.translate(value=(0, width/2-epsilon, 0))
    bpy.ops.transform.resize(value=(insetDiameter+.3, insetDiameter+.3, insetDiameter+.3))
    booleanObjects( body, bpy.data.objects['Sphere'], 'DIFFERENCE' )
    if length>linkThickness+tolerance:
      bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=(insetDiameter-tolerance)/2, depth=linkThickness)
      bpy.ops.transform.translate(value=(-insetDiameter, width/2-epsilon, -linkThickness/2+epsilon))
      bpy.ops.transform.rotate(value=(1.5708/2,), axis=(0,1,0))
      booleanObjects( body, bpy.data.objects['Cylinder'], 'DIFFERENCE' )
  if outset:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, size=.5, location=(0, 0, 0))
    bpy.ops.transform.translate(value=(-length, -width/2+epsilon, 0))
    if adapterWidth<0:
      bpy.ops.transform.translate(value=(0, adapterWidth, 0))
    bpy.ops.transform.resize(value=(insetDiameter, insetDiameter, insetDiameter))
    booleanObjects( body, bpy.data.objects['Sphere'], 'UNION' )
  body.select=True
  return body

# make two rounded boxes, mirrored in y
def makePanel(length, innerRadius, width, inset, outset, adapterWidth):
  panel = makeRoundedBox(length, width, inset, outset, adapterWidth)
  bpy.ops.transform.translate(value=(0, innerRadius+width/2, 0))
  bpy.ops.object.transform_apply(location=True)
  panel.select=True
  bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'})
  bpy.ops.transform.resize(value=(1, -1, 1))
  panel.select=True
  bpy.data.objects['body.001'].select=True
  bpy.ops.object.join()
  bpy.ops.object.editmode_toggle()
  bpy.ops.mesh.normals_make_consistent(inside=False)
  bpy.ops.object.editmode_toggle()
  return bpy.data.objects['body.001']

# make a single link
def makeLink( centerLength, femaleWidth, maleLength, maleWidth, adapterWidth ):
  maleAdapter = 0
  femaleAdapter = 0
  if adapterWidth>0:
    maleAdapter = tolerance+adapterWidth/2;
  elif adapterWidth==0:
    maleAdapter = tolerance;
  else:
    femaleAdapter = tolerance+adapterWidth/2;
  inside = makePanel( maleLength, epsilon/2, maleWidth/2, True, False, maleAdapter )
  inside.name='inside'
  outside = makePanel( femaleLength+centerLength, maleWidth/2+maleAdapter+epsilon, femaleWidth, False, True, femaleAdapter )
  outside.name='outside'
  bpy.ops.transform.translate(value=(-femaleLength-maleLength+linkThickness+tolerance/2, 0, 0))
  bpy.ops.object.select_all(action='DESELECT')
  if centerLength>linkThickness*2:
    padding2 = makePanel( epsilon, epsilon/2, maleWidth/2+tolerance, False, False, 0 )
    padding2.name='padding2'
    bpy.ops.transform.translate(value=(-centerLength-maleLength, 0, 0))
    padding2.select=True

  inside.select=True
  outside.select=True
  bpy.ops.object.join()
  bpy.ops.object.editmode_toggle()
  bpy.ops.mesh.normals_make_consistent(inside=False)
  bpy.ops.object.editmode_toggle()
  bpy.ops.transform.translate(value=(0, 0, linkThickness/2))
  return outside

# Here you do the stuff!!

# centerLength is how long you want each of the individual links to be
# femaleWidth is how wide you want the outside of the joint to be
# maleLength is how long you want the inner joint to stick out
# maleWidth is how wide you want the inner joint to be
# the last argument, the adapterWidth, is the maleWidth difference between the current link and the next link

makeLink(centerLength, femaleWidth, maleLength, maleWidth, 0).select=True

# walk in the positive direction, making links
offset = centerLength+maleLength+femaleLength
for i in range(1, 5):
  global offset
  makeLink(centerLength, femaleWidth, maleLength, maleWidth+i*2, -2).select=True
  bpy.ops.transform.translate(value=(offset, 0, 0))
  offset = offset+centerLength+maleLength+femaleLength

# if you want, you can finish off with something with a longer maleLength so that it is easier to attach/detatch
i=5
makeLink(centerLength, femaleWidth, maleLength+linkThickness/2, maleWidth+i*2, -2).select=True
bpy.ops.transform.translate(value=(offset+linkThickness/2, 0, 0))

# walk in the negative direction
offset = -(centerLength+maleLength+femaleLength)
for i in range(1, 6):
  global offset
  makeLink(centerLength, femaleWidth, maleLength, maleWidth+(i-1)*2, 2).select=True
  bpy.ops.transform.translate(value=(offset, 0, 0))
  offset -= centerLength+maleLength+femaleLength

# once you're done, just join everything together
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
