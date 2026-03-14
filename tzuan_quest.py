#!/usr/bin/env python3
import requests, time, json, random, re, base64
import threading, sqlite3, os, sys
from datetime import datetime, timezone

try:
    from colorama import Fore, Back, Style, init as _ci
    _ci(autoreset=True)
    GR=Fore.GREEN; RD=Fore.RED; YL=Fore.YELLOW; CY=Fore.CYAN
    MG=Fore.MAGENTA; WH=Fore.WHITE; BL=Fore.BLUE; DM=Style.DIM
    BD=Style.BRIGHT; RS=Style.RESET_ALL
    BGN=Back.GREEN; BGR=Back.RED; BGY=Back.YELLOW; BGM=Back.MAGENTA; BGC=Back.CYAN; BGB=Back.BLUE
except ImportError:
    RS="\033[0m"
    BD="\033[1m"; DM="\033[2m"
    GR="\033[92m"; RD="\033[91m"; YL="\033[93m"
    CY="\033[96m"; MG="\033[95m"; WH="\033[97m"; BL="\033[94m"
    BGN="\033[42m"; BGR="\033[41m"; BGY="\033[43m"
    BGM="\033[45m"; BGC="\033[46m"; BGB="\033[44m"

def c(*args):
    styles=[a for a in args if isinstance(a,str) and a!=args[-1]] if len(args)>1 else []
    text=args[0] if args else ""
    return "".join(args[1:])+str(text)+RS

_lk=threading.Lock()
def pr(msg=""): 
    with _lk: print(msg)
def prnl(msg=""):
    with _lk: print(msg, end="", flush=True)

def vis(s): return re.sub(r'\x1b\[[0-9;]*m','',str(s))
def vlen(s): return len(vis(s))

API_BASE="https://discord.com/api/v9"
HEARTBEAT_INTERVAL=20
AUTO_ACCEPT=True
DB_PATH="tzuan.db"
AUTOFARM_POLL=300
LIVE_REFRESH=3

SUPPORTED_TASKS=["WATCH_VIDEO","PLAY_ON_DESKTOP","STREAM_ON_DESKTOP","PLAY_ACTIVITY","WATCH_VIDEO_ON_MOBILE"]
TASK_LABEL={"WATCH_VIDEO":"🎬 Video","WATCH_VIDEO_ON_MOBILE":"📱 Mobile",
            "PLAY_ON_DESKTOP":"🎮 Game","STREAM_ON_DESKTOP":"📺 Stream","PLAY_ACTIVITY":"🕹️  Activity"}
TASK_COL={"WATCH_VIDEO":MG,"WATCH_VIDEO_ON_MOBILE":MG,"PLAY_ON_DESKTOP":CY,
          "STREAM_ON_DESKTOP":BL,"PLAY_ACTIVITY":YL}

sessions: dict={}
_af_alive=False

def clr(): os.system("cls" if os.name=="nt" else "clear")

def pad_line(content, width):
    p=width-vlen(content)
    return content+" "*max(0,p)

def box_line(content, width, lc=CY):
    return c("║",lc)+pad_line(" "+content+" ",width-2)+c("║",lc)

def grad_bar(pct, width=24):
    filled=int(pct/100*width)
    if pct>=80:   bar_c=GR
    elif pct>=50: bar_c=YL
    elif pct>=25: bar_c=RD+BD
    else:         bar_c=RD
    b=c("█"*filled,bar_c,BD)+c("░"*(width-filled),WH,DM)
    pct_c=GR if pct>=80 else YL if pct>=50 else RD
    return b+" "+c(f"{pct:3d}%",pct_c,BD)

def ask(prompt, default=None):
    d=f"  {c('['+default+']',WH,DM)}" if default else ""
    try:
        v=input(c(f"\n  {c('▶',YL,BD)} {prompt}{d}  ",WH)).strip()
        return v if v else (default or "")
    except (KeyboardInterrupt,EOFError):
        pr(c("\n\n  👋  Tạm biệt!\n",GR,BD)); sys.exit(0)

def ask_int(prompt, valid=None, default=None):
    while True:
        try:
            n=int(ask(prompt,str(default) if default is not None else None))
            if valid is None or n in valid: return n
            pr(c(f"  ✘  Chỉ nhập: {sorted(valid)}",RD))
        except ValueError: pr(c("  ✘  Phải là số!",RD))

def wait_enter(msg="  ↩  Enter để tiếp tục..."):
    input(c(f"\n{msg}",WH,DM))

def pick_account(action=""):
    rows=db_list()
    if not rows:
        pr(c("  ✘  Chưa có tài khoản! Chọn [1] để thêm.",RD,BD)); return None
    pr(c(f"\n  ┌─ Chọn tài khoản {action}",YL,BD))
    for r in rows:
        s=sessions.get(r["id"],{})
        af=c(" ◆AF",GR,BD) if db_af_get(r["id"]) else ""
        run=c(" ⚙",YL,BD) if s.get("running") else ""
        name=r["username"]
        pr(c(f"  │ ",YL)+c(f" [{r['id']}] ",CY,BD)+c(name,WH,BD)+af+run)
    return next((r for r in rows if r["id"]==ask_int("ID tài khoản",valid=[r["id"] for r in rows])),None)

