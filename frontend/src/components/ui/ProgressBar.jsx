export const ProgressBar = ({ percent, color = "bg-[#4f46e5]", className = "" }) => (
  <div className={`w-full bg-slate-100 rounded-full h-1.5 ${className}`}>
    <div className={`${color} h-1.5 rounded-full`} style={{ width: `${percent}%` }}></div>
  </div>
);
