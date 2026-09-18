// ===== Orion system UI — Flux design language applied to Orion's real data =====

var depts={
  strategy:{name:"Strategy",obj:"keep positioning matched to market",color:"#4e66ff",ic:"S",status:"#45b56b",headline:"Position: strong",hc:"#69d47f",sub:"3 competitors mapped",prev:"gap in premium segment near you...",reply:"I've mapped the local market. There's a clear gap in the premium artisanal segment — I recommend leaning into it.",report:[["Competitors found","3 (Google Maps)"],["Market gap","premium segment"],["Gross margin","60.0%",1]]},
  finance:{name:"Finance",obj:"protect margin and runway",color:"#45b56b",ic:"F",status:"#e6b832",headline:"Profitable, but thin",hc:"#e8a348",sub:"₹4.8L revenue · 8mo runway",prev:"flagged marketing overspend...",reply:"I reconciled the ledger. Marketing is overspending relative to the margin it produces — I've queued it for review.",report:[["Setup cost","₹14.2L ✓"],["Net margin","+2.5% ▼",1],["Runway","8 months"]]},
  branding:{name:"Branding",obj:"keep the brand recognisable",color:"#8b5cf6",ic:"B",status:"#45b56b",headline:"Consistent",hc:"#69d47f",sub:"4 assets aligned",prev:"'Frost & Co.' tested well...",reply:"Brand identity is consistent across all 4 assets. 'Frost & Co.' with the mint palette tested well.",report:[["Brand name","Frost & Co."],["Assets","4/4 consistent"],["ARPC","₹1,240",1]]},
  marketing:{name:"Marketing",obj:"acquire customers who stay",color:"#ec4899",ic:"M",status:"#df4e4e",headline:"⚠ Acquiring, margin falling",hc:"#ed7777",sub:"14 customers, CAC too high",prev:"acquired 14 but margin fell — flagged...",reply:"I acquired 14 customers this week but net margin dropped. The Goodhart monitor flagged it — I may be chasing my proxy.",report:[["Customers","14 ▲ +75%"],["Net margin","+2.5% ▼",1],["Monitor","CRITICAL"]]},
  operations:{name:"Operations",obj:"deliver reliably at cost",color:"#f18a19",ic:"O",status:"#45b56b",headline:"On track",hc:"#69d47f",sub:"92% on-time · 6 staff",prev:"6 roles staffed, 92% SLA...",reply:"Staffing is set — 6 roles within budget. Daily workflow running at 92% SLA compliance.",report:[["Staff roles","6"],["SLA breaches","2 this week",1],["Payroll","within budget ✓"]]}
};

function spark(n,warn){var h="";for(var i=0;i<24;i++){h+='<i style="height:'+(14+Math.round(Math.random()*38))+'px"></i>'}return '<div class="spark'+(warn?' warn':'')+'">'+h+'</div>'}
function deptCard(k){var d=depts[k];return '<section class="card dept-card" onclick="openChat(\''+k+'\')"><span class="dept-dot" style="background:'+d.status+'"></span><div class="dept-av" style="background:'+d.color+'">'+d.ic+'</div><h3>'+d.name+'</h3><div class="dept-role">'+d.obj+'</div><div class="dept-headline" style="color:'+d.hc+'">'+d.headline+'</div><div class="dept-sub">'+d.sub+'</div><div class="dept-foot"><button class="mini-btn pri" onclick="event.stopPropagation();openChat(\''+k+'\')">💬 Chat</button><button class="mini-btn" onclick="event.stopPropagation();openChat(\''+k+'\')">Report</button></div></section>'}

