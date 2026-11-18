// Public-data screening in metres; this does not perform survey registration.
const same = (a,b) => a[0] === b[0] && a[1] === b[1];
const sub = (a,b) => [a[0]-b[0],a[1]-b[1]];
const cross = (a,b) => a[0]*b[1]-a[1]*b[0];
const dot = (a,b) => a[0]*b[0]+a[1]*b[1];
const mix = (a,b,t) => a.map((n,i)=>n+(b[i]-n)*t);

function pointSegment(p,a,b) {
  const v=sub(b,a), t=dot(v,v) ? Math.max(0,Math.min(1,dot(sub(p,a),v)/dot(v,v))) : 0;
  const q=mix(a,b,t); return {distance:Math.hypot(...sub(p,q)),point:q};
}
export function segmentClosest(a,b,c,d) {
  const ab=sub(b,a),cd=sub(d,c),ac=sub(c,a),denom=cross(ab,cd);
  if(Math.abs(denom)>1e-12) {
    const t=cross(ac,cd)/denom,u=cross(ac,ab)/denom;
    if(t>=0&&t<=1&&u>=0&&u<=1){const point=mix(a,b,t);return {distance:0,onRoute:point,onFeature:point};}
  }
  const candidates=[...[[a,c,d],[b,c,d]].map(([p,x,y])=>{const q=pointSegment(p,x,y);return {distance:q.distance,onRoute:p,onFeature:q.point};}),
    ...[[c,a,b],[d,a,b]].map(([p,x,y])=>{const q=pointSegment(p,x,y);return {distance:q.distance,onRoute:q.point,onFeature:p};})];
  return candidates.reduce((best,q)=>q.distance<best.distance?q:best);
}
function edges(line) { return line.slice(1).map((p,i)=>[line[i],p]); }

export function assembleRings(parts) {
  const remaining=parts.map(part=>part.map(p=>[...p])),rings=[];
  if(remaining.some(p=>p.length<2))throw new Error('Missing multipolygon member geometry');
  while(remaining.length) {
    const ring=remaining.shift();
    while(!same(ring[0],ring.at(-1))) {
      const matches=remaining.map((part,i)=>({i,part,reverse:same(part.at(-1),ring.at(-1))}))
        .filter(({part})=>same(part[0],ring.at(-1))||same(part.at(-1),ring.at(-1)));
      if(matches.length!==1)throw new Error(`Open or ambiguous multipolygon ring: ${matches.length} continuations`);
      const {i,part,reverse}=matches[0];remaining.splice(i,1);
      ring.push(...(reverse?[...part].reverse():part).slice(1));
    }
    if(ring.length<4)throw new Error('Degenerate water ring');
    rings.push(ring);
  }
  return rings;
}

export function pointInRing(point,ring) {
  let inside=false;
  for(const [a,b] of edges(ring)) {
    if(pointSegment(point,a,b).distance<1e-8)return true;
    if((a[1]>point[1])!==(b[1]>point[1])&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }
  return inside;
}
export function pointInWater(point,polygons) {
  return polygons.some(([outer,...holes])=>pointInRing(point,outer)&&!holes.some(hole=>pointInRing(point,hole)));
}
export function waterLocation(point,polygons) {
  if(pointInWater(point,polygons))return 'water_area';
  if(polygons.some(([outer,...holes])=>pointInRing(point,outer)&&holes.some(hole=>pointInRing(point,hole))))return 'inner_exclusion';
  return 'outside_outer';
}

export function waterPolygons(element,project=p=>p) {
  const coords=geometry=>{
    if(!geometry?.length||geometry.some(p=>!Number.isFinite(p.lon)||!Number.isFinite(p.lat)))throw new Error(`Missing water geometry ${element.type}/${element.id}`);
    return geometry.map(p=>project([p.lon,p.lat]));
  };
  if(element.type==='way')return assembleRings([coords(element.geometry)]).map(ring=>[ring]);
  if(element.type!=='relation'||element.tags?.type!=='multipolygon')throw new Error(`Unsupported water element ${element.type}/${element.id}`);
  const parts={outer:[],inner:[]};
  for(const member of element.members||[]) {
    if(member.type!=='way'||!(member.role in parts))throw new Error(`Unsupported water member ${element.id}/${member.ref}/${member.role}`);
    parts[member.role].push(coords(member.geometry));
  }
  const outers=assembleRings(parts.outer),inners=assembleRings(parts.inner),polygons=outers.map(outer=>[outer]);
  if(!outers.length)throw new Error(`Missing water outer ${element.id}`);
  for(const hole of inners) {
    const parents=outers.map((outer,i)=>({outer,i})).filter(({outer})=>pointInRing(hole[0],outer));
    if(parents.length!==1)throw new Error(`Unassigned or ambiguous inner ${element.id}`);
    polygons[parents[0].i].push(hole);
  }
  return polygons;
}

export function observeLine(line,feature) {
  const routeEdges=line.length===1?[[line[0],line[0]]]:edges(line);
  const boundaries=feature.polygons?feature.polygons.flat():[feature.line];
  let best={distance:Infinity};
  for(const boundary of boundaries)for(const [c,d] of edges(boundary))for(const [a,b] of routeEdges) {
    const q=segmentClosest(a,b,c,d);if(q.distance<best.distance)best=q;
    if(best.distance===0)break;
  }
  if(!Number.isFinite(best.distance))throw new Error('No measurable public geometry');
  const inside=feature.polygons ? line.find(point=>pointInWater(point,feature.polygons)) : undefined;
  const contained=inside&&best.distance>=1e-8;
  return {...best,boundaryDistance:best.distance,distance:contained?0:best.distance,
    onRoute:contained?inside:best.onRoute,onFeature:contained?inside:best.onFeature,
    relation:best.distance<1e-8?'boundary_or_line_intersection':inside?'inside_water_area':'outside'};
}

export function observePad(ring,feature) {
  if(!feature.polygons)throw new Error('Pad screening requires a water polygon');
  const boundary=observeLine(ring,feature);
  if(boundary.distance===0)return boundary;
  const enclosed=feature.polygons.map(([outer])=>outer[0]).find(p=>pointInRing(p,ring));
  return enclosed?{distance:0,boundaryDistance:boundary.boundaryDistance,onRoute:enclosed,onFeature:enclosed,relation:'water_area_within_display_pad'}:boundary;
}
