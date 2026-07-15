import React, { useMemo, useState, useCallback } from 'react';
import ReactFlow, { Background, Controls, ConnectionMode, applyNodeChanges, applyEdgeChanges, addEdge } from 'reactflow';
import type { Node, Edge, NodeChange, EdgeChange, Connection } from 'reactflow';
import 'reactflow/dist/style.css';
import { useStore } from '../store/useStore';
import { CircuitNode } from './CircuitNode';
import { BackgroundNode } from './BackgroundNode';

const nodeTypes = {
  component: CircuitNode,
  background: BackgroundNode,
};

export const CircuitViewer: React.FC<{ nodes: Node[], edges: Edge[], onNodesChange?: (changes: NodeChange[]) => void }> = ({ nodes, edges, onNodesChange: externalOnNodesChange }) => {
  const { 
    highlightedElements, 
    activeOverlays, 
    toggleOverlay,
    setAllOverlays,
    activeLoopId, setActiveLoopId,
    activeNodeId, setActiveNodeId,
    hoveredElementId,
    simulationData, 
    analysisData,
    setSelectedComponentId,
    addWireBetween,
    removeWireBetween,
  } = useStore();

  // Determine which elements should be dimmed based on overlays
  const activeLoop = useMemo(() => {
    if (!activeOverlays.kvlLoops || !activeLoopId || !analysisData?.topology?.loops) return null;
    return analysisData.topology.loops.find((l: any) => l.id === activeLoopId) || null;
  }, [activeOverlays.kvlLoops, activeLoopId, analysisData]);

  const activeNode = useMemo(() => {
    if (!activeOverlays.kclNodes || !activeNodeId || !analysisData?.topology?.nodes) return null;
    return analysisData.topology.nodes.find((n: any) => n.id === activeNodeId) || null;
  }, [activeOverlays.kclNodes, activeNodeId, analysisData]);

  // Apply glowing effects and voltages based on global state
  const styledNodes = useMemo(() => {
    return nodes.map(node => {
      const isDirectlyHighlighted = highlightedElements.some(e => e.type === 'component' && e.id === node.id);
      const isHovered = hoveredElementId === node.id;

      let isDimmed = false;
      let isInLoop = false;
      let isInNode = false;
      
      if (activeLoop) {
        isInLoop = activeLoop.components.includes(node.id);
        if (!isInLoop) isDimmed = true;
      }
      
      if (activeNode) {
        const connectedComps = activeNode.pins ? activeNode.pins.map((p: string) => p.split('.')[0]) : [];
        isInNode = connectedComps.includes(node.id);
        if (!isInNode) isDimmed = true;
      }

      if ((activeOverlays.kvlLoops && !activeLoop) || (activeOverlays.kclNodes && !activeNode)) {
          isDimmed = true;
      }

      return {
        ...node,
        data: {
          ...node.data,
          isHighlighted: isDirectlyHighlighted || isHovered || isInLoop || isInNode,
          isDimmed,
          activeOverlays,
        },
        style: {
          opacity: isDimmed ? 0.3 : 1,
          transition: 'opacity 0.3s'
        }
      };
    });
  }, [nodes, highlightedElements, hoveredElementId, activeLoop, activeNode, activeOverlays]);

  const styledEdges = useMemo(() => {
    return edges.map(edge => {
      let strokeColor = '#3b82f6';
      let isAnimated = false;
      let strokeWidth = 2;
      let isDimmed = false;

      if (activeLoop) {
        if (!activeLoop.components.includes(edge.source) && !activeLoop.components.includes(edge.target)) {
          isDimmed = true;
        } else {
          strokeColor = '#f59e0b'; // Amber for KVL loop
          strokeWidth = 3;
          isAnimated = true; // Animate voltage drops
        }
      }
      
      if (activeNode) {
         const connectedComps = activeNode.pins ? activeNode.pins.map((p: string) => p.split('.')[0]) : [];
         const edgeTouchesNode = connectedComps.includes(edge.source) || connectedComps.includes(edge.target);
         if (!edgeTouchesNode) {
           isDimmed = true;
         } else {
           strokeColor = '#a855f7'; // Purple for KCL node
           strokeWidth = 3;
           isAnimated = true; // Show incoming/outgoing currents
         }
      }

      if ((activeOverlays.kvlLoops && !activeLoop) || (activeOverlays.kclNodes && !activeNode)) {
          isDimmed = true;
      }

      // Current Flow Mode
      if (activeOverlays.currentFlow) {
        isAnimated = true;
        if (!activeLoop && !activeNode) strokeColor = '#22d3ee';
        strokeWidth = 3;
      }
      
      if (activeOverlays.nodeVoltages && !activeLoop && !activeNode) {
        strokeColor = '#ef4444'; // Red for voltage mode
      }

      // Selection highlight
      if (edge.selected) {
        strokeColor = '#ec4899'; // Pink highlighting
        strokeWidth = 4;
        isDimmed = false;
      }
      
      return {
        ...edge,
        animated: isAnimated,
        interactionWidth: 20, // Increases the click/hover area
        style: { 
          stroke: strokeColor, 
          strokeWidth,
          opacity: isDimmed ? 0.1 : 1,
          transition: 'all 0.3s'
        },
      };
    });
  }, [edges, activeOverlays, simulationData, activeLoop, activeNode, activeNodeId]);

  // Make edges deletable
  const deletableEdges = useMemo(() => {
    return styledEdges.map(edge => ({ ...edge, deletable: true }));
  }, [styledEdges]);

  // Handle node position changes (drag)
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    if (externalOnNodesChange) externalOnNodesChange(changes);
  }, [externalOnNodesChange]);

  // Handle edge deletions
  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    for (const change of changes) {
      if (change.type === 'remove') {
        const edge = styledEdges.find(e => e.id === change.id);
        if (edge) {
          removeWireBetween(edge.source, edge.target, edge.sourceHandle || undefined, edge.targetHandle || undefined);
        }
      }
    }
  }, [styledEdges, removeWireBetween]);

  // Handle new connections
  const onConnect = useCallback((connection: Connection) => {
    if (connection.source && connection.target) {
      addWireBetween(connection.source, connection.target, connection.sourceHandle || undefined, connection.targetHandle || undefined);
    }
  }, [addWireBetween]);

  const fitViewOptions = { padding: 0.3, maxZoom: 1.5, minZoom: 0.3 };

  return (
    <div className="w-full h-full relative bg-slate-950">
      {/* Top Overlay Controls */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-slate-900/90 backdrop-blur-md p-2 rounded-xl border border-slate-700 shadow-2xl flex gap-2 items-center">
        <button 
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${!Object.values(activeOverlays).some(Boolean) ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}`}
          onClick={() => setAllOverlays({currentFlow:false, nodeVoltages:false, kvlLoops:false, kclNodes:false, equations:false})}
        >Standard</button>
        <div className="w-px h-6 bg-slate-700 mx-1"></div>
        <button 
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${activeOverlays.currentFlow ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}`}
          onClick={() => toggleOverlay('currentFlow')}
        >Current Flow</button>
        <button 
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${activeOverlays.nodeVoltages ? 'bg-red-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}`}
          onClick={() => toggleOverlay('nodeVoltages')}
        >Node Voltages</button>
        
        <div className="flex items-center gap-1 bg-slate-800 rounded-md p-0.5 border border-slate-700 focus-within:border-amber-500 transition-colors">
          <button 
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${activeOverlays.kvlLoops ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-white'}`}
            onClick={() => {
              toggleOverlay('kvlLoops');
              if (!activeLoopId && analysisData?.topology?.loops?.[0]) {
                setActiveLoopId(analysisData.topology.loops[0].id);
              }
            }}
          >KVL Loops</button>
          {activeOverlays.kvlLoops && analysisData?.topology?.loops && (
             <select 
               className="bg-transparent text-xs text-white outline-none pr-2 cursor-pointer font-mono"
               value={activeLoopId || ''}
               onChange={(e) => setActiveLoopId(e.target.value)}
             >
               <option value="" className="bg-slate-800">Select Loop</option>
               {analysisData.topology.loops.map((l: any) => (
                 <option key={l.id} value={l.id} className="bg-slate-800">{l.id}</option>
               ))}
             </select>
          )}
        </div>

        <div className="flex items-center gap-1 bg-slate-800 rounded-md p-0.5 border border-slate-700 focus-within:border-purple-500 transition-colors">
          <button 
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${activeOverlays.kclNodes ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'}`}
            onClick={() => {
              toggleOverlay('kclNodes');
              if (!activeNodeId && analysisData?.topology?.nodes?.[0]) {
                setActiveNodeId(analysisData.topology.nodes[0].id);
              }
            }}
          >KCL Nodes</button>
          {activeOverlays.kclNodes && analysisData?.topology?.nodes && (
             <select 
               className="bg-transparent text-xs text-white outline-none pr-2 cursor-pointer font-mono"
               value={activeNodeId || ''}
               onChange={(e) => setActiveNodeId(e.target.value)}
             >
               <option value="" className="bg-slate-800">Select Node</option>
               {analysisData.topology.nodes.map((n: any) => (
                 <option key={n.id} value={n.id} className="bg-slate-800">{n.id}</option>
               ))}
             </select>
          )}
        </div>

        <div className="w-px h-6 bg-slate-700 mx-1"></div>
        <button 
          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${activeOverlays.equations ? 'bg-emerald-600 text-white shadow-[0_0_15px_rgba(5,150,105,0.4)]' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}`}
          onClick={() => toggleOverlay('equations')}
        >Equation Overlay</button>
      </div>

      <ReactFlow
        nodes={styledNodes}
        edges={deletableEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          setSelectedComponentId(node.id);
        }}
        onPaneClick={() => {
          setSelectedComponentId(null);
        }}
        onConnect={onConnect}
        deleteKeyCode={['Backspace', 'Delete']}
        fitView
        fitViewOptions={fitViewOptions}
        connectionMode={ConnectionMode.Loose}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{ type: 'step', interactionWidth: 20 }}
        nodesDraggable={true}
        nodesConnectable={true}
        snapToGrid={true}
        snapGrid={[20, 20]}
      >
        <Background color="var(--nixt-border)" gap={20} size={2} />
        <Controls className="bg-[#1C1A24] border-[var(--nixt-border)] fill-[var(--nixt-text-dim)]" />
      </ReactFlow>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none w-full flex justify-center">
        <p className="bg-slate-900/80 backdrop-blur-sm text-slate-400 text-xs px-4 py-2 rounded-full border border-slate-800 shadow-sm flex items-center gap-2 max-w-2xl text-center">
          <span className="text-cyan-500 font-semibold shrink-0">Tip:</span> You can manually connect components, or select a wire and press <kbd className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700">Backspace</kbd> to delete it.
        </p>
      </div>
    </div>
  );
};
