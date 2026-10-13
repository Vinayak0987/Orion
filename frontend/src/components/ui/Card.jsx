export const Card = ({ children, className = "" }) => (
  <div className={`bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] ${className}`}>
    {children}
  </div>
);