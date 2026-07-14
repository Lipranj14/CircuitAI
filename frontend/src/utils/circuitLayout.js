import ELK from 'elkjs/lib/elk.bundled.js'

const elk = new ELK()

export async function layoutCircuit(components, connections) {
  const graph = {
    id: "root",
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.spacing.nodeNode': '60',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80'
    },
    children: components.map(c => ({
      id: c.id,
      width: 100,
      height: 80
    })),
    edges: connections.map(conn => ({
      id: `edge-${conn.from}-${conn.to}`,
      sources: [conn.from.split('.')[0]],
      targets: [conn.to.split('.')[0]]
    }))
  }

  const layout = await elk.layout(graph)

  // Return a map of component ID to x,y position
  const positions = {}
  for (const node of layout.children) {
    positions[node.id] = { x: node.x, y: node.y }
  }
  return positions
}
