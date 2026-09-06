import React, { useRef, useEffect } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

export default function GraphView({ nodes = [], relationships = [] }){
  const fgRef = useRef()
  // convert to force-graph format, ensuring links only reference existing nodes
  const nodeIds = new Set(nodes.map(n=>n.id.toString()))
  const validLinks = relationships
    .filter(r => r && nodeIds.has(r.source_node_id.toString()) && nodeIds.has(r.target_node_id.toString()))
    .map(r => ({
      source: r.source_node_id.toString(),
      target: r.target_node_id.toString(),
      type: r.relationship_type
    }))

  const data = {
    nodes: nodes.map(n=>({ id: n.id.toString(), name: n.label, group: n.node_type })),
    links: validLinks
  }

  useEffect(()=>{
    if(fgRef.current) fgRef.current.d3Force('charge').strength(-100)
  },[])

  return <ForceGraph2D ref={fgRef} graphData={data} nodeLabel={n=>n.name} linkDirectionalArrowLength={4} linkDirectionalArrowRelPos={1} />
}
