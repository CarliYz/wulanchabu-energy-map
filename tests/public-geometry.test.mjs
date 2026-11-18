import test from 'node:test';
import assert from 'node:assert/strict';
import {assembleRings,waterPolygons,pointInWater,waterLocation,observeLine,observePad,segmentClosest} from '../src/map_v2/public_geometry.mjs';
const ring=[[0,0],[200,0],[200,200],[0,200],[0,0]];
const geom=points=>points.map(([lon,lat])=>({lon,lat}));

test('a water relation without top-level geometry retains its outer and island',()=>{
  const island=[[80,80],[120,80],[120,120],[80,120],[80,80]];
  const polygons=waterPolygons({type:'relation',id:7,tags:{type:'multipolygon'},members:[
    {type:'way',ref:1,role:'outer',geometry:geom(ring)},
    {type:'way',ref:2,role:'inner',geometry:geom(island)}]});
  assert.equal(polygons.length,1);assert.equal(polygons[0].length,2);
  assert.equal(pointInWater([20,20],polygons),true);assert.equal(pointInWater([100,100],polygons),false);
  assert.equal(waterLocation([100,100],polygons),'inner_exclusion');
});
test('a line entirely in water is an overlap even when both banks exceed 30m',()=>{
  const result=observeLine([[90,90],[110,110]],{polygons:[[ring]]});
  assert.equal(result.relation,'inside_water_area');assert.equal(result.distance,0);assert.equal(result.boundaryDistance,90);
});
test('a line on an island is not classified as water containment',()=>{
  const hole=[[40,40],[160,40],[160,160],[40,160],[40,40]];
  const result=observeLine([[90,90],[110,110]],{polygons:[[ring,hole]]});
  assert.equal(result.relation,'outside');assert.equal(result.distance,50);
});
test('crossing a water boundary reports the actual intersection position',()=>{
  const result=observeLine([[-20,50],[20,50]],{polygons:[[ring]]});
  assert.equal(result.distance,0);assert.deepEqual(result.onRoute,[0,50]);
  assert.deepEqual(segmentClosest([-20,50],[20,50],[0,0],[0,200]).onRoute,[0,50]);
});
test('split and reversed members assemble while missing members fail explicitly',()=>{
  assert.deepEqual(assembleRings([[[0,0],[10,0]],[[10,10],[10,0]],[[10,10],[0,10],[0,0]]]),[[[0,0],[10,0],[10,10],[0,10],[0,0]]]);
  assert.throws(()=>assembleRings([[[0,0],[10,0]]]),/Open or ambiguous/);
  assert.throws(()=>waterPolygons({type:'way',id:3}),/Missing water geometry/);
});
test('collinear and zero-length segments return finite closest positions',()=>{
  assert.equal(segmentClosest([0,0],[10,0],[5,0],[15,0]).distance,0);
  assert.equal(segmentClosest([0,0],[0,0],[2,0],[3,0]).distance,2);
});
test('a small pond wholly enclosed by a display pad is still an overlap',()=>{
  const pond=[[90,90],[110,90],[110,110],[90,110],[90,90]];
  const result=observePad(ring,{polygons:[[pond]]});
  assert.equal(result.distance,0);assert.equal(result.relation,'water_area_within_display_pad');
});
