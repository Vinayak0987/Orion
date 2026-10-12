export const Avatar = ({ initials, color = "bg-[#4f46e5] text-white", size = "w-8 h-8", src = "" }) =>
  src ? (
    <img src={src} className={`${size} rounded-full object-cover border border-slate-200`} />
  ) : (
    <div className={`${size} ${color} rounded-full flex items-center justify-center text-xs font-semibold shadow-sm border border-slate-100`}>
      {initials}
    </div>
  );
