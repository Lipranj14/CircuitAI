import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import { componentSVGs } from '../assets/symbols';

const handleStyle: React.CSSProperties = {
  width: 12,
  height: 12,
  background: '#22d3ee',
  border: '3px solid #0e7490',
  boxShadow: '0 0 10px rgba(34,211,238,0.5)',
  cursor: 'crosshair',
};

export function CircuitNode({ data, selected }: NodeProps) {
  const componentType = (data?.componentType || 'resistor').toLowerCase();
  const svg = componentSVGs[componentType];

  // Simulation data overlay
  const voltage = data?.voltage;
  const current = data?.current;
  const hasSimData = voltage !== undefined || current !== undefined;
  const isHighlighted = data?.isHighlighted;
  const componentValue = data?.value;

  let highlightClass = '';
  if (isHighlighted) highlightClass = 'ring-4 ring-cyan-400 ring-offset-2 ring-offset-slate-900 rounded-md bg-cyan-900/30';

  const activeOverlays = data?.activeOverlays || {};
  
  // Advanced Visualizations
  let visualizationStyle: React.CSSProperties = {};
  if (activeOverlays.nodeVoltages && voltage !== undefined) {
      const v = typeof voltage === 'number' ? voltage : 0;
      if (Math.abs(v) > 0.1) {
          visualizationStyle.color = '#ef4444';
          highlightClass += ' shadow-[0_0_15px_rgba(239,68,68,0.3)] bg-red-900/20';
      } else {
          visualizationStyle.color = '#3b82f6';
      }
  }

  return (
    <div
      className={`circuit-node ${selected ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-900' : ''} ${hasSimData ? 'has-sim-data' : ''} ${highlightClass} transition-all duration-300 p-2 rounded-lg cursor-pointer hover:bg-slate-800/80`}
      data-component-type={componentType}
      style={visualizationStyle}
    >
      {/* LEFT handles */}
      <Handle type="target" position={Position.Left} id="left" style={handleStyle} />
      <Handle type="source" position={Position.Left} id="left" style={{ ...handleStyle, opacity: 0, pointerEvents: 'all' }} />

      {/* TOP handles */}
      <Handle type="target" position={Position.Top} id="top" style={handleStyle} />
      <Handle type="source" position={Position.Top} id="top" style={{ ...handleStyle, opacity: 0, pointerEvents: 'all' }} />

      <div className="node-symbol">
        {svg || <div className="node-fallback-icon">{componentType[0]?.toUpperCase()}</div>}
      </div>
      <div className="node-label">{data.label}</div>

      {/* Component value badge (always shown when available) */}
      {componentValue && !hasSimData && (
        <div className="text-[9px] font-mono text-cyan-300/80 bg-cyan-950/40 px-1.5 py-0.5 rounded mt-0.5 text-center border border-cyan-900/30">
          {componentValue}
        </div>
      )}

      {hasSimData && (
        <div className="sim-overlay">
          {voltage !== undefined && (
            <span className="sim-voltage">{typeof voltage === 'number' ? voltage.toFixed(2) : voltage}V</span>
          )}
          {current !== undefined && (
            <span className="sim-current">{typeof current === 'number' ? (current * 1000).toFixed(2) : current}mA</span>
          )}
        </div>
      )}

      {/* RIGHT handles */}
      <Handle type="source" position={Position.Right} id="right" style={handleStyle} />
      <Handle type="target" position={Position.Right} id="right" style={{ ...handleStyle, opacity: 0, pointerEvents: 'all' }} />

      {/* BOTTOM handles */}
      <Handle type="source" position={Position.Bottom} id="bottom" style={handleStyle} />
      <Handle type="target" position={Position.Bottom} id="bottom" style={{ ...handleStyle, opacity: 0, pointerEvents: 'all' }} />
    </div>
  );
}