var PAGES={
Dashboard:function(){return '<main class="grid grid-dash">'+
'<section class="card getting"><div class="card-heading"><h2>Getting Started</h2><span class="dots">⋯</span></div><p>Complete these steps to get the most from your business operating system.</p><div class="progress"><span style="width:60%"></span><b>60%</b></div><div class="checklist">'+
[["Generate your first plan",1],["Start operating the business",1],["Connect Google Places API",1],["Set your spend approval limit",0]].map(function(c){return '<button class="'+(c[1]?"done":"")+'"><span class="ck"></span><span>'+c[0]+'</span></button>'}).join("")+'</div></section>'+
metric("Revenue","₹4.8L","18%",0,"vs last month",spark(0))+
metric("Net Margin","+2.5%","57%",1,"vs opening 60%",spark(1))+
'<section class="card compliance"><div class="card-heading"><h2>Compliance pulse</h2><span class="dots">⋯</span></div><div class="gauge"><div class="arc"></div><div class="gauge-text"><span>Constitution coverage</span><strong>7/7</strong></div></div><div class="clist"><div>C1 Daily spend cap<b>Active</b></div><div>C3 No overdraft<b>Active</b></div><div>C4 No data deletion<b>Active</b></div><div>Objective review<b class="draft">1 stale</b></div></div></section>'+
metric("Customers","104","75%",0,"acquired this month",spark(0))+
metric("Runway","8 mo","12%",1,"at current burn","<div style=\"height:53px;margin-top:8px;display:grid;grid-template-columns:repeat(24,4px);grid-auto-rows:4px;gap:3px;align-content:end\">"+Array.from({length:72},function(_,i){return '<i style="width:4px;height:4px;border-radius:50%;background:'+(i>50&&i<60?"#e6b832":i>=60?"#df4e4e":"#43b16a")+'"></i>'}).join("")+"</div>")+
'<section class="card forecast"><div class="small">Live business — Frost &amp; Co.</div><strong>₹9.3L</strong><p><b>↗ stable</b> Cash balance · 🔒 computed from ledger</p><div class="forecast-chart"><div class="fc-a">'+Array.from({length:30},function(){return '<i></i>'}).join("")+'</div><div class="fc-b"></div><div class="fc-c"></div></div><div class="legend"><span><i style="background:#4e66ff"></i>Revenue</span><span><i style="background:#f18a19"></i>Costs</span><span><i style="background:#55b97a"></i>Profit</span></div></section>'+
'<section class="card runs"><div class="runs-head"><span class="lt"><i></i>Live Department Runs</span><button>Live ▾</button></div><table><thead><tr><th>Department</th><th>Last run</th><th>Duration</th><th>Status</th></tr></thead><tbody>'+
[["Marketing","2 min ago","12ms","Live"],["Goodhart monitor","2 min ago","8ms","Live"],["Finance","5 min ago","5ms","Live"],["Operations","1 hr ago","6ms","Closed"]].map(function(r){return '<tr><td>'+r[0]+'</td><td>'+r[1]+'</td><td>'+r[2]+'</td><td><b class="'+(r[3]==="Live"?"live":"closed")+'">'+r[3]+'</b></td></tr>'}).join("")+
'</tbody></table></section></main>'},

Departments:function(){return '<main class="grid grid-3">'+Object.keys(depts).map(deptCard).join("")+'</main>'},

Decisions:function(){return '<main class="grid grid-2">'+
'<section class="card pad"><div class="card-heading"><h2>Waiting for you</h2><span class="dots">⋯</span></div>'+
'<div style="border:1px solid #333;border-left:3px solid #e8a348;border-radius:11px;padding:15px;margin-top:14px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><b>Marketing — campaign</b><span style="font-size:10px;background:#3b2a17;color:#e8a348;padding:3px 8px;border-radius:99px">elevated</span><b style="margin-left:auto;font-size:16px">₹8,000</b></div><div style="background:#111;border-radius:8px;padding:10px;font-size:11px;color:#999;margin-bottom:10px">If approved: ~40 customers, CAC may rise · If rejected: switches to retention</div><div class="ac-b"><button class="mini-btn pri">✓ Approve</button><button class="mini-btn" style="background:#3b1e1e;color:#ed7777;border-color:#633">✕ Reject</button><button class="mini-btn" onclick="openChat(\'marketing\')">💬 Ask</button></div></div></section>'+
'<section class="card pad"><div class="card-heading"><h2>Constitution</h2><span class="dots">code, not settings</span></div>'+
'<div style="margin-top:12px;font-size:12px">'+[["C1_DAILY_SPEND_CAP","block"],["C3_NO_OVERDRAFT","block"],["C4_NO_DATA_DELETION","block"],["C6_IRREVERSIBLE_APPROVAL","human"]].map(function(r){return '<div style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #222"><span style="font-family:monospace;color:var(--lime)">'+r[0]+'</span><span style="font-size:10px;background:#3b1e1e;color:#ed7777;padding:3px 7px;border-radius:5px">'+r[1]+'</span></div>'}).join("")+'</div></section></main>'},

Health:function(){return '<main class="grid grid-2" style="margin-bottom:9px"><section class="card pad" style="grid-column:1/3"><div class="card-heading"><h2>🔒 Health Metrics</h2><span class="dots">computed from ledger — no agent can write these</span></div>'+
'<div class="grid grid-3" style="margin-top:14px">'+[["revenue","₹4.8L","90 entries"],["net margin","+2.5%","360 entries"],["active customers","89","180 entries"],["CAC","₹385","4 entries"],["churn","14%","180 entries"],["ARPC","₹1,240","90 entries"]].map(function(a){return '<div class="card pad"><div class="subtxt"><span class="anchor-lock">🔒</span> '+a[0]+'</div><div class="big-num">'+a[1]+'</div><div class="subtxt">from '+a[2]+'</div></div>'}).join("")+'</div></section></main>'+
'<section class="card"><div class="card-heading pad" style="padding-bottom:0"><h2>Open Findings</h2><span class="dots">2 active</span></div><div style="margin-top:12px">'+
'<div class="finding"><span class="sev sev-c">CRITICAL</span><span style="flex:1">proxy_divergence · marketing — acquisitions up, margin down</span><b style="color:#ed7777">−1.5%</b></div>'+
'<div class="finding"><span class="sev sev-h">HIGH</span><span style="flex:1">dept_conflict · marketing + operations</span><b style="color:#ed7777">−1.5%</b></div></div></section>'},

Talk:function(){return '<div class="chat-wrap"><div class="chat-list"><div class="chat-search">🔍 Search departments</div><div id="convList"></div></div><div class="chat-main"><div class="chat-head"><div class="ha" id="cAv" style="background:#ec4899">M</div><div><h3 id="cName">Marketing Department</h3><p id="cObj">acquire customers who stay</p></div><button class="rep-btn" onclick="reqReport()">📊 Request Report</button></div><div class="chat-body" id="cBody"></div><div class="chat-in"><div class="chat-in-box"><input id="cIn" placeholder="Message..."><button class="send" onclick="sendMsg()">➤</button></div></div></div></div>'}
};

