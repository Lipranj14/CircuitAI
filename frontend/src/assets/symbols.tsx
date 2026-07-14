export const componentSVGs: Record<string, any> = {
  resistor: (
    <svg width="80" height="40" viewBox="0 0 80 40">
      <line x1="0" y1="20" x2="15" y2="20" stroke="currentColor" strokeWidth="2"/>
      <polyline points="15,20 20,8 28,32 36,8 44,32 52,8 60,32 65,20" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="65" y1="20" x2="80" y2="20" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  battery: (
    <svg width="60" height="40" viewBox="0 0 60 40">
      <line x1="0" y1="20" x2="22" y2="20" stroke="currentColor" strokeWidth="2"/>
      <line x1="22" y1="6" x2="22" y2="34" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="30" y1="12" x2="30" y2="28" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="38" y1="6" x2="38" y2="34" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="38" y1="20" x2="60" y2="20" stroke="currentColor" strokeWidth="2"/>
      <text x="24" y="5" fontSize="8" fill="#22d3ee" fontFamily="monospace">+</text>
    </svg>
  ),
  voltage_source: (
    <svg width="60" height="50" viewBox="0 0 60 50">
      <line x1="0" y1="25" x2="12" y2="25" stroke="currentColor" strokeWidth="2"/>
      <circle cx="30" cy="25" r="16" fill="none" stroke="currentColor" strokeWidth="2"/>
      <text x="22" y="22" fontSize="10" fill="#22d3ee" fontFamily="monospace">+</text>
      <text x="32" y="32" fontSize="10" fill="#94a3b8" fontFamily="monospace">−</text>
      <line x1="46" y1="25" x2="60" y2="25" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  capacitor: (
    <svg width="60" height="40" viewBox="0 0 60 40">
      <line x1="0" y1="20" x2="24" y2="20" stroke="currentColor" strokeWidth="2"/>
      <line x1="24" y1="6" x2="24" y2="34" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="36" y1="6" x2="36" y2="34" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="36" y1="20" x2="60" y2="20" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  inductor: (
    <svg width="80" height="40" viewBox="0 0 80 40">
      <line x1="0" y1="20" x2="12" y2="20" stroke="currentColor" strokeWidth="2"/>
      <path d="M12,20 C12,10 22,10 22,20 C22,10 32,10 32,20 C32,10 42,10 42,20 C42,10 52,10 52,20 C52,10 62,10 62,20" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="62" y1="20" x2="80" y2="20" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  led: (
    <svg width="60" height="40" viewBox="0 0 60 40">
      <line x1="0" y1="20" x2="18" y2="20" stroke="currentColor" strokeWidth="2"/>
      <polygon points="18,8 18,32 38,20" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="38" y1="8" x2="38" y2="32" stroke="currentColor" strokeWidth="2"/>
      <line x1="38" y1="20" x2="60" y2="20" stroke="currentColor" strokeWidth="2"/>
      <line x1="34" y1="6" x2="42" y2="0" stroke="#f59e0b" strokeWidth="1.5"/>
      <line x1="40" y1="8" x2="48" y2="2" stroke="#f59e0b" strokeWidth="1.5"/>
    </svg>
  ),
  diode: (
    <svg width="60" height="40" viewBox="0 0 60 40">
      <line x1="0" y1="20" x2="18" y2="20" stroke="currentColor" strokeWidth="2"/>
      <polygon points="18,8 18,32 38,20" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="38" y1="8" x2="38" y2="32" stroke="currentColor" strokeWidth="2"/>
      <line x1="38" y1="20" x2="60" y2="20" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  ground: (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <line x1="20" y1="0" x2="20" y2="16" stroke="currentColor" strokeWidth="2"/>
      <line x1="6" y1="16" x2="34" y2="16" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="10" y1="22" x2="30" y2="22" stroke="currentColor" strokeWidth="2"/>
      <line x1="14" y1="28" x2="26" y2="28" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  ),
  switch: (
    <svg width="60" height="40" viewBox="0 0 60 40">
      <line x1="0" y1="24" x2="18" y2="24" stroke="currentColor" strokeWidth="2"/>
      <circle cx="18" cy="24" r="3" fill="currentColor"/>
      <line x1="18" y1="24" x2="42" y2="10" stroke="currentColor" strokeWidth="2"/>
      <circle cx="42" cy="24" r="3" fill="currentColor"/>
      <line x1="42" y1="24" x2="60" y2="24" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  // Op-Amp: triangle with +/- inputs
  opamp: (
    <svg width="80" height="60" viewBox="0 0 80 60">
      <line x1="0" y1="18" x2="15" y2="18" stroke="currentColor" strokeWidth="2"/>
      <line x1="0" y1="42" x2="15" y2="42" stroke="currentColor" strokeWidth="2"/>
      <polygon points="15,0 15,60 70,30" fill="none" stroke="currentColor" strokeWidth="2"/>
      <text x="20" y="24" fontSize="12" fill="#ef4444" fontFamily="monospace" fontWeight="bold">−</text>
      <text x="20" y="48" fontSize="12" fill="#22d3ee" fontFamily="monospace" fontWeight="bold">+</text>
      <line x1="70" y1="30" x2="80" y2="30" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  // NPN Transistor
  transistor_npn: (
    <svg width="60" height="60" viewBox="0 0 60 60">
      <line x1="0" y1="30" x2="20" y2="30" stroke="currentColor" strokeWidth="2"/>
      <line x1="20" y1="10" x2="20" y2="50" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="20" y1="18" x2="45" y2="5" stroke="currentColor" strokeWidth="2"/>
      <line x1="20" y1="42" x2="45" y2="55" stroke="currentColor" strokeWidth="2"/>
      {/* Arrow on emitter */}
      <polygon points="38,50 45,55 40,46" fill="currentColor" stroke="currentColor" strokeWidth="1"/>
      {/* Labels */}
      <text x="48" y="10" fontSize="8" fill="#94a3b8" fontFamily="monospace">C</text>
      <text x="2" y="27" fontSize="8" fill="#94a3b8" fontFamily="monospace">B</text>
      <text x="48" y="58" fontSize="8" fill="#94a3b8" fontFamily="monospace">E</text>
    </svg>
  ),
  // PNP Transistor
  transistor_pnp: (
    <svg width="60" height="60" viewBox="0 0 60 60">
      <line x1="0" y1="30" x2="20" y2="30" stroke="currentColor" strokeWidth="2"/>
      <line x1="20" y1="10" x2="20" y2="50" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="20" y1="18" x2="45" y2="5" stroke="currentColor" strokeWidth="2"/>
      <line x1="20" y1="42" x2="45" y2="55" stroke="currentColor" strokeWidth="2"/>
      {/* Arrow on emitter pointing inward */}
      <polygon points="25,38 20,42 28,44" fill="currentColor" stroke="currentColor" strokeWidth="1"/>
      <text x="48" y="10" fontSize="8" fill="#94a3b8" fontFamily="monospace">C</text>
      <text x="2" y="27" fontSize="8" fill="#94a3b8" fontFamily="monospace">B</text>
      <text x="48" y="58" fontSize="8" fill="#94a3b8" fontFamily="monospace">E</text>
    </svg>
  ),
  // N-Channel MOSFET
  mosfet_n: (
    <svg width="60" height="60" viewBox="0 0 60 60">
      <line x1="0" y1="30" x2="18" y2="30" stroke="currentColor" strokeWidth="2"/>
      <line x1="22" y1="10" x2="22" y2="50" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="26" y1="10" x2="26" y2="22" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="26" x2="26" y2="34" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="38" x2="26" y2="50" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="15" x2="45" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="45" y1="15" x2="45" y2="5" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="45" x2="45" y2="45" stroke="currentColor" strokeWidth="2"/>
      <line x1="45" y1="45" x2="45" y2="55" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="30" x2="45" y2="30" stroke="currentColor" strokeWidth="2"/>
      {/* Arrow */}
      <polygon points="30,30 26,27 26,33" fill="currentColor"/>
      <text x="48" y="8" fontSize="7" fill="#94a3b8" fontFamily="monospace">D</text>
      <text x="2" y="28" fontSize="7" fill="#94a3b8" fontFamily="monospace">G</text>
      <text x="48" y="58" fontSize="7" fill="#94a3b8" fontFamily="monospace">S</text>
    </svg>
  ),
  // P-Channel MOSFET
  mosfet_p: (
    <svg width="60" height="60" viewBox="0 0 60 60">
      <line x1="0" y1="30" x2="18" y2="30" stroke="currentColor" strokeWidth="2"/>
      <line x1="22" y1="10" x2="22" y2="50" stroke="currentColor" strokeWidth="2.5"/>
      <line x1="26" y1="10" x2="26" y2="22" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="26" x2="26" y2="34" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="38" x2="26" y2="50" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="15" x2="45" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="45" y1="15" x2="45" y2="5" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="45" x2="45" y2="45" stroke="currentColor" strokeWidth="2"/>
      <line x1="45" y1="45" x2="45" y2="55" stroke="currentColor" strokeWidth="2"/>
      <line x1="26" y1="30" x2="45" y2="30" stroke="currentColor" strokeWidth="2"/>
      {/* Arrow pointing out */}
      <polygon points="38,30 42,27 42,33" fill="currentColor"/>
      <text x="48" y="58" fontSize="7" fill="#94a3b8" fontFamily="monospace">D</text>
      <text x="2" y="28" fontSize="7" fill="#94a3b8" fontFamily="monospace">G</text>
      <text x="48" y="8" fontSize="7" fill="#94a3b8" fontFamily="monospace">S</text>
    </svg>
  ),
  // Transformer
  transformer: (
    <svg width="60" height="50" viewBox="0 0 60 50">
      <path d="M8,5 C8,10 18,10 18,15 C18,20 8,20 8,25 C8,30 18,30 18,35 C18,40 8,40 8,45" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="28" y1="5" x2="28" y2="45" stroke="currentColor" strokeWidth="1" strokeDasharray="3"/>
      <line x1="32" y1="5" x2="32" y2="45" stroke="currentColor" strokeWidth="1" strokeDasharray="3"/>
      <path d="M42,5 C42,10 52,10 52,15 C52,20 42,20 42,25 C42,30 52,30 52,35 C52,40 42,40 42,45" fill="none" stroke="currentColor" strokeWidth="2"/>
    </svg>
  ),
  // Terminal / Node label (Vin, Vout, etc.)
  terminal: (
    <svg width="30" height="30" viewBox="0 0 30 30">
      <circle cx="15" cy="15" r="8" fill="none" stroke="currentColor" strokeWidth="2.5"/>
      <circle cx="15" cy="15" r="3" fill="currentColor"/>
    </svg>
  ),
  // IC / Chip
  ic: (
    <svg width="60" height="50" viewBox="0 0 60 50">
      <rect x="10" y="5" width="40" height="40" rx="3" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="0" y1="15" x2="10" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="0" y1="35" x2="10" y2="35" stroke="currentColor" strokeWidth="2"/>
      <line x1="50" y1="15" x2="60" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="50" y1="35" x2="60" y2="35" stroke="currentColor" strokeWidth="2"/>
      <circle cx="18" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  ),
  chip: (
    <svg width="60" height="50" viewBox="0 0 60 50">
      <rect x="10" y="5" width="40" height="40" rx="3" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="0" y1="15" x2="10" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="0" y1="35" x2="10" y2="35" stroke="currentColor" strokeWidth="2"/>
      <line x1="50" y1="15" x2="60" y2="15" stroke="currentColor" strokeWidth="2"/>
      <line x1="50" y1="35" x2="60" y2="35" stroke="currentColor" strokeWidth="2"/>
      <circle cx="18" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  ),
};
