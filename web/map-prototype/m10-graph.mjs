export function validateSystemGraph(graph, parentIds) {
  const owners = new Set([...parentIds, ...graph.objects.map(o => o.object_id)]);
  if (!Array.isArray(graph.ports) || !graph.ports.length) throw new Error('M10 ports missing');
  const ports = new Map();
  for (const port of graph.ports) {
    if (ports.has(port.port_id) || !owners.has(port.object_id) ||
        !['in', 'out'].includes(port.direction) || !port.medium || !port.circuit_id ||
        port.position?.xyz_m?.length !== 3 || !port.position.xyz_m.every(Number.isFinite)) {
      throw new Error(`M10 invalid port: ${port.port_id}`);
    }
    ports.set(port.port_id, port);
  }
  const connections = new Set();
  for (const edge of graph.connections) {
    const a = ports.get(edge.from_port_id), b = ports.get(edge.to_port_id);
    if (!a || !b) throw new Error(`M10 connection port missing: ${edge.connection_id}`);
    const directions = edge.role === 'internal' ? ['in', 'out'] : ['out', 'in'];
    if (connections.has(edge.connection_id) || a.object_id !== edge.from_object_id || b.object_id !== edge.to_object_id ||
        a.medium !== b.medium || a.medium !== edge.medium || a.circuit_id !== b.circuit_id || a.circuit_id !== edge.circuit_id ||
        a.direction !== directions[0] || b.direction !== directions[1] || edge.execution_allowed !== false) {
      throw new Error(`M10 incompatible connection: ${edge.connection_id}`);
    }
    connections.add(edge.connection_id);
  }
  if (graph.ptes?.initial_mode !== 'IDLE' || graph.ptes?.execution_allowed !== false ||
      graph.ptes?.simultaneous_charge_discharge_allowed !== false || graph.execution_allowed !== false) {
    throw new Error('M10 PTES candidate mode invalid');
  }
}