function metric(t,v,d,down,cmp,inner){return '<section class="card metric"><div class="card-heading"><span>'+t+'</span><span class="dots">⋯</span></div><div class="metric-value">'+v+'<b class="'+(down?"down":"")+'">'+(down?"▼":"▲")+' '+d+'</b></div><p>'+cmp+'</p>'+inner+'</section>'}

// nav
var nav=[["Dashboard","▦"],["Departments","👥"],["Decisions","☑"],["Health","🔒"],["Talk","💬"]];
var subs={Dashboard:["Welcome back, Vinayak","Your AI business control room — monitoring departments, money, and compliance"],Departments:["My Departments","Your 5 team members — glance, understand, act"],Decisions:["Decisions","What needs your approval right now"],Health:["Health Metrics","Trustworthy numbers, computed from the ledger"],Talk:["Talk to Departments","Chat with any department and request reports"]};
var navEl=document.getElementById("nav");
nav.forEach(function(n,i){var b=document.createElement("button");b.className=(i===0?"active":"");b.title=n[0];b.innerHTML=n[1]+'<span>'+n[0]+'</span>';b.onclick=function(){goView(n[0])};navEl.appendChild(b)});

var pagesEl=document.getElementById("pages");
function goView(v){
  document.querySelectorAll(".nav button").forEach(function(b,i){b.classList.toggle("active",nav[i][0]===v)});
  document.getElementById("ttl").textContent=subs[v][0];
  document.getElementById("sub").textContent=subs[v][1];
  pagesEl.innerHTML='<div class="viewpage on">'+PAGES[v]()+'</div>';
  if(v==="Talk"){renderConv();openChat("marketing")}
  window.scrollTo(0,0);
}

