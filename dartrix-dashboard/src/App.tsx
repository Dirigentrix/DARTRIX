import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Shield, 
  Zap, 
  Cpu, 
  Terminal, 
  AlertTriangle, 
  Radio, 
  ChevronRight,
  Gauge
} from 'lucide-react';

// --- MOCK DATA GENERATOR ---
const generateTelemetry = () => ({
  intensity: Math.random() * 0.8 + 0.1,
  tension: Math.random() * 0.5 + 0.2,
  drift: (Math.random() - 0.5) * 0.1,
  state: Math.random() > 0.9 ? 'WARNING' : 'STABLE',
  timestamp: new Date().toLocaleTimeString(),
});

const App: React.FC = () => {
  const [telemetry, setTelemetry] = useState(generateTelemetry());
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const newData = generateTelemetry();
      setTelemetry(newData);
      setHistory(prev => [newData, ...prev].slice(0, 10));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-black text-cyan-500 font-mono p-4 flex flex-col gap-4 overflow-hidden border-4 border-slate-900">
      {/* HEADER / HUD */}
      <header className="flex justify-between items-center border-b border-cyan-900/50 pb-2 mb-2">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500 blur-sm animate-pulse opacity-20"></div>
            <Radio className="w-8 h-8 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-widest text-white">DARTRIX-OPS</h1>
            <p className="text-[10px] text-cyan-700 tracking-[0.2em]">RADDAR MISSION CONTROL // V2.0.4</p>
          </div>
        </div>
        <div className="flex gap-6 text-[10px] items-center">
          <div className="flex flex-col items-end">
            <span className="text-cyan-800 uppercase">System Status</span>
            <span className={telemetry.state === 'STABLE' ? 'text-green-500' : 'text-red-500 animate-pulse'}>
              {telemetry.state}
            </span>
          </div>
          <div className="flex flex-col items-end border-l border-cyan-900/50 pl-4">
            <span className="text-cyan-800 uppercase">Local Time</span>
            <span className="text-white">{telemetry.timestamp}</span>
          </div>
        </div>
      </header>

      {/* MAIN GRID */}
      <main className="flex-1 grid grid-cols-12 gap-4">
        
        {/* LEFT COLUMN: CORE METRICS */}
        <section className="col-span-3 flex flex-col gap-4">
          <div className="bg-slate-950/50 border border-cyan-900/30 p-4 relative overflow-hidden group">
             <div className="absolute top-0 right-0 p-1"><Activity className="w-3 h-3 text-cyan-900" /></div>
             <h3 className="text-[10px] text-cyan-700 uppercase mb-2">Field Intensity [I]</h3>
             <div className="text-4xl font-black text-white">{telemetry.intensity.toFixed(4)}</div>
             <div className="mt-4 h-1 bg-cyan-900/20 w-full overflow-hidden">
                <div 
                  className="h-full bg-cyan-500 transition-all duration-500 ease-out" 
                  style={{ width: `${telemetry.intensity * 100}%` }}
                ></div>
             </div>
          </div>

          <div className="bg-slate-950/50 border border-cyan-900/30 p-4 relative">
             <h3 className="text-[10px] text-cyan-700 uppercase mb-2">Biometric Tension [T]</h3>
             <div className="text-4xl font-black text-white">{telemetry.tension.toFixed(4)}</div>
             <div className="mt-2 flex gap-1">
               {Array.from({length: 12}).map((_, i) => (
                 <div key={i} className={`h-4 flex-1 ${i / 12 < telemetry.tension ? 'bg-cyan-600' : 'bg-cyan-900/20'}`}></div>
               ))}
             </div>
          </div>

          <div className="bg-slate-950/50 border border-cyan-900/30 p-4 flex-1">
             <h3 className="text-[10px] text-cyan-700 uppercase mb-4">Telemetry Logs</h3>
             <div className="text-[9px] flex flex-col gap-2">
               {history.map((h, i) => (
                 <div key={i} className="flex justify-between border-b border-cyan-900/10 pb-1">
                   <span className="text-cyan-800">[{h.timestamp}]</span>
                   <span className="text-cyan-400">Φ:{h.intensity.toFixed(2)}</span>
                   <span className={h.state === 'STABLE' ? 'text-green-900' : 'text-red-500'}>{h.state[0]}</span>
                 </div>
               ))}
             </div>
          </div>
        </section>

        {/* CENTER COLUMN: THE ORB / MAIN VISUAL */}
        <section className="col-span-6 flex flex-col gap-4 relative">
          <div className="flex-1 bg-slate-950/50 border border-cyan-900/30 relative flex items-center justify-center overflow-hidden">
            {/* BACKGROUND GRID */}
            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, #06b6d4 1px, transparent 1px)', backgroundSize: '30px 30px' }}></div>
            
            {/* GLOWING ORB */}
            <div className="relative w-64 h-64">
              <div 
                className="absolute inset-0 rounded-full border-2 border-cyan-500/30 animate-[spin_10s_linear_infinite]"
                style={{ transform: `scale(${1 + telemetry.drift})` }}
              ></div>
              <div className="absolute inset-0 rounded-full border border-dashed border-cyan-400/20 animate-[spin_15s_linear_infinite_reverse]"></div>
              
              <div className="absolute inset-8 rounded-full bg-cyan-500/5 blur-3xl animate-pulse"></div>
              
              {/* CORE CORE */}
              <div className="absolute inset-[35%] rounded-full bg-gradient-to-tr from-cyan-600 to-white shadow-[0_0_50px_rgba(6,182,212,0.5)] flex items-center justify-center">
                 <Shield className="w-8 h-8 text-slate-950" />
              </div>

              {/* ROTATING POINTS */}
              <div className="absolute inset-0 animate-[spin_4s_linear_infinite]">
                 <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_10px_#22d3ee]"></div>
              </div>
            </div>

            {/* OVERLAY HUD DATA */}
            <div className="absolute bottom-4 left-4 text-[10px] space-y-1">
               <div className="flex gap-2 items-center"><ChevronRight className="w-2 h-2" /> DRIFT_COEFF: {telemetry.drift.toFixed(6)}</div>
               <div className="flex gap-2 items-center"><ChevronRight className="w-2 h-2" /> SYNC_LOCK: TRUE</div>
            </div>
          </div>
          
          <div className="h-24 bg-slate-950/50 border border-cyan-900/30 p-2 flex gap-4">
            <div className="flex-1 border-r border-cyan-900/30 flex flex-col justify-center">
               <span className="text-[8px] text-cyan-800 text-center">CPU LOAD</span>
               <div className="flex justify-center gap-1 mt-1">
                  {[...Array(8)].map((_, i) => <div key={i} className="w-2 h-4 bg-cyan-950"></div>)}
               </div>
            </div>
            <div className="flex-1 flex items-center justify-center gap-3">
              <Zap className="text-yellow-500 w-5 h-5" />
              <div className="text-xs">POWER NOMINAL: 98.4%</div>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: MODULES / OPERATORS */}
        <section className="col-span-3 flex flex-col gap-4">
          <div className="bg-slate-950/50 border border-cyan-900/30 p-4">
             <h3 className="text-[10px] text-cyan-700 uppercase mb-4 flex items-center gap-2">
               <Terminal className="w-3 h-3" /> Command Console
             </h3>
             <div className="space-y-3">
                <button className="w-full text-left p-2 border border-cyan-900/50 hover:bg-cyan-900/20 text-[10px] transition-colors">
                  > EXECUTE_RESONANCE_SCAN
                </button>
                <button className="w-full text-left p-2 border border-cyan-900/50 hover:bg-cyan-900/20 text-[10px] transition-colors">
                  > RECALIBRATE_PHI_OP
                </button>
                <button className="w-full text-left p-2 border border-red-900/50 hover:bg-red-900/20 text-red-900 text-[10px] transition-colors">
                  > EMERGENCY_CORE_DUMP
                </button>
             </div>
          </div>

          <div className="flex-1 bg-slate-950/50 border border-cyan-900/30 p-4 overflow-hidden flex flex-col">
             <h3 className="text-[10px] text-cyan-700 uppercase mb-4 flex items-center gap-2">
               <Cpu className="w-3 h-3" /> Sub-System Matrix
             </h3>
             <div className="grid grid-cols-4 gap-2 flex-1">
               {Array.from({length: 20}).map((_, i) => (
                 <div key={i} className={`border border-cyan-900/20 ${Math.random() > 0.8 ? 'bg-cyan-500/20 animate-pulse' : 'bg-transparent'}`}></div>
               ))}
             </div>
          </div>
        </section>
      </main>

      {/* FOOTER TICKER */}
      <footer className="h-6 border-t border-cyan-900/50 flex items-center px-4 justify-between text-[10px] bg-slate-950">
        <div className="flex gap-4">
          <span className="text-cyan-800">LATENCY: 12ms</span>
          <span className="text-cyan-800">ENCRYPTION: AES-256-RADDAR</span>
        </div>
        <div className="text-white animate-pulse">
           READY FOR OPERATOR INPUT...
        </div>
      </footer>

      {/* SCANLINE EFFECT */}
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-50 bg-[length:100%_2px,3px_100%]"></div>
    </div>
  );
};

export default App;
