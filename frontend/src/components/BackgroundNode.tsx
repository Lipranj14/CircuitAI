import type { NodeProps } from 'reactflow';
import { useStore } from '../store/useStore';

export function BackgroundNode({ data }: NodeProps) {
  const { uploadedImage } = useStore();
  const { bgOpacity = 0.5 } = data || {};

  if (!uploadedImage) return null;

  return (
    <div 
      className="pointer-events-none"
      style={{ opacity: bgOpacity }}
    >
      <img 
        src={uploadedImage} 
        alt="Reference Circuit" 
        className="max-w-none origin-top-left"
        style={{
          transform: `scale(2.0)`, // Matches SCALE in App.tsx
          imageRendering: 'pixelated'
        }}
      />
    </div>
  );
}