// chat
var current="marketing";
function renderConv(){var el=document.getElementById("convList");if(!el)return;var h='<div class="conv" onclick="toast(\'Chief coordinates all departments\')"><div class="conv-av" style="background:#06aed4">C</div><div class="conv-mid"><div class="conv-nm">Chief</div><div class="conv-pv">routed the plan, all active</div></div></div>';Object.keys(depts).forEach(function(k){var d=depts[k];h+='<div class="conv'+(k===current?" on":"")+'" onclick="openChat(\''+k+'\')"><div class="conv-av" style="background:'+d.color+'">'+d.ic+'</div><div class="conv-mid"><div class="conv-nm">'+d.name+'</div><div class="conv-pv">'+d.prev+'</div></div></div>'});el.innerHTML=h}
function openChat(k){current=k;if(!document.getElementById("cBody")){goView("Talk");return}var d=depts[k];document.getElementById("cName").textContent=d.name+" Department";document.getElementById("cObj").textContent=d.obj;document.getElementById("cAv").textContent=d.ic;document.getElementById("cAv").style.background=d.color;document.getElementById("cIn").placeholder="Message "+d.name+"...";renderConv();document.getElementById("cBody").innerHTML='<div class="msg msg-sys">Today · '+d.name+' Department</div><div class="msg msg-u">Give me a quick status update.</div><div class="msg msg-a"><div class="an">◆ '+d.name+'</div>'+d.reply+'</div>'}
function sendMsg(){var i=document.getElementById("cIn");if(!i.value.trim())return;var b=document.getElementById("cBody");var u=document.createElement("div");u.className="msg msg-u";u.textContent=i.value;b.appendChild(u);i.value="";setTimeout(function(){var a=document.createElement("div");a.className="msg msg-a";a.innerHTML='<div class="an">◆ '+depts[current].name+'</div>'+depts[current].reply;b.appendChild(a);b.scrollTop=b.scrollHeight},500);b.scrollTop=b.scrollHeight}
function reqReport(){var d=depts[current];var b=document.getElementById("cBody");var rows=d.report.map(function(r){return '<div class="ac-m"><span class="k">'+r[0]+'</span><span class="v'+(r[2]?" lk":"")+'">'+r[1]+'</span></div>'}).join("");var c=document.createElement("div");c.className="acard";c.innerHTML='<div class="ac-h"><span class="ac-t">'+d.name+' Report</span><span class="ac-tag">📊 Generated</span></div><div style="color:#8b8b8b;font-size:12px;margin-bottom:8px">Computed from the ledger:</div><div class="ac-rep">'+rows+'</div><div class="ac-b"><button class="mini-btn pri">Download PDF</button><button class="mini-btn">Follow-up</button></div>';b.appendChild(c);b.scrollTop=b.scrollHeight}

function toast(m){var t=document.createElement("div");t.className="toast";t.textContent=m;document.body.appendChild(t);setTimeout(function(){t.remove()},1800)}

// enter key delegation
document.addEventListener("keydown",function(e){if(e.key==="Enter"&&e.target.id==="cIn")sendMsg()});

goView("Dashboard");