def _status_chip(aid):
    s=sessions.get(aid,{})
    if s.get("running"):
        sd,sn=s.get("current_progress",(0,0)); pct=int(sd/sn*100) if sn else 0
        qi=s.get("queue_index",0); qt=s.get("queue_total",0)
        return c(f" ⚙ {pct}% ({qi}/{qt}) ",YL,BD), True
    return c(" ○ Rảnh ",WH,DM), False


def db_init():
    con=sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL, username TEXT, user_id TEXT, added_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS autofarm (
        account_id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0, updated_at TEXT)""")
    con.commit(); con.close()

def db_add(token,username,user_id):
    con=sqlite3.connect(DB_PATH)
    cur=con.execute("INSERT INTO accounts (token,username,user_id,added_at) VALUES (?,?,?,?)",
        (token,username,user_id,datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    aid=cur.lastrowid; con.commit(); con.close(); return aid

def db_del(aid):
    con=sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM accounts WHERE id=?",(aid,))
    con.execute("DELETE FROM autofarm WHERE account_id=?",(aid,))
    con.commit(); con.close()

def db_list():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
    rows=con.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    con.close(); return [dict(r) for r in rows]

def db_get(aid):
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM accounts WHERE id=?",(aid,)).fetchone()
    con.close(); return dict(row) if row else None

def db_af_set(aid,enabled):
    con=sqlite3.connect(DB_PATH)
    con.execute("""INSERT INTO autofarm (account_id,enabled,updated_at) VALUES (?,?,?)
        ON CONFLICT(account_id) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at""",
        (aid,1 if enabled else 0,datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    con.commit(); con.close()

def db_af_get(aid):
    con=sqlite3.connect(DB_PATH)
    row=con.execute("SELECT enabled FROM autofarm WHERE account_id=?",(aid,)).fetchone()
    con.close(); return bool(row[0]) if row else False

def db_af_all():
    con=sqlite3.connect(DB_PATH)
    rows=con.execute("SELECT account_id FROM autofarm WHERE enabled=1").fetchall()
    con.close(); return [r[0] for r in rows]


_build=None
def fetch_build():
    global _build
    if _build: return _build
    try:
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        r=requests.get("https://discord.com/app",headers={"User-Agent":ua},timeout=15)
        for h in re.findall(r'/assets/([a-f0-9]+)\.js',r.text)[-5:]:
            ar=requests.get(f"https://discord.com/assets/{h}.js",headers={"User-Agent":ua},timeout=15)
            m=re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})',ar.text)
            if m: _build=int(m.group(1)); return _build
    except: pass
    _build=504649; return _build

def make_sp(build):
    obj={"os":"Windows","browser":"Discord Client","release_channel":"stable","client_version":"1.0.9175",
         "os_version":"10.0.26100","os_arch":"x64","app_arch":"x64","system_locale":"en-US",
         "browser_user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7",
         "browser_version":"32.2.7","client_build_number":build,"native_build_number":59498,"client_event_source":None}
    return base64.b64encode(json.dumps(obj).encode()).decode()

class DiscordAPI:
    def __init__(self,token):
        self.token=token; self.s=requests.Session()
        self.s.headers.update({"Authorization":token,"Content-Type":"application/json",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7",
            "X-Super-Properties":make_sp(fetch_build()),"X-Discord-Locale":"en-US",
            "X-Discord-Timezone":"Asia/Ho_Chi_Minh","Origin":"https://discord.com",
            "Referer":"https://discord.com/channels/@me"})
    def get(self,p,**kw):          return self.s.get(f"{API_BASE}{p}",**kw)
    def post(self,p,payload=None): return self.s.post(f"{API_BASE}{p}",json=payload)
    def validate(self):
        try:
            r=self.get("/users/@me"); return r.json() if r.status_code==200 else None
        except: return None


def _g(d,*keys):
    if not d: return None
    for k in keys:
        if k in d: return d[k]
    return None

def q_name(q):
    cfg=q.get("config",{}); msgs=cfg.get("messages",{})
    n=_g(msgs,"questName","quest_name") or _g(msgs,"gameTitle","game_title")
    if n: return n.strip()
    return cfg.get("application",{}).get("name") or f"Quest#{q.get('id','?')}"

def q_expires(q): return _g(q.get("config",{}),"expiresAt","expires_at")
def q_ustatus(q):
    us=_g(q,"userStatus","user_status"); return us if isinstance(us,dict) else {}
def q_tc(q):
    cfg=q.get("config",{})
    return _g(cfg,"taskConfig","task_config","taskConfigV2","task_config_v2")
def q_tt(q):
    tc=q_tc(q)
    if not tc or "tasks" not in tc: return None
    for t in SUPPORTED_TASKS:
        if tc["tasks"].get(t) is not None: return t
    return None
def q_sneed(q):
    tc=q_tc(q); tt=q_tt(q)
    return tc["tasks"][tt].get("target",0) if tc and tt else 0
def q_sdone(q):
    tt=q_tt(q)
    if not tt: return 0
    return (q_ustatus(q).get("progress",{}) or {}).get(tt,{}).get("value",0)
def q_enrolled_at(q): return _g(q_ustatus(q),"enrolledAt","enrolled_at")
def q_enrolled(q):    return bool(q_enrolled_at(q))
def q_completed(q):   return bool(_g(q_ustatus(q),"completedAt","completed_at"))
def q_completable(q):
    exp=q_expires(q)
    if exp:
        try:
            if datetime.fromisoformat(exp.replace("Z","+00:00"))<=datetime.now(timezone.utc): return False
        except: pass
    tc=q_tc(q)
    return bool(tc and "tasks" in tc and any(tc["tasks"].get(t) is not None for t in SUPPORTED_TASKS))

def q_reward(q):
    rewards=q.get("config",{}).get("rewards_config",{}).get("rewards") or []
    parts=[]
    for r in rewards:
        if not isinstance(r,dict): continue
        rtype=r.get("type"); name=r.get("messages",{}).get("name","").strip()
        if rtype==4:
            qty=r.get("orb_quantity") or r.get("premium_orb_quantity") or 0
            parts.append(f"🔮 {qty} Orbs" if qty else f"🔮 {name or 'Orbs'}")
        elif rtype==1: parts.append(f"🎁 {name or 'Item'}")
        elif rtype==3: parts.append(f"✨ {name or 'Collectible'}")
        else:          parts.append(f"🎀 {name or f'Type{rtype}'}")
    return " · ".join(parts) if parts else "Phần thưởng"

def q_timeleft(q):
    exp=q_expires(q)
    if not exp: return ""
    try:
        delta=datetime.fromisoformat(exp.replace("Z","+00:00"))-datetime.now(timezone.utc)
        tot=int(delta.total_seconds())
        if tot<=0: return c("Hết hạn",RD,BD)
        d,rem=divmod(tot,86400); h,rem=divmod(rem,3600); m=rem//60
        if d:   return c(f"{d}d{h}h",GR)
        elif h: return c(f"{h}h{m}m",YL)
        return  c(f"{m}p",RD,BD)
    except: return ""


def get_sess(aid):
    if aid not in sessions:
        sessions[aid]={"api":None,"completer":None,"running":False,"thread":None,
            "progress_log":[],"current_quest":None,"current_progress":(0,0),
            "queue_index":0,"queue_total":0,"start_time":None,"target":None,"autofarm_pending":False}
    return sessions[aid]

def restore(aid):
    s=get_sess(aid)
    if s.get("api"): return True
    row=db_get(aid)
    if not row: return False
    api=DiscordAPI(row["token"]); d=api.validate()
    if not d: return False
    s["api"]=api; s["completer"]=QuestCompleter(api,aid); s["target"]=d; return True


class QuestCompleter:
    def __init__(self,api,aid): self.api=api; self.aid=aid; self.done_ids=set()

    def _s(self): return get_sess(self.aid)

    def _log(self,msg):
        s=self._s(); logs=s.get("progress_log",[])
        ts=datetime.now().strftime("%H:%M:%S")
        clean=re.sub(r'\*\*(.+?)\*\*',r'\1',msg); clean=re.sub(r'`(.+?)`',r'\1',clean)
        entry={"ts":ts,"msg":clean,"raw":msg}
        logs.append(entry); s["progress_log"]=logs[-80:]

    def fetch(self):
        try:
            r=self.api.get("/quests/@me")
            if r.status_code!=200: return []
            data=r.json(); return data.get("quests",data) if isinstance(data,dict) else data
        except: return []

    def enroll(self,q):
        qid=q["id"]
        for _ in range(3):
            try:
                r=self.api.post(f"/quests/{qid}/enroll",{"location":11,"is_targeted":False,
                    "metadata_raw":None,"metadata_sealed":None,
                    "traffic_metadata_raw":q.get("traffic_metadata_raw"),
                    "traffic_metadata_sealed":q.get("traffic_metadata_sealed")})
                if r.status_code==429: time.sleep(r.json().get("retry_after",5)+1); continue
                return r.status_code in (200,201,204)
            except: return False
        return False

    def auto_enroll(self,quests):
        if not AUTO_ACCEPT: return quests
        need=[q for q in quests if not q_enrolled(q) and not q_completed(q) and q_completable(q)]
        for q in need:
            if self.enroll(q): self._log(f"✅ Đã nhận: **{q_name(q)}**")
            time.sleep(3)
        if need: time.sleep(2); return self.fetch()
        return quests

    def do_video(self,q):
        name=q_name(q); qid=q["id"]; sn=q_sneed(q); sd=q_sdone(q)
        eat=q_enrolled_at(q)
        ets=(datetime.fromisoformat(eat.replace("Z","+00:00")).timestamp() if eat else time.time())
        self._log(f"🎬 Bắt đầu: **{name}** ({sd:.0f}/{sn}s)")
        mf,spd,iv=10,7,1
        while sd<sn:
            if not self._s().get("running"): return
            ma=(time.time()-ets)+mf; ts=sd+spd
            if (ma-sd)>=spd:
                try:
                    r=self.api.post(f"/quests/{qid}/video-progress",{"timestamp":min(sn,ts+random.random())})
                    if r.status_code==200:
                        if r.json().get("completed_at"): self._log(f"✅ **{name}**"); return
                        sd=min(sn,ts); self._s()["current_progress"]=(sd,sn)
                    elif r.status_code==429: time.sleep(r.json().get("retry_after",5)+1); continue
                except Exception as e: self._log(f"❌ {e}")
            if ts>=sn:
                try: self.api.post(f"/quests/{qid}/video-progress",{"timestamp":sn})
                except: pass
                self._log(f"✅ **{name}**"); return
            time.sleep(iv)

    def do_heartbeat(self,q):
        name=q_name(q); qid=q["id"]; tt=q_tt(q); sn=q_sneed(q); sd=q_sdone(q)
        pid=random.randint(1000,30000)
        self._log(f"{TASK_LABEL.get(tt,'🎮')} Bắt đầu: **{name}** (~{max(0,sn-sd)//60}p)")
        completed=False
        while sd<sn:
            if not self._s().get("running"): return
            try:
                r=self.api.post(f"/quests/{qid}/heartbeat",{"stream_key":f"call:0:{pid}","terminal":False})
                if r.status_code==200:
                    body=r.json(); prog=body.get("progress",{})
                    if prog and tt in prog: sd=prog[tt].get("value",sd)
                    self._s()["current_progress"]=(sd,sn)
                    if body.get("completed_at") or sd>=sn: completed=True; break
                elif r.status_code==429: time.sleep(r.json().get("retry_after",10)+1); continue
            except Exception as e: self._log(f"❌ {e}")
            time.sleep(HEARTBEAT_INTERVAL)
        try: self.api.post(f"/quests/{qid}/heartbeat",{"stream_key":f"call:0:{pid}","terminal":True})
        except: pass
        if completed: self._log(f"✅ **{name}**")

    def do_activity(self,q):
        name=q_name(q); qid=q["id"]; sk="call:0:1"; sn=q_sneed(q); sd=q_sdone(q)
        self._log(f"🕹️  Bắt đầu: **{name}** (~{max(0,sn-sd)//60}p)")
        completed=False
        while sd<sn:
            if not self._s().get("running"): return
            try:
                r=self.api.post(f"/quests/{qid}/heartbeat",{"stream_key":sk,"terminal":False})
                if r.status_code==200:
                    body=r.json(); prog=body.get("progress",{})
                    if prog and "PLAY_ACTIVITY" in prog: sd=prog["PLAY_ACTIVITY"].get("value",sd)
                    self._s()["current_progress"]=(sd,sn)
                    if body.get("completed_at") or sd>=sn: completed=True; break
                elif r.status_code==429: time.sleep(r.json().get("retry_after",10)+1); continue
            except Exception as e: self._log(f"❌ {e}")
            time.sleep(HEARTBEAT_INTERVAL)
        try: self.api.post(f"/quests/{qid}/heartbeat",{"stream_key":sk,"terminal":True})
        except: pass
        if completed: self._log(f"✅ **{name}**")

    def process(self,q):
        tt=q_tt(q); qid=q.get("id")
        if not tt or qid in self.done_ids: return
        s=self._s(); s["current_quest"]=q_name(q); s["current_progress"]=(q_sdone(q),q_sneed(q))
        if tt in ("WATCH_VIDEO","WATCH_VIDEO_ON_MOBILE"): self.do_video(q)
        elif tt in ("PLAY_ON_DESKTOP","STREAM_ON_DESKTOP"): self.do_heartbeat(q)
        elif tt=="PLAY_ACTIVITY": self.do_activity(q)
        self.done_ids.add(qid)

    def run_list(self,ids):
        quests=self.auto_enroll(self.fetch()); qmap={q["id"]:q for q in quests}; total=len(ids)
        for idx,qid in enumerate(ids,1):
            if not self._s().get("running"): break
            q=qmap.get(qid)
            if q and q_enrolled(q) and not q_completed(q) and q_completable(q):
                self._s()["queue_index"]=idx; self._s()["queue_total"]=total
                self.process(q)
        s=self._s()
        if s.get("running"): self._log("🏁 **Hoàn thành tất cả quest!**")
        s["running"]=False; s["current_quest"]=None


def start_farm(aid,ids):
    s=get_sess(aid); c_=s["completer"]; c_.done_ids.clear()
    s["running"]=True; s["start_time"]=datetime.now()
    logs=s.get("progress_log",[])
    if logs: logs.append({"ts":"──────","msg":"────────────────────────────────────","raw":""})
    s["progress_log"]=logs
    def _run():
        try: c_.run_list(ids)
        except Exception as e: s["progress_log"].append({"ts":datetime.now().strftime("%H:%M:%S"),"msg":f"❌ Lỗi: {e}","raw":""})
        finally: s["running"]=False
    t=threading.Thread(target=_run,daemon=True); s["thread"]=t; t.start()

def _do_autofarm(aid,silent=False):
    s=get_sess(aid); c_=s.get("completer")
    if not c_ or s.get("running") or s.get("autofarm_pending"): return
    s["autofarm_pending"]=True
    try:
        if s.get("running"): return
        all_q=c_.auto_enroll(c_.fetch())
        avail=[q for q in all_q if q_completable(q) and not q_completed(q) and q["id"] not in c_.done_ids]
        if not avail: return
        if not silent:
            row=db_get(aid); tag=row["username"] if row else f"#{aid}"
            pr(c(f"\n  🤖  AutoFarm [{tag}] — {len(avail)} quest mới!\n",MG,BD))
        start_farm(aid,[q["id"] for q in avail])
    except Exception as e: pr(c(f"  ✘  AutoFarm #{aid}: {e}",RD))
    finally: s["autofarm_pending"]=False

def _af_bg():
    while True:
        time.sleep(AUTOFARM_POLL)
        try:
            for aid in db_af_all():
                if not restore(aid): continue
                s=get_sess(aid)
                if s.get("running"): continue
                threading.Thread(target=_do_autofarm,args=(aid,),daemon=True).start()
        except: pass

def ensure_af():
    global _af_alive
    if not _af_alive:
        _af_alive=True
        threading.Thread(target=_af_bg,daemon=True).start()


W=58

def _row(content, lc=CY, rpad=True):
    txt=" "+content+" "
    p=W-2-vlen(txt)
    return c("║",lc)+txt+(" "*max(0,p) if rpad else "")+c("║",lc)

def _top(title="", lc=CY):
    if title:
        tl=vlen(title); lpad=(W-2-tl)//2; rpad=W-2-tl-lpad
        pr(c("╔"+"═"*lpad,lc)+title+c("═"*rpad+"╗",lc))
    else:
        pr(c("╔"+"═"*(W-2)+"╗",lc))

def _mid(lc=CY):  pr(c("╠"+"═"*(W-2)+"╣",lc))
def _bot(lc=CY):  pr(c("╚"+"═"*(W-2)+"╝",lc))
def _sep(lc=CY):  pr(c("║"+"─"*(W-2)+"║",lc))
def _emp(lc=CY):  pr(c("║"+" "*(W-2)+"║",lc))


def print_dashboard():
    rows=db_list()
    title=c("  🎮  TZUAN QUEST TOOL  ",WH,BD)
    _top(title,MG)
    _emp(MG)

    if not rows:
        pr(_row(c("  Chưa có tài khoản — nhấn [1] để thêm",WH,DM),MG))
    else:
        for r in rows:
            s=sessions.get(r["id"],{})
            af=c(" ◆AF",GR,BD) if db_af_get(r["id"]) else ""
            chip,running=_status_chip(r["id"])
            id_tag=c(f" #{r['id']} ",BGC+WH,BD) if not running else c(f" #{r['id']} ",BGY+WH,BD)
            name=c(f" {r['username']} ",WH,BD)
            ln=id_tag+name+af+" "+chip
            pr(_row(ln,MG))

    _emp(MG); _mid(MG)
    menu=[("1",MG,"👤  Quản lý tài khoản"),("2",GR,"🎯  Farm Quest"),
          ("3",CY,"🤖  AutoFarm"),("4",RD,"🛑  Dừng Farm"),("0",WH,"❌  Thoát")]
    for k,kc,label in menu:
        kb=c(f" {k} ",BGM+WH,BD) if kc==MG else c(f" {k} ",BGN+WH,BD) if kc==GR else \
           c(f" {k} ",BGC+WH,BD) if kc==CY else c(f" {k} ",BGR+WH,BD) if kc==RD else \
           c(f" {k} ",WH+DM,BD)
        pr(_row(f"  {kb}  {c(label,kc,BD)}",MG))
    _bot(MG)
    pr()


def live_progress(aid):
    row=db_get(aid)
    name=row["username"] if row else f"#{aid}"
    last_log_count=0
    _stop_flag=threading.Event()

    def _watcher():
        while not _stop_flag.is_set():
            time.sleep(LIVE_REFRESH)
            s=get_sess(aid)
            if not s.get("running"):
                _stop_flag.set()

    t=threading.Thread(target=_watcher,daemon=True); t.start()

    pr(c(f"\n  ╔══ 🔴 LIVE — {name} ══════════════════════════════╗",RD,BD))
    pr(c(f"  ║  Đang farm... log cập nhật tự động               ║",RD))
    pr(c(f"  ║  Nhấn Ctrl+C để về menu (farm vẫn chạy ngầm)     ║",RD))
    pr(c(f"  ╚═══════════════════════════════════════════════════╝",RD,BD))

    try:
        while True:
            s=get_sess(aid); running=s.get("running",False)
            logs=s.get("progress_log",[])

            if len(logs)>last_log_count:
                new_entries=logs[last_log_count:]
                for entry in new_entries:
                    ts=entry["ts"]; msg=entry["msg"]
                    if "✅" in msg or "🏁" in msg:
                        tag=c(f"[{ts}]",GR,BD); line=c(msg,GR,BD)
                    elif "❌" in msg:
                        tag=c(f"[{ts}]",RD,BD); line=c(msg,RD)
                    elif "──" in ts:
                        pr(c("  ├"+"─"*50,WH,DM)); last_log_count+=1; continue
                    elif any(e in msg for e in ["🎬","🎮","📺","📱","🕹","🤖","✅ Đã nhận"]):
                        tag=c(f"[{ts}]",CY,BD); line=c(msg,CY)
                    else:
                        tag=c(f"[{ts}]",WH,DM); line=c(msg,WH)

                    sd2,sn2=s.get("current_progress",(0,0))
                    pct2=int(sd2/sn2*100) if sn2 else 0
                    bar=grad_bar(pct2,16)
                    qi=s.get("queue_index",0); qt=s.get("queue_total",0)
                    q_chip=c(f"[{qi}/{qt}]",YL,BD) if qt else ""
                    pr(f"  {tag} {line}")
                    if any(e in msg for e in ["🎬","🎮","📺","📱","🕹"]):
                        pr(c(f"  │  Tiến độ: ",WH)+bar+c(f"  {q_chip}",WH))
                    last_log_count+=1

            if not running:
                pr(c("\n  ╔══════════════════════════════════════════════════╗",GR,BD))
                pr(c("  ║  ✅  FARM HOÀN THÀNH!                            ║",GR,BD))
                pr(c("  ╚══════════════════════════════════════════════════╝",GR,BD))
                break

            if s.get("running"):
                cq=s.get("current_quest") or "..."; sd2,sn2=s.get("current_progress",(0,0))
                pct2=int(sd2/sn2*100) if sn2 else 0
                st_line=c(f"  ├─ ⚙  {cq[:38]}  ",WH,DM)+grad_bar(pct2,14)
                with _lk: print(f"\r{vis(st_line):<70}", end="\r", flush=True)

            time.sleep(0.5)
    except KeyboardInterrupt:
        _stop_flag.set()
        pr(c("\n\n  ← Về menu (farm vẫn chạy ngầm)",WH,DM))
        return

    _stop_flag.set()
    wait_enter()


def menu_accounts():
    while True:
        clr(); rows=db_list()
        _top(c(" 👤 QUẢN LÝ TÀI KHOẢN ",WH,BD),CY); _emp()
        if rows:
            for r in rows:
                s=sessions.get(r["id"],{})
                af=c(" ◆AF",GR,BD) if db_af_get(r["id"]) else ""
                run=c(" ⚙ Đang farm",YL,BD) if s.get("running") else c(" ○ Rảnh",WH,DM)
                id_b=c(f" #{r['id']} ",BGC+WH,BD)
                pr(_row(f"{id_b}  {c(r['username'],WH,BD)}{af}{run}  {c(r['added_at'],WH,DM)}"))
        else:
            pr(_row(c("  (Trống)",WH,DM)))
        _emp(); _mid()
        for k,label in [("1","➕  Thêm tài khoản"),("3","🗑️   Xoá tài khoản"),("0","←   Quay lại")]:
            pr(_row(f"  {c(f' {k} ',BGM+WH,BD)}  {c(label,WH,BD)}"))
        _bot(); pr()
        ch=ask("Chọn")
        if   ch=="0": break
        elif ch=="1": _add_account()
        elif ch=="3": _del_account()

def _add_account():
    clr()
    _top(c(" ➕ THÊM TÀI KHOẢN ",WH,BD),GR); _emp()
    _bot(GR); pr()
    token=ask("Nhập Token")
    if not token: pr(c("  ✘  Token trống!",RD,BD)); wait_enter(); return
    pr(c("  ●  Đang xác thực...",CY))
    api=DiscordAPI(token); d=api.validate()
    if not d: pr(c("  ✘  Token không hợp lệ!",RD,BD)); wait_enter(); return
    username=d.get("username","?"); uid=d.get("id","?"); gname=d.get("global_name") or username
    aid=db_add(token,username,uid)
    s=get_sess(aid); s["api"]=api; s["completer"]=QuestCompleter(api,aid); s["target"]=d
    pr()
    pr(c(f"  ✔  Đã thêm  #{aid}",GR,BD))
    pr(c(f"     Tên: {gname}  (@{username})",WH))
    pr(c(f"     Discord ID: {uid}",WH,DM))
    wait_enter()

def _del_account():
    row=pick_account("xoá")
    if not row: wait_enter(); return
    if sessions.get(row["id"],{}).get("running"):
        pr(c("  ▲  Đang farm! Dừng trước ([4]).",YL,BD)); wait_enter(); return
    if ask(f"Xoá @{row['username']}? (y/n)",default="n").lower()!="y":
        pr(c("  Đã huỷ.",WH,DM)); wait_enter(); return
    db_del(row["id"])
    if row["id"] in sessions: del sessions[row["id"]]
    pr(c("  ✔  Đã xoá.",GR,BD)); wait_enter()


def menu_farm():
    clr()
    row=pick_account("farm")
    if not row: wait_enter(); return
    aid=row["id"]
    if not restore(aid):
        pr(c("  ✘  Không kết nối được. Token hết hạn?",RD,BD)); wait_enter(); return
    s=get_sess(aid)
    if s.get("running"):
        pr(c("  ▲  Đang farm rồi! Xem live ngay:",YL,BD))
        if ask("Xem live progress? (y/n)",default="y").lower()=="y":
            live_progress(aid)
        return
    c_=s["completer"]; target=s.get("target",{}); dname=target.get("global_name") or target.get("username",f"#{aid}")
    pr(c(f"  ●  Đang tải quest của {dname}...",CY))
    all_q=c_.fetch()
    if not all_q: pr(c("  ▲  Không có quest nào!",YL)); wait_enter(); return

    available=[q for q in all_q if q_completable(q) and not q_completed(q)]
    done_q=[q for q in all_q if q_completed(q)]

    clr()
    title=c(f" 📋 Quest — {dname[:30]} ",WH,BD)
    _top(title,GR)
    stat_line=(c(f" Tổng: {len(all_q)} ",WH)+
               c(f" ✅ Xong: {len(done_q)} ",GR,BD)+c(" │ ",WH,DM)+
               c(f" 🔥 Farm được: {len(available)} ",YL,BD))
    pr(_row(stat_line,GR))

    if done_q:
        _sep(GR)
        pr(_row(c("  ✅  Đã hoàn thành:",GR,BD),GR))
        for q in done_q[:4]:
            pr(_row(c(f"     ✔  {q_name(q)[:44]}",GR),GR))
        if len(done_q)>4: pr(_row(c(f"     … +{len(done_q)-4} nữa",WH,DM),GR))

    if not available:
        _sep(GR); pr(_row(c("  🎉  Tất cả quest đã xong!",GR,BD),GR)); _bot(GR)
        wait_enter(); return

    _sep(GR)
    pr(_row(c(f"  🔥  Có thể farm ({len(available)}):",YL,BD),GR))
    _bot(GR); pr()

    for i,q in enumerate(available[:25],1):
        tt=q_tt(q) or "?"; sn=q_sneed(q); sd=q_sdone(q); pct=int(sd/sn*100) if sn else 0
        mleft=max(0,sn-sd)//60; rwd=q_reward(q); tl=q_timeleft(q)
        enr=c("▶",GR,BD) if q_enrolled(q) else c("○",WH,DM)
        tc=TASK_COL.get(tt,WH)
        num_b=c(f" {i:2d} ",BGM+WH,BD)
        type_b=c(f" {TASK_LABEL.get(tt,'?')} ",tc,BD)
        pr(f"  {num_b} {type_b}  {c(q_name(q)[:35],WH,BD)}")
        bar=grad_bar(pct,18)
        pr(c(f"         {enr} ",WH)+bar+c(f"  ~{mleft}p  ",WH,DM)+tl)
        pr(c(f"         🎁 {rwd[:52]}",MG))
        pr()

    pr(c("  ─────────────────────────────────────────────────────",WH,DM))
    pr(c("  Nhập số, cách nhau bởi cách/phẩy. Ví dụ:  1 3 2",WH))
    pr(c("  Enter hoặc  a  →  farm TẤT CẢ",WH,DM)); pr()

    raw=ask("Chọn quest").strip().lower()
    if raw in ("","a","all"):
        ordered=available
    else:
        try: nums=[int(x) for x in re.split(r'[\s,，]+',raw) if x]
        except ValueError: pr(c("  ✘  Chỉ nhập số!",RD)); wait_enter(); return
        bad=[n for n in nums if n<1 or n>len(available)]
        if bad: pr(c(f"  ✘  Số không hợp lệ: {bad}",RD)); wait_enter(); return
        seen=set(); ordered=[]
        for n in nums:
            if n not in seen: ordered.append(available[n-1]); seen.add(n)

    pr()
    _top(c(f" Kế hoạch farm ({len(ordered)} quest) ",WH,BD),YL)
    for j,q in enumerate(ordered,1):
        tt=q_tt(q); tc=TASK_COL.get(tt,WH)
        pr(_row(f"  {c(str(j),YL,BD)}.  {c(TASK_LABEL.get(tt,'?'),tc)}  {c(q_name(q)[:40],WH)}",YL))
    _bot(YL); pr()

    if ask(f"Bắt đầu? (y/n)",default="y").lower()!="y":
        pr(c("  Đã huỷ.",WH,DM)); wait_enter(); return

    start_farm(aid,[q["id"] for q in ordered])
    live_progress(aid)


def menu_autofarm():
    clr(); row=pick_account()
    if not row: wait_enter(); return
    aid=row["id"]
    if not restore(aid): pr(c("  ✘  Không kết nối được.",RD,BD)); wait_enter(); return
    s=get_sess(aid); target=s.get("target",{}); dname=target.get("global_name") or target.get("username",f"#{aid}")
    cur=db_af_get(aid)
    clr()
    st_b=c(f" {'🟢 BẬT' if cur else '🔴 TẮT'} ",BGN+WH,BD) if cur else c(f" {'🔴 TẮT'} ",BGR+WH,BD)
    _top(c(f" 🤖 AutoFarm — {dname[:28]} ",WH,BD),CY); _emp()
    pr(_row(f"  Trạng thái:  {st_b}"))
    pr(_row(c(f"  Chu kỳ: mỗi {AUTOFARM_POLL//60} phút tự tìm & farm quest mới",WH,DM)))
    _emp(); _mid()
    pr(_row(f"  {c(' 1 ',BGN+WH,BD)}  {c('🟢  Bật AutoFarm',GR,BD)}"))
    pr(_row(f"  {c(' 2 ',BGR+WH,BD)}  {c('🔴  Tắt AutoFarm',RD,BD)}"))
    pr(_row(f"  {c(' 0 ',WH+DM,BD)}  ←   Quay lại"))
    _bot(); pr()
    ch=ask("Chọn",default="0")
    if ch not in ("1","2"): return
    enable=(ch=="1"); db_af_set(aid,enable)
    if enable:
        ensure_af()
        pr(c(f"  ✔  AutoFarm BẬT  →  {dname}",GR,BD))
        pr(c(f"  ●  Kiểm tra quest mới mỗi {AUTOFARM_POLL//60} phút. Config lưu DB.",CY))
    else: pr(c(f"  ✔  AutoFarm TẮT  →  {dname}",YL,BD))
    wait_enter()


def menu_stop():
    clr(); running=[(aid,s) for aid,s in sessions.items() if s.get("running")]
    if not running: pr(c("  ●  Không ai đang farm.",CY)); wait_enter(); return
    _top(c(" 🛑 DỪNG FARM ",WH,BD),RD); _emp()
    for aid,s in running:
        row=db_get(aid); name=row["username"] if row else f"#{aid}"
        cq=s.get("current_quest") or "..."; qi=s.get("queue_index",0); qt=s.get("queue_total",0)
        sd,sn=s.get("current_progress",(0,0)); pct=int(sd/sn*100) if sn else 0
        id_b=c(f" #{aid} ",BGR+WH,BD)
        pr(_row(f"{id_b}  {c(name,WH,BD)}  ⚙  {c(cq[:28],YL)}  {c(f'{pct}% ({qi}/{qt})',YL,BD)}",RD))
    _emp(); _mid(RD)
    pr(_row(c("  [ID]  Dừng 1 tài khoản    [a]  Dừng TẤT CẢ    [0]  Quay lại",WH),RD))
    _bot(RD); pr()
    ch=ask("Chọn").lower()
    if ch=="0": return
    if ch in ("a","all"):
        for aid,s in running: s["running"]=False
        pr(c(f"  ✔  Đã dừng {len(running)} tài khoản.",GR,BD))
    else:
        try:
            aid=int(ch); s=sessions.get(aid)
            if s and s.get("running"):
                s["running"]=False; row=db_get(aid)
                pr(c(f"  ✔  Đã dừng #{aid} ({row['username'] if row else '?'}).",GR,BD))
            else: pr(c(f"  ✘  #{aid} không đang farm.",RD))
        except ValueError: pr(c("  ✘  Nhập số ID hoặc 'a'.",RD))
    wait_enter()


def startup():
    clr()
    pr(c("╔══════════════════════════════════════════════════════╗",MG,BD))
    pr(c("║",MG,BD)+c("    🎮  TZUAN QUEST TOOL  — Đang khởi động...  ",WH,BD)+c("║",MG,BD))
    pr(c("╚══════════════════════════════════════════════════════╝",MG,BD)); pr()
    db_init()
    for row in db_list():
        if restore(row["id"]):
            pr(c(f"  ✔  #{row['id']} @{row['username']}",GR))
        else:
            pr(c(f"  ▲  #{row['id']} @{row['username']}  — token lỗi/hết hạn",YL))
    if db_af_all(): ensure_af(); pr(c("  🤖  AutoFarm đang chạy ngầm.",MG))
    if not db_list(): pr(c("  Chào mừng! Nhấn [1] → [1] để thêm tài khoản đầu tiên.",CY,BD))
    time.sleep(1)


def main():
    startup()
    handlers={"1":menu_accounts,"2":menu_farm,"3":menu_autofarm,"4":menu_stop}
    while True:
        clr(); print_dashboard()
        try: ch=input(c("  ▶  Chọn  ",YL,BD)).strip()
        except (KeyboardInterrupt,EOFError):
            for _,s in sessions.items():
                if s.get("running"): s["running"]=False
            pr(c("\n  👋  Tạm biệt!\n",GR,BD)); sys.exit(0)
        if ch=="0":
            for _,s in sessions.items():
                if s.get("running"): s["running"]=False
            pr(c("\n  👋  Tạm biệt!\n",GR,BD)); sys.exit(0)
        elif ch in handlers: clr(); handlers[ch]()
        else: pr(c("  Chọn 0–4!",RD)); time.sleep(0.7)

if __name__=="__main__":
    main()
