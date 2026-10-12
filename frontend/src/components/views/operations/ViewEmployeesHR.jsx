import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { Avatar } from "../../ui/Avatar.jsx";
import { OpsHeader, Tabs, FilterBar, StatusPill } from "./OpsShared.jsx";
import { Users, UsersRound, CalendarCheck, Clock, Briefcase, Plus, Download, MoreHorizontal, TrendingUp } from "lucide-react";

const STATS = [
  { title: "Total Employees", value: "248", sub: "", icon: UsersRound, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Present Today", value: "216", sub: "(87%)", icon: CalendarCheck, iconTint: "text-emerald-600", iconBg: "bg-emerald-50" },
  { title: "On Leave", value: "18", sub: "(7%)", icon: Clock, iconTint: "text-orange-500", iconBg: "bg-orange-50" },
  { title: "Open Positions", value: "12", sub: "", icon: Briefcase, iconTint: "text-violet-600", iconBg: "bg-violet-50" },
];

const ROWS = [
  { name: "Aarav Sharma", role: "Software Engineer", dept: "Engineering", status: "Active", att: "Present", attTone: "green", img: "https://i.pravatar.cc/80?img=11" },
  { name: "Kavya Iyer", role: "Product Manager", dept: "Product", status: "Active", att: "Present", attTone: "green", img: "https://i.pravatar.cc/80?img=47" },
  { name: "Rohan Mehta", role: "UI/UX Designer", dept: "Design", status: "Active", att: "On Leave", attTone: "amber", img: "https://i.pravatar.cc/80?img=15" },
  { name: "Neha Patel", role: "Data Analyst", dept: "Analytics", status: "Active", att: "Present", attTone: "green", initials: "NP", color: "bg-violet-100 text-violet-600" },
  { name: "Arjun Singh", role: "DevOps Engineer", dept: "Infrastructure", status: "Active", att: "Present", attTone: "green", img: "https://i.pravatar.cc/80?img=33" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none mt-1.5">
          {m.value}{m.sub && <span className="text-[22px] font-bold ml-1">{m.sub}</span>}
        </h3>
        <div className="mt-2.5 flex items-center gap-1 text-[13px] font-semibold text-emerald-600">
          <TrendingUp size={14} strokeWidth={2.6} />0%
        </div>
      </div>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={22} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewEmployeesHR = () => {
  const [tab, setTab] = useState("Employees");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Users}
        title="Employees / HR"
        subtitle="Manage staff, schedules and attendance"
        iconTint="text-[#4f46e5]"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            <Plus size={18} strokeWidth={2.4} /> Add Employee
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["Employees", "Attendance", "Leave Requests", "Performance", "Departments"]} active={tab} onChange={setTab} />

      <FilterBar
        placeholder="Search employees..."
        filters={["All Departments", "All Status"]}
        action={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-slate-700 text-[15px] font-semibold hover:bg-slate-50">
            <Download size={18} strokeWidth={2} /> Export
          </button>
        }
      />

      <Card className="overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50/70 text-left text-[13px] font-bold text-slate-500">
              <th className="py-3.5 pl-5 w-12"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></th>
              <th className="py-3.5 font-bold">Name</th>
              <th className="py-3.5 font-bold">Role</th>
              <th className="py-3.5 font-bold">Department</th>
              <th className="py-3.5 font-bold">Status</th>
              <th className="py-3.5 font-bold">Attendance</th>
              <th className="py-3.5 pr-5 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ROWS.map((r, i) => (
              <tr key={i} className="text-[14px] hover:bg-slate-50/50">
                <td className="py-4 pl-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></td>
                <td className="py-4">
                  <span className="flex items-center gap-3">
                    <Avatar src={r.img} initials={r.initials} color={r.color} size="w-9 h-9" />
                    <span className="font-semibold text-[#0b1220]">{r.name}</span>
                  </span>
                </td>
                <td className="py-4 text-blue-600 font-medium">{r.role}</td>
                <td className="py-4 text-slate-500">{r.dept}</td>
                <td className="py-4"><StatusPill label={r.status} tone="green" /></td>
                <td className="py-4"><StatusPill label={r.att} tone={r.attTone} /></td>
                <td className="py-4 pr-5 text-right"><MoreHorizontal size={18} className="text-slate-400 inline-block" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};
