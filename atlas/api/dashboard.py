from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heimdall</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg:#080a0e;
  --bg1:#0c0f14;
  --bg2:#111520;
  --bg3:#161c2a;
  --border:#1e2535;
  --border2:#252f45;
  --amber:#f5a623;
  --amber2:#ffc55a;
  --amber-dim:#3a2800;
  --red:#ff4757;
  --green:#2ed573;
  --blue:#3d9eff;
  --text:#dce3f0;
  --text2:#8899bb;
  --text3:#4a5a7a;
  --font:'Geist Mono',monospace;
  --sidebar:220px;
  --topbar:48px;
}

html,body{height:100%;overflow:hidden}
body{font-family:var(--font);background:var(--bg);color:var(--text);display:flex;flex-direction:column}

/* ── Scanline overlay ── */
body::before{
  content:'';position:fixed;inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 4px);
  pointer-events:none;z-index:9999
}

/* ── Top command bar ── */
.cmdbar{
  height:var(--topbar);flex-shrink:0;
  background:var(--bg1);border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:0;
  position:relative;z-index:100
}
.cmdbar-logo{
  width:var(--sidebar);flex-shrink:0;
  display:flex;align-items:center;gap:.6rem;
  padding:0 1.1rem;border-right:1px solid var(--border);height:100%
}
.cmdbar-logo-mark{
  width:22px;height:22px;border:1.5px solid var(--amber);
  display:flex;align-items:center;justify-content:center;
  font-size:.6rem;font-weight:700;color:var(--amber);letter-spacing:.05em;
  flex-shrink:0
}
.cmdbar-logo-text{font-size:.72rem;font-weight:600;color:var(--text);letter-spacing:.12em;text-transform:uppercase}
.cmdbar-logo-sub{font-size:.58rem;color:var(--text3);letter-spacing:.08em;margin-top:1px}
.cmdbar-nav{display:flex;align-items:center;height:100%;flex:1}
.nav-tab{
  height:100%;padding:0 1.2rem;
  display:flex;align-items:center;gap:.45rem;
  font-size:.68rem;font-weight:500;color:var(--text3);
  letter-spacing:.1em;text-transform:uppercase;cursor:pointer;
  border-right:1px solid var(--border);position:relative;
  transition:color .15s;user-select:none
}
.nav-tab:hover{color:var(--text2)}
.nav-tab.active{color:var(--amber)}
.nav-tab.active::after{
  content:'';position:absolute;bottom:0;left:0;right:0;height:2px;background:var(--amber)
}
.nav-tab-icon{font-size:.8rem;opacity:.7}
.cmdbar-right{display:flex;align-items:center;gap:.5rem;margin-left:auto;padding:0 1rem}
.status-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;animation:pulse-dot 2s infinite}
@keyframes pulse-dot{0%,100%{opacity:1}50%{opacity:.4}}
.status-dot.ok{background:var(--green)}
.status-dot.err{background:var(--red)}
.status-dot.warn{background:var(--amber)}
.status-label{font-size:.62rem;color:var(--text3);letter-spacing:.06em}
.model-btn{
  background:var(--bg2);border:1px solid var(--border2);
  color:var(--text2);font-family:var(--font);font-size:.65rem;
  padding:.25rem .6rem;border-radius:3px;cursor:pointer;
  display:flex;align-items:center;gap:.4rem;
  transition:border-color .15s,color .15s;letter-spacing:.06em
}
.model-btn:hover{border-color:var(--amber);color:var(--amber)}
.model-btn .chevron{font-size:.5rem;opacity:.5}

/* ── Layout ── */
.layout{display:flex;flex:1;overflow:hidden;position:relative}

/* ── Panels ── */
.panel{display:none;flex:1;overflow:hidden;flex-direction:column}
.panel.active{display:flex}

/* ══════════════════════════════════════
   CHAT PANEL
══════════════════════════════════════ */
.chat-wrap{display:flex;flex:1;overflow:hidden}

/* Left gutter — thread list */
.thread-list{
  width:var(--sidebar);flex-shrink:0;
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;
  background:var(--bg1)
}
.thread-header{
  padding:.6rem .8rem;border-bottom:1px solid var(--border);
  font-size:.6rem;font-weight:600;color:var(--text3);
  letter-spacing:.12em;text-transform:uppercase;
  display:flex;justify-content:space-between;align-items:center
}
.new-thread-btn{
  background:none;border:1px solid var(--border2);color:var(--text3);
  font-family:var(--font);font-size:.6rem;padding:.15rem .4rem;
  border-radius:2px;cursor:pointer;transition:all .15s
}
.new-thread-btn:hover{border-color:var(--amber);color:var(--amber)}
.thread-items{flex:1;overflow-y:auto;padding:.3rem 0}
.thread-item{
  padding:.5rem .8rem;cursor:pointer;
  border-left:2px solid transparent;
  transition:background .1s
}
.thread-item:hover{background:var(--bg2)}
.thread-item.active{background:var(--bg2);border-left-color:var(--amber)}
.thread-item-title{font-size:.68rem;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.thread-item-meta{font-size:.58rem;color:var(--text3);margin-top:.2rem}

/* Chat main */
.chat-main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.chat-messages{
  flex:1;overflow-y:auto;padding:1.5rem 2rem;
  display:flex;flex-direction:column;gap:1.2rem
}
.chat-messages::-webkit-scrollbar{width:3px}
.chat-messages::-webkit-scrollbar-thumb{background:var(--border2);border-radius:99px}

.msg{display:flex;gap:.75rem;animation:msg-in .2s ease}
@keyframes msg-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.msg.user{flex-direction:row-reverse}
.msg.user .msg-body{align-items:flex-end}

.msg-avatar{
  width:28px;height:28px;flex-shrink:0;margin-top:2px;
  display:flex;align-items:center;justify-content:center;
  font-size:.7rem;font-weight:700;letter-spacing:.05em
}
.msg.assistant .msg-avatar{
  border:1px solid var(--border2);color:var(--amber);
  background:var(--amber-dim)
}
.msg.user .msg-avatar{
  border:1px solid var(--border2);color:var(--text3);background:var(--bg3)
}

.msg-body{display:flex;flex-direction:column;gap:.3rem;max-width:72%}
.msg-bubble{
  background:var(--bg2);border:1px solid var(--border);
  padding:.7rem .9rem;font-size:.8rem;line-height:1.65;
  border-radius:2px 8px 8px 8px
}
.msg.user .msg-bubble{
  background:var(--bg3);border-color:var(--border2);
  border-radius:8px 2px 8px 8px;color:var(--text2)
}
.msg-meta{font-size:.58rem;color:var(--text3);letter-spacing:.04em}
.msg.user .msg-meta{text-align:right}

/* MD rendering inside bubbles */
.md-content p{margin:0 0 .5em}
.md-content p:last-child{margin-bottom:0}
.md-content h1,.md-content h2,.md-content h3{
  font-weight:600;margin:.7em 0 .3em;color:var(--amber)
}
.md-content h1{font-size:.95rem}
.md-content h2{font-size:.88rem}
.md-content h3{font-size:.82rem}
.md-content ul,.md-content ol{padding-left:1.3em;margin:.3em 0 .5em}
.md-content li{margin-bottom:.2em}
.md-content code{
  background:var(--bg);border:1px solid var(--border2);
  padding:.05em .35em;font-family:var(--font);font-size:.78em;color:var(--amber2)
}
.md-content pre{
  background:var(--bg);border:1px solid var(--border);
  padding:.75rem 1rem;overflow-x:auto;margin:.5em 0;border-radius:4px
}
.md-content pre code{background:none;border:none;padding:0;color:var(--text);font-size:.78rem}
.md-content blockquote{border-left:2px solid var(--amber);padding-left:.7rem;color:var(--text2);margin:.4em 0}
.md-content strong{color:var(--text);font-weight:600}
.md-content em{color:var(--text2);font-style:italic}
.md-content a{color:var(--blue);text-decoration:underline}
.md-content table{border-collapse:collapse;width:100%;margin:.5em 0;font-size:.76rem}
.md-content th,.md-content td{border:1px solid var(--border);padding:.3rem .55rem}
.md-content th{background:var(--bg3);color:var(--amber);font-weight:600}

/* context pills */
.ctx-pills{display:flex;flex-wrap:wrap;gap:.3rem}
.ctx-pill{
  font-size:.6rem;background:var(--amber-dim);border:1px solid rgba(245,166,35,.2);
  color:var(--amber);padding:.1rem .45rem;border-radius:2px;letter-spacing:.04em
}

/* Thinking */
.thinking-wrap{display:flex;gap:.75rem;animation:msg-in .2s ease}
.thinking-bubble{
  background:var(--bg2);border:1px solid var(--border);
  padding:.6rem .9rem;font-size:.75rem;color:var(--text3);
  display:flex;align-items:center;gap:.5rem;border-radius:2px 8px 8px 8px
}
.thinking-dots{display:flex;gap:3px;align-items:center}
.thinking-dots span{
  width:4px;height:4px;background:var(--amber);border-radius:50%;
  animation:blink 1.2s infinite
}
.thinking-dots span:nth-child(2){animation-delay:.2s}
.thinking-dots span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.15}40%{opacity:1}}

/* Input */
.chat-input-area{
  border-top:1px solid var(--border);background:var(--bg1);
  padding:.75rem 1.5rem .9rem;flex-shrink:0
}
.chat-input-meta{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:.5rem
}
.memory-toggle{
  display:flex;align-items:center;gap:.4rem;
  font-size:.6rem;color:var(--text3);cursor:pointer;
  user-select:none;letter-spacing:.06em
}
.memory-toggle input{accent-color:var(--amber)}
.memory-toggle:hover{color:var(--text2)}
.char-counter{font-size:.58rem;color:var(--text3)}
.chat-input-row{display:flex;gap:.6rem;align-items:flex-end}
#chat-input{
  flex:1;background:var(--bg2);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.78rem;
  padding:.55rem .8rem;resize:none;outline:none;
  min-height:38px;max-height:130px;line-height:1.55;
  border-radius:3px;transition:border-color .15s
}
#chat-input:focus{border-color:var(--amber)}
#chat-input::placeholder{color:var(--text3)}
.send-btn{
  background:var(--amber);border:none;color:#000;
  font-family:var(--font);font-size:.68rem;font-weight:700;
  padding:.5rem .9rem;border-radius:3px;cursor:pointer;
  letter-spacing:.08em;text-transform:uppercase;
  transition:background .15s;flex-shrink:0;height:38px
}
.send-btn:hover{background:var(--amber2)}
.send-btn:disabled{background:var(--border2);color:var(--text3);cursor:not-allowed}

/* ══════════════════════════════════════
   MEMORY PANEL
══════════════════════════════════════ */
.memory-wrap{display:flex;flex:1;overflow:hidden}
.mem-sidebar{
  width:260px;flex-shrink:0;border-right:1px solid var(--border);
  background:var(--bg1);display:flex;flex-direction:column;overflow:hidden
}
.mem-sidebar-section{padding:.8rem;border-bottom:1px solid var(--border)}
.sec-label{font-size:.58rem;font-weight:600;color:var(--text3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.5rem}
.mem-search-input{
  width:100%;background:var(--bg2);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.72rem;
  padding:.4rem .6rem;outline:none;border-radius:2px;
  transition:border-color .15s
}
.mem-search-input:focus{border-color:var(--amber)}
.mem-search-input::placeholder{color:var(--text3)}
.table-pills{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.4rem}
.table-pill{
  font-size:.58rem;padding:.15rem .45rem;border-radius:2px;
  border:1px solid var(--border2);color:var(--text3);cursor:pointer;
  transition:all .1s;background:none
}
.table-pill:hover{border-color:var(--amber);color:var(--amber)}
.table-pill.active{background:var(--amber-dim);border-color:var(--amber);color:var(--amber)}
.mem-action-btn{
  width:100%;background:var(--amber);border:none;
  color:#000;font-family:var(--font);font-size:.65rem;font-weight:700;
  padding:.4rem;border-radius:2px;cursor:pointer;
  letter-spacing:.08em;text-transform:uppercase;
  transition:background .15s;margin-top:.5rem
}
.mem-action-btn:hover{background:var(--amber2)}
.mem-action-btn.secondary{background:var(--bg2);border:1px solid var(--border2);color:var(--text2)}
.mem-action-btn.secondary:hover{border-color:var(--amber);color:var(--amber)}

/* Store form */
.store-form-fields{display:flex;flex-direction:column;gap:.35rem}
.store-textarea{
  width:100%;background:var(--bg);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.72rem;
  padding:.4rem .6rem;outline:none;resize:vertical;min-height:64px;
  border-radius:2px;transition:border-color .15s
}
.store-textarea:focus{border-color:var(--amber)}
.store-row{display:flex;gap:.3rem}
.store-mini-input{
  flex:1;background:var(--bg);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.68rem;
  padding:.3rem .5rem;outline:none;border-radius:2px;transition:border-color .15s
}
.store-mini-input:focus{border-color:var(--amber)}
.store-mini-select{
  background:var(--bg);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.68rem;
  padding:.3rem .5rem;outline:none;border-radius:2px;cursor:pointer;
  flex:1
}

/* Mem main */
.mem-main{flex:1;overflow-y:auto;padding:1.2rem 1.5rem;display:flex;flex-direction:column;gap:.6rem}
.mem-main::-webkit-scrollbar{width:3px}
.mem-main::-webkit-scrollbar-thumb{background:var(--border2);border-radius:99px}
.mem-empty{color:var(--text3);font-size:.72rem;text-align:center;padding:3rem 0;letter-spacing:.06em}

.mem-card{
  background:var(--bg1);border:1px solid var(--border);
  padding:.8rem 1rem;border-radius:3px;
  transition:border-color .15s;cursor:default;
  animation:msg-in .15s ease
}
.mem-card:hover{border-color:var(--border2)}
.mem-card-text{font-size:.78rem;line-height:1.6;color:var(--text);margin-bottom:.5rem}
.mem-card-footer{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap}
.mem-tag{
  font-size:.58rem;padding:.1rem .4rem;border-radius:2px;
  font-weight:600;letter-spacing:.06em
}
.tag-type{background:#0d2040;color:var(--blue)}
.tag-table{background:var(--amber-dim);color:var(--amber)}
.sim-wrap{margin-left:auto;display:flex;align-items:center;gap:.4rem}
.sim-pct{font-size:.62rem;color:var(--text3)}
.sim-bar{width:48px;height:3px;background:var(--border);border-radius:99px;overflow:hidden}
.sim-fill{height:100%;border-radius:99px;transition:width .3s}
.alert-msg{font-size:.7rem;padding:.4rem .6rem;border-radius:2px;margin-top:.3rem}
.alert-ok{background:#0a2010;border:1px solid #1a4020;color:var(--green)}
.alert-err{background:#200a0a;border:1px solid #401010;color:var(--red)}
.mem-mode-tabs{display:flex;gap:0;border:1px solid var(--border);border-radius:3px;overflow:hidden}
.mem-mode-tab{flex:1;background:none;border:none;color:var(--text3);font-family:var(--font);font-size:.62rem;font-weight:600;padding:.35rem 0;cursor:pointer;transition:all .15s;letter-spacing:.06em;text-transform:uppercase}
.mem-mode-tab:hover{color:var(--text2);background:var(--bg3)}
.mem-mode-tab.active{background:var(--amber);color:#000}
.browse-table-row{display:flex;align-items:center;justify-content:space-between;padding:.45rem .5rem;cursor:pointer;border-radius:2px;transition:background .1s;margin-bottom:.2rem}
.browse-table-row:hover{background:var(--bg3)}
.browse-table-row.active{background:var(--bg3);border-left:2px solid var(--amber);padding-left:.35rem}
.browse-table-name{font-size:.7rem;color:var(--text2)}
.browse-table-count{font-size:.62rem;font-weight:700;color:var(--amber);background:var(--amber-dim);border:1px solid rgba(245,166,35,.2);padding:.1rem .4rem;border-radius:2px;min-width:28px;text-align:center}
.mem-card-id{font-size:.58rem;color:var(--text3);font-family:var(--font);letter-spacing:.04em;margin-bottom:.25rem}
.mem-card-path{font-size:.6rem;color:var(--text3);margin-top:.2rem;word-break:break-all}

/* ══════════════════════════════════════
   SYSTEM PANEL
══════════════════════════════════════ */
.sys-wrap{flex:1;overflow-y:auto;padding:1.5rem 2rem;display:grid;grid-template-columns:1fr 1fr;gap:1rem;align-content:start}
.sys-wrap::-webkit-scrollbar{width:3px}
.sys-wrap::-webkit-scrollbar-thumb{background:var(--border2);border-radius:99px}
.sys-card{background:var(--bg1);border:1px solid var(--border);padding:1rem 1.2rem;border-radius:3px}
.sys-card.full{grid-column:1/-1}
.sys-card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.7rem}
.sys-card-title{font-size:.65rem;font-weight:600;color:var(--text3);letter-spacing:.12em;text-transform:uppercase}
.sys-badge{font-size:.6rem;font-weight:700;padding:.15rem .5rem;border-radius:2px;letter-spacing:.06em}
.badge-ok{background:#0a2010;color:var(--green)}
.badge-err{background:#200a0a;color:var(--red)}
.badge-warn{background:#201800;color:var(--amber)}
.sys-detail{font-size:.72rem;color:var(--text2);line-height:1.6}
.sys-detail code{color:var(--amber);font-size:.7rem}
.model-list{display:flex;flex-direction:column;gap:.35rem}
.model-row{display:flex;align-items:center;gap:.5rem;font-size:.72rem;padding:.4rem .6rem;background:var(--bg2);border:1px solid var(--border);border-radius:2px}
.model-row-name{color:var(--text);flex:1}
.model-row-provider{font-size:.6rem;color:var(--text3)}
.refresh-btn{
  background:none;border:1px solid var(--border2);color:var(--text3);
  font-family:var(--font);font-size:.6rem;padding:.2rem .5rem;
  border-radius:2px;cursor:pointer;transition:all .15s;letter-spacing:.06em
}
.refresh-btn:hover{border-color:var(--amber);color:var(--amber)}

/* ══════════════════════════════════════
   ROADMAP PANEL
══════════════════════════════════════ */
.road-wrap{flex:1;overflow-y:auto;padding:1.5rem 2rem}
.road-wrap::-webkit-scrollbar{width:3px}
.road-wrap::-webkit-scrollbar-thumb{background:var(--border2);border-radius:99px}
.road-phase{margin-bottom:2rem}
.road-phase-title{
  font-size:.65rem;font-weight:700;color:var(--text3);
  letter-spacing:.14em;text-transform:uppercase;
  border-bottom:1px solid var(--border);padding-bottom:.5rem;margin-bottom:.8rem;
  display:flex;align-items:center;gap:.5rem
}
.phase-status{font-size:.6rem;padding:.1rem .4rem;border-radius:2px;font-weight:700;letter-spacing:.06em}
.phase-done{background:#0a2010;color:var(--green)}
.phase-wip{background:#201800;color:var(--amber)}
.phase-todo{background:var(--bg3);color:var(--text3)}
.road-item{
  display:flex;align-items:flex-start;gap:.7rem;
  padding:.45rem 0;border-bottom:1px solid var(--border)
}
.road-item:last-child{border-bottom:none}
.road-check{width:14px;height:14px;flex-shrink:0;margin-top:1px;display:flex;align-items:center;justify-content:center}
.road-check.done{color:var(--green);font-size:.7rem}
.road-check.wip{width:12px;height:12px;border:1.5px solid var(--amber);border-radius:50%;flex-shrink:0;margin-top:2px}
.road-check.todo{width:12px;height:12px;border:1px solid var(--border2);border-radius:50%;flex-shrink:0;margin-top:2px}
.road-item-text{font-size:.73rem;color:var(--text2);line-height:1.5}
.road-item.done-item .road-item-text{color:var(--text3)}

/* ══════════════════════════════════════
   MODEL PICKER DROPDOWN
══════════════════════════════════════ */
.model-picker-wrap{position:relative}
.model-dropdown{
  position:absolute;top:calc(100% + 6px);right:0;
  background:var(--bg1);border:1px solid var(--border2);
  width:300px;z-index:999;
  box-shadow:0 12px 40px rgba(0,0,0,.6);
  border-radius:3px;overflow:hidden
}
.md-section-label{
  font-size:.58rem;font-weight:700;color:var(--text3);
  letter-spacing:.12em;text-transform:uppercase;
  padding:.55rem .8rem .25rem;background:var(--bg2)
}
.md-option{
  display:flex;align-items:center;justify-content:space-between;
  padding:.5rem .8rem;cursor:pointer;transition:background .1s;gap:.5rem;
  border-top:1px solid var(--border)
}
.md-option:hover{background:var(--bg2)}
.md-option.selected{background:var(--bg3);border-left:2px solid var(--amber)}
.md-option.unavail{opacity:.35;cursor:not-allowed}
.md-opt-name{font-size:.72rem;color:var(--text)}
.md-opt-sub{font-size:.6rem;color:var(--text3);margin-top:.1rem}
.md-badges{display:flex;gap:.25rem;flex-shrink:0}
.mdbadge{font-size:.58rem;padding:.1rem .35rem;border-radius:2px;font-weight:600;letter-spacing:.04em}
.mdb-local{background:#0d2040;color:var(--blue)}
.mdb-cloud{background:var(--amber-dim);color:var(--amber)}
.mdb-fast{background:#0a2010;color:var(--green)}
.mdb-slow{background:#200e00;color:#fb923c}
.mdb-free{background:#0a2010;color:var(--green)}
.mdb-paid{background:#200e00;color:#fb923c}

/* ── Scrollbars global ── */
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:99px}

@media(max-width:700px){
  .thread-list{display:none}
  .mem-sidebar{display:none}
  .cmdbar-logo-sub{display:none}
}

/* ══════════════════════════════════════
   KNOWLEDGE GRAPH PANEL
══════════════════════════════════════ */
.graph-wrap{display:flex;flex:1;overflow:hidden}
.graph-sidebar{
  width:260px;flex-shrink:0;
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  background:var(--bg1);
  overflow-y:auto
}
.graph-controls{padding:.8rem}
.graph-selection{
  flex:1;padding:.8rem;
  border-top:1px solid var(--border);
  overflow-y:auto
}
.graph-main{flex:1;display:flex;flex-direction:column;position:relative}
#graph-viz{flex:1;background:var(--bg);cursor:grab}
#graph-viz:active{cursor:grabbing}
.graph-toolbar{
  position:absolute;bottom:1rem;left:50%;transform:translateX(-50%);
  display:flex;gap:.5rem;
  background:var(--bg2);border:1px solid var(--border);
  padding:.4rem;border-radius:4px
}
.graph-toolbar button{
  background:none;border:1px solid var(--border2);
  color:var(--text3);font-family:var(--font);font-size:.6rem;
  padding:.3rem .6rem;cursor:pointer;border-radius:2px
}
.graph-toolbar button:hover{border-color:var(--amber);color:var(--amber)}
.vault-toggles{display:flex;flex-direction:column;gap:.3rem}
.vault-toggle{
  display:flex;align-items:center;gap:.5rem;
  font-size:.65rem;color:var(--text2);
  cursor:pointer;padding:.3rem;border-radius:2px
}
.vault-toggle:hover{background:var(--bg2)}
.vault-toggle input{margin:0}
.vault-dot{width:8px;height:8px;border-radius:50%}
.vault-personal{background:#2196F3}
.vault-youtube{background:#F44336}
.vault-wiki{background:#4CAF50}
.vault-projects{background:#FF9800}
.vault-inbox{background:#9E9E9E}
.graph-search-input{
  width:100%;background:var(--bg);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:.7rem;
  padding:.4rem;border-radius:2px;margin-bottom:.4rem
}
.graph-stats{font-size:.6rem;color:var(--text3)}
.graph-stats-row{display:flex;justify-content:space-between;padding:.2rem 0}
.node-circle{stroke:var(--bg);stroke-width:1.5px;cursor:pointer;transition:all .2s}
.node-circle:hover{stroke:var(--amber);stroke-width:3px}
.node-label{font-size:10px;fill:var(--text);pointer-events:none}
.link-line{stroke:var(--border2);stroke-opacity:.6;stroke-width:1px}
.link-line.highlight{stroke:var(--amber);stroke-opacity:1;stroke-width:2px}
.node-circle.dim{opacity:.2}
.node-circle.highlight{opacity:1;stroke:var(--amber);stroke-width:3px}

</style>
</head>
<body>

<!-- Top command bar -->
<header class="cmdbar">
  <div class="cmdbar-logo">
    <div class="cmdbar-logo-mark">HM</div>
    <div>
      <div class="cmdbar-logo-text">Heimdall</div>
      <div class="cmdbar-logo-sub">PA / v0.1</div>
    </div>
  </div>
  <nav class="cmdbar-nav">
    <div class="nav-tab active" id="nav-chat" onclick="switchTab('chat')">
      <span class="nav-tab-icon">_</span> Chat
    </div>
    <div class="nav-tab" id="nav-memory" onclick="switchTab('memory')">
      <span class="nav-tab-icon">#</span> Memory
    </div>
    <div class="nav-tab" id="nav-system" onclick="switchTab('system')">
      <span class="nav-tab-icon">@</span> System
    </div>
    <div class="nav-tab" id="nav-roadmap" onclick="switchTab('roadmap')">
      <span class="nav-tab-icon">~</span> Roadmap
    </div>
    <div class="nav-tab" id="nav-graph" onclick="switchTab('graph')">
      <span class="nav-tab-icon">◈</span> Graph
    </div>
  </nav>
  <div class="cmdbar-right">
    <div id="svc-postgres" style="display:flex;align-items:center;gap:.3rem">
      <span class="status-dot warn" id="dot-postgres"></span>
      <span class="status-label">postgres</span>
    </div>
    <div id="svc-ollama" style="display:flex;align-items:center;gap:.3rem;margin-left:.4rem">
      <span class="status-dot warn" id="dot-ollama"></span>
      <span class="status-label">ollama</span>
    </div>
    <button class="model-btn" onclick="morningBrief()" id="brief-btn" style="margin-left:.6rem;border-color:var(--amber);color:var(--amber)">
      ☀️ Brief
    </button>
    <div class="model-picker-wrap" style="margin-left:.4rem">
      <button class="model-btn" onclick="toggleModelPicker()" id="model-btn">
        <span id="model-label">loading…</span>
        <span class="chevron">▼</span>
      </button>
      <div class="model-dropdown" id="model-dropdown" style="display:none">
        <div id="md-local"></div>
        <div id="md-cloud"></div>
      </div>
    </div>
  </div>
</header>

<!-- Main layout -->
<div class="layout">

  <!-- ── CHAT ── -->
  <div class="panel active" id="panel-chat">
    <div class="chat-wrap">
      <div class="thread-list">
        <div class="thread-header">
          <span>Threads</span>
          <button class="new-thread-btn" onclick="newThread()">+ new</button>
        </div>
        <div class="thread-items" id="thread-items">
          <div class="thread-item active" data-tid="0">
            <div class="thread-item-title">New thread</div>
            <div class="thread-item-meta">now</div>
          </div>
        </div>
      </div>
      <div class="chat-main">
        <div id="brief-bar" style="display:none;border-bottom:1px solid var(--border);background:var(--bg1);padding:.6rem 1.5rem;animation:msg-in .3s ease">
          <div id="brief-content" style="font-size:.78rem;line-height:1.7;color:var(--text)"></div>
        </div>
        <div class="chat-messages" id="chat-messages">
          <div class="msg assistant">
            <div class="msg-avatar">HM</div>
            <div class="msg-body">
              <div class="msg-bubble"><span class="md-content">Heimdall online. How can I assist?</span></div>
              <div class="msg-meta">heimdall &middot; ready</div>
            </div>
          </div>
        </div>
        <div class="chat-input-area">
          <div class="chat-input-meta">
            <label class="memory-toggle">
              <input type="checkbox" id="store-toggle"> save to memory
            </label>
            <span class="char-counter" id="char-counter">0</span>
          </div>
          <div class="chat-input-row">
            <textarea id="chat-input" rows="1" placeholder="> enter message…"></textarea>
            <button class="send-btn" id="send-btn" onclick="sendChat()">Send</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── MEMORY ── -->
  <div class="panel" id="panel-memory">
    <div class="memory-wrap">
      <div class="mem-sidebar">
        <div class="mem-sidebar-section">
          <div class="mem-mode-tabs">
            <button class="mem-mode-tab active" id="mode-browse-btn" onclick="setMemMode('browse')">Browse</button>
            <button class="mem-mode-tab" id="mode-search-btn" onclick="setMemMode('search')">Search</button>
            <button class="mem-mode-tab" id="mode-store-btn" onclick="setMemMode('store')">Store</button>
          </div>
        </div>
        <div class="mem-sidebar-section" id="mode-browse">
          <div class="sec-label">Tables</div>
          <div id="browse-table-list"></div>
          <button class="mem-action-btn" style="margin-top:.5rem" onclick="browseTable(browseActiveTable)">Refresh ↻</button>
        </div>
        <div class="mem-sidebar-section" id="mode-search" style="display:none">
          <div class="sec-label">Semantic Search</div>
          <input class="mem-search-input" id="mem-query" placeholder="semantic query…" onkeydown="if(event.key==='Enter')searchMemory()">
          <div class="table-pills" id="table-pills" style="margin-top:.4rem">
            <button class="table-pill active" data-table="__all__" onclick="setTable(this,'__all__')">all</button>
            <button class="table-pill" data-table="vector_memory" onclick="setTable(this,'vector_memory')">memory</button>
            <button class="table-pill" data-table="vector_notes" onclick="setTable(this,'vector_notes')">notes</button>
            <button class="table-pill" data-table="vector_chat_summaries" onclick="setTable(this,'vector_chat_summaries')">summaries</button>
            <button class="table-pill" data-table="vector_code_chunks" onclick="setTable(this,'vector_code_chunks')">code</button>
          </div>
          <button class="mem-action-btn" onclick="searchMemory()">Search →</button>
        </div>
        <div class="mem-sidebar-section" id="mode-store" style="display:none;flex:1;overflow-y:auto">
          <div class="sec-label">Embed &amp; Store</div>
          <div class="store-form-fields">
            <textarea class="store-textarea" id="store-text" placeholder="text to embed…" rows="4"></textarea>
            <div class="store-row">
              <select class="store-mini-select" id="store-table">
                <option value="vector_memory">memory</option>
                <option value="vector_notes">notes</option>
                <option value="vector_chat_summaries">summaries</option>
                <option value="vector_code_chunks">code</option>
              </select>
              <input class="store-mini-input" id="store-type" value="fact" placeholder="type">
            </div>
            <input class="store-mini-input" id="store-path" placeholder="source path (optional)" style="width:100%">
            <button class="mem-action-btn" onclick="storeMemory()">Store →</button>
            <div id="store-msg"></div>
          </div>
        </div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
        <div id="mem-browse-header" style="border-bottom:1px solid var(--border);background:var(--bg1);padding:.5rem 1rem;display:flex;align-items:center;gap:.6rem;flex-shrink:0">
          <span id="mem-browse-title" style="font-size:.65rem;font-weight:600;color:var(--text3);letter-spacing:.1em;text-transform:uppercase">vector_memory</span>
          <span id="mem-browse-count" style="font-size:.6rem;color:var(--text3);background:var(--bg3);border:1px solid var(--border2);padding:.1rem .4rem;border-radius:2px"></span>
          <div style="margin-left:auto;display:flex;gap:.4rem;align-items:center">
            <button class="refresh-btn" onclick="browsePage(-1)">← prev</button>
            <span id="mem-page-label" style="font-size:.6rem;color:var(--text3)"></span>
            <button class="refresh-btn" onclick="browsePage(1)">next →</button>
          </div>
        </div>
        <div class="mem-main" id="mem-results">
          <div class="mem-empty">// loading…</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── SYSTEM ── -->
  <div class="panel" id="panel-system">
    <div class="sys-wrap" id="sys-wrap">
      <div class="sys-card" style="grid-column:1/-1;display:flex;align-items:center;justify-content:space-between">
        <span style="font-size:.65rem;color:var(--text3);letter-spacing:.1em">SYSTEM HEALTH</span>
        <button class="refresh-btn" onclick="loadSystem()">↻ refresh</button>
      </div>
    </div>
  </div>

  <!-- ── ROADMAP ── -->
  <div class="panel" id="panel-roadmap">
    <div class="road-wrap" id="road-wrap">
      <!-- Populated by JS -->
    </div>
  </div>

  <!-- ── KNOWLEDGE GRAPH ── -->
  <div class="panel" id="panel-graph">
    <div class="graph-wrap">
      <div class="graph-sidebar">
        <div class="graph-controls">
          <div class="sec-label">Vaults</div>
          <div id="graph-vault-filters" class="vault-toggles">
            <!-- Populated by JS -->
          </div>
          <div class="sec-label" style="margin-top:1rem">Search</div>
          <input type="text" id="graph-search" class="graph-search-input" placeholder="Find note..." onkeydown="if(event.key==='Enter')searchGraph()">
          <button class="mem-action-btn" onclick="searchGraph()">Find →</button>
          <div class="sec-label" style="margin-top:1rem">Stats</div>
          <div id="graph-stats" class="graph-stats">
            <!-- Populated by JS -->
          </div>
        </div>
        <div class="graph-selection" id="graph-selection" style="display:none">
          <div class="sec-label">Selected</div>
          <div id="selected-node-info"></div>
          <div class="sec-label" style="margin-top:.8rem">Connected</div>
          <div id="connected-nodes"></div>
        </div>
      </div>
      <div class="graph-main">
        <div id="graph-viz"></div>
        <div class="graph-toolbar">
          <button onclick="resetGraphZoom()" title="Reset view">⌖ Reset</button>
          <button onclick="toggleBacklinks()" title="Toggle backlinks">⇄ Links</button>
          <button onclick="reindexGraph()" title="Reindex vault">↻ Reindex</button>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
const API = '';
let chatHistory = [];
let selectedModel = 'groq-llama4-scout';
let selectedTable = '__all__';
let threadCounter = 0;
const threads = { 0: { title: 'New thread', messages: [] } };

// ── Tab switching ──
function switchTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
  if (name === 'system') loadSystem();
  if (name === 'roadmap') renderRoadmap();
  if (name === 'graph') initGraph();
}

// ── Model picker ──
function toggleModelPicker() {
  const dd = document.getElementById('model-dropdown');
  dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', e => {
  if (!e.target.closest('.model-picker-wrap')) {
    const dd = document.getElementById('model-dropdown');
    if (dd) dd.style.display = 'none';
  }
});
function selectModel(id, label) {
  selectedModel = id;
  document.getElementById('model-label').textContent = id;
  document.getElementById('model-dropdown').style.display = 'none';
  document.querySelectorAll('.md-option').forEach(el => {
    el.classList.toggle('selected', el.dataset.id === id);
  });
}

async function loadModelOptions() {
  try {
    const r = await fetch(API + '/models');
    const data = await r.json();
    const spd = s => s === 'fast' ? '<span class="mdbadge mdb-fast">fast</span>' : '<span class="mdbadge mdb-slow">slow</span>';
    const cst = c => c === 'free' ? '<span class="mdbadge mdb-free">free</span>' : '<span class="mdbadge mdb-paid">' + c + '</span>';

    const localEl = document.getElementById('md-local');
    if (data.local && data.local.length) {
      localEl.innerHTML = '<div class="md-section-label">Local — Ollama</div>' +
        data.local.map(m =>
          '<div class="md-option" data-id="' + m.id + '" data-name="' + m.name + '" data-avail="true">' +
          '<div><div class="md-opt-name">' + m.name + '</div></div>' +
          '<div class="md-badges"><span class="mdbadge mdb-local">local</span>' + spd(m.speed) + cst(m.cost) + '</div></div>'
        ).join('');
      localEl.addEventListener('click', e => {
        const opt = e.target.closest('.md-option');
        if (opt) selectModel(opt.dataset.id, opt.dataset.name);
      });
    }

    const cloudEl = document.getElementById('md-cloud');
    if (data.cloud && data.cloud.length) {
      cloudEl.innerHTML = '<div class="md-section-label">Cloud</div>' +
        data.cloud.map(m =>
          '<div class="md-option' + (!m.available ? ' unavail' : '') + (m.id === selectedModel ? ' selected' : '') +
          '" data-id="' + m.id + '" data-name="' + m.name + '" data-avail="' + m.available + '">' +
          '<div><div class="md-opt-name">' + m.name + '</div>' +
          (!m.available ? '<div class="md-opt-sub">api key not set</div>' : '') + '</div>' +
          '<div class="md-badges"><span class="mdbadge mdb-cloud">' + m.provider + '</span>' + spd(m.speed) + cst(m.cost) + '</div></div>'
        ).join('');
      cloudEl.addEventListener('click', e => {
        const opt = e.target.closest('.md-option');
        if (opt && opt.dataset.avail === 'true') selectModel(opt.dataset.id, opt.dataset.name);
      });
    }

    // auto-select first available cloud, else first local
    const firstCloud = data.cloud?.find(m => m.available);
    const firstLocal = data.local?.[0];
    const pick = firstCloud || firstLocal;
    if (pick) selectModel(pick.id, pick.id);
  } catch(e) { console.error(e); }
}

// ── Status dots ──
async function loadStatus() {
  try {
    const r = await fetch(API + '/health');
    const d = await r.json();
    const set = (svc, info) => {
      const dot = document.getElementById('dot-' + svc);
      if (dot) dot.className = 'status-dot ' + (info.status === 'ok' ? 'ok' : 'err');
    };
    Object.entries(d.services || {}).forEach(([k, v]) => set(k, v));
  } catch {}
}

// ── Threads ──
function newThread() {
  threadCounter++;
  threads[threadCounter] = { title: 'Thread ' + threadCounter, messages: [] };
  const items = document.getElementById('thread-items');
  const div = document.createElement('div');
  div.className = 'thread-item';
  div.dataset.tid = threadCounter;
  div.innerHTML = '<div class="thread-item-title">Thread ' + threadCounter + '</div><div class="thread-item-meta">now</div>';
  div.onclick = () => switchThread(threadCounter);
  items.appendChild(div);
  switchThread(threadCounter);
}
function switchThread(tid) {
  chatHistory = threads[tid]?.messages || [];
  document.querySelectorAll('.thread-item').forEach(el => {
    el.classList.toggle('active', el.dataset.tid == tid);
  });
  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML = chatHistory.length
    ? chatHistory.filter(m => m.role !== 'system').map(m =>
        '<div class="msg ' + m.role + '">' +
        '<div class="msg-avatar">' + (m.role === 'user' ? 'U' : 'HM') + '</div>' +
        '<div class="msg-body"><div class="msg-bubble">' +
        (m.role === 'assistant' ? '<span class="md-content">' + (typeof marked !== 'undefined' ? marked.parse(m.content) : esc(m.content)) + '</span>'
          : esc(m.content)) +
        '</div></div></div>'
      ).join('')
    : '<div class="msg assistant"><div class="msg-avatar">HM</div><div class="msg-body"><div class="msg-bubble"><span class="md-content">Heimdall online. How can I assist?</span></div><div class="msg-meta">heimdall &middot; ready</div></div></div>';
}

// ── Chat ──
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.getElementById('chat-input').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 130) + 'px';
  document.getElementById('char-counter').textContent = this.value.length;
});
document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

function appendThinking() {
  const wrap = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'thinking-wrap';
  div.id = 'thinking';
  div.innerHTML = '<div class="msg-avatar" style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;color:var(--amber);background:var(--amber-dim);border:1px solid var(--border2)">HM</div>' +
    '<div class="thinking-bubble"><div class="thinking-dots"><span></span><span></span><span></span></div> processing</div>';
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
}
function removeThinking() { document.getElementById('thinking')?.remove(); }

async function sendChat() {
  const input = document.getElementById('chat-input');
  const btn = document.getElementById('send-btn');
  const msg = input.value.trim();
  if (!msg) return;
  const model = selectedModel;
  const saveToMem = document.getElementById('store-toggle').checked;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('char-counter').textContent = '0';
  btn.disabled = true;

  // User bubble
  const wrap = document.getElementById('chat-messages');
  const userDiv = document.createElement('div');
  userDiv.className = 'msg user';
  userDiv.innerHTML = '<div class="msg-avatar">U</div><div class="msg-body"><div class="msg-bubble">' + esc(msg) + '</div><div class="msg-meta">you &middot; now</div></div>';
  wrap.appendChild(userDiv);
  chatHistory.push({ role: 'user', content: msg });
  appendThinking();
  wrap.scrollTop = wrap.scrollHeight;

  try {
    const res = await fetch(API + '/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(-12), model, store_in_memory: saveToMem })
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'error');
    removeThinking();

    // Streaming bubble
    const aDiv = document.createElement('div');
    aDiv.className = 'msg assistant';
    aDiv.innerHTML = '<div class="msg-avatar">HM</div><div class="msg-body"><div class="msg-bubble" id="sbubble"><span class="md-content" id="scontent"></span></div><div class="msg-meta" id="smeta">streaming…</div></div>';
    wrap.appendChild(aDiv);
    wrap.scrollTop = wrap.scrollHeight;

    const contentEl = document.getElementById('scontent');
    const metaEl = document.getElementById('smeta');
    let full = '', ctx = [], usedModel = model;

    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split(String.fromCharCode(10));
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const ev = JSON.parse(line.slice(6));
          if (ev.type === 'context') { ctx = ev.data; }
          else if (ev.type === 'token') {
            full += ev.data;
            contentEl.innerHTML = typeof marked !== 'undefined' ? marked.parse(full) : esc(full);
            wrap.scrollTop = wrap.scrollHeight;
          } else if (ev.type === 'done') { usedModel = ev.model; }
          else if (ev.type === 'error') { throw new Error(ev.data); }
        } catch { continue; }
      }
    }

    aDiv.querySelector('#sbubble').removeAttribute('id');
    contentEl.removeAttribute('id');
    metaEl.removeAttribute('id');
    metaEl.textContent = usedModel + ' · now';

    if (ctx.length) {
      const pills = document.createElement('div');
      pills.className = 'ctx-pills';
      pills.innerHTML = ctx.map(c => '<span class="ctx-pill">📎 ' + esc(c.text.slice(0, 45)) + (c.text.length > 45 ? '…' : '') + '</span>').join('');
      metaEl.before(pills);
    }

    chatHistory.push({ role: 'assistant', content: full });

    // Update thread title from first message
    const tid = document.querySelector('.thread-item.active')?.dataset?.tid;
    if (tid !== undefined && threads[tid]) {
      threads[tid].messages = chatHistory;
      if (msg.length > 0) {
        const titleEl = document.querySelector('.thread-item.active .thread-item-title');
        if (titleEl && titleEl.textContent === 'New thread' || titleEl?.textContent?.startsWith('Thread')) {
          titleEl.textContent = msg.slice(0, 28) + (msg.length > 28 ? '…' : '');
        }
      }
    }

  } catch(e) {
    removeThinking();
    const errDiv = document.createElement('div');
    errDiv.className = 'msg assistant';
    errDiv.innerHTML = '<div class="msg-avatar">HM</div><div class="msg-body"><div class="msg-bubble" style="color:var(--red)">Error: ' + esc(e.message) + '</div></div>';
    wrap.appendChild(errDiv);
  }
  btn.disabled = false;
  input.focus();
}

// ── Memory ──
let browseActiveTable = 'vector_memory';
let browsePage_ = 0;
const browsePageSize = 20;
let memMode = 'browse';

function setMemMode(mode) {
  memMode = mode;
  ['browse','search','store'].forEach(m => {
    document.getElementById('mode-' + m).style.display = m === mode ? '' : 'none';
    document.getElementById('mode-' + m + '-btn').classList.toggle('active', m === mode);
  });
  const header = document.getElementById('mem-browse-header');
  if (mode === 'browse') {
    header.style.display = 'flex';
    browseTable(browseActiveTable);
  } else {
    header.style.display = 'none';
    document.getElementById('mem-results').innerHTML = '<div class="mem-empty">// ' + (mode === 'search' ? 'enter a query and search' : 'fill in the form to embed & store') + '</div>';
  }
}

async function loadBrowseCounts() {
  try {
    const r = await fetch(API + '/memory/counts');
    const data = await r.json();
    const tables = ['vector_memory','vector_notes','vector_chat_summaries','vector_code_chunks'];
    const labels = {'vector_memory':'memory','vector_notes':'notes','vector_chat_summaries':'summaries','vector_code_chunks':'code'};
    const listEl = document.getElementById('browse-table-list');
    listEl.innerHTML = tables.map(t =>
      '<div class="browse-table-row' + (t === browseActiveTable ? ' active' : '') + '" data-t="' + t + '">' +
      '<span class="browse-table-name">' + labels[t] + '</span>' +
      '<span class="browse-table-count">' + (data[t] || 0) + '</span></div>'
    ).join('');
    listEl.querySelectorAll('.browse-table-row').forEach(el => {
      el.addEventListener('click', () => browseTable(el.dataset.t));
    });
  } catch {}
}

async function browseTable(table) {
  browseActiveTable = table;
  browsePage_ = 0;
  document.querySelectorAll('.browse-table-row').forEach(el => {
    el.classList.toggle('active', el.dataset.t === table);
  });
  await renderBrowsePage();
}

async function browsePage(dir) {
  browsePage_ = Math.max(0, browsePage_ + dir);
  await renderBrowsePage();
}

async function renderBrowsePage() {
  const container = document.getElementById('mem-results');
  const offset = browsePage_ * browsePageSize;
  document.getElementById('mem-browse-title').textContent = browseActiveTable;
  document.getElementById('mem-page-label').textContent = 'p.' + (browsePage_ + 1);
  container.innerHTML = '<div class="mem-empty">// loading…</div>';
  try {
    const r = await fetch(API + '/memory/browse?table=' + browseActiveTable + '&limit=' + browsePageSize + '&offset=' + offset);
    const data = await r.json();
    if (!data.length) {
      container.innerHTML = '<div class="mem-empty">// ' + (offset === 0 ? 'no entries in this table' : 'no more entries') + '</div>';
      if (offset > 0) { browsePage_--; }
      return;
    }
    // also fetch count for badge
    fetch(API + '/memory/counts').then(r2 => r2.json()).then(counts => {
      document.getElementById('mem-browse-count').textContent = (counts[browseActiveTable] || '?') + ' entries';
    }).catch(() => {});

    container.innerHTML = data.map(row =>
      '<div class="mem-card">' +
        '<div class="mem-card-id">' + row.id.slice(0,8) + '…' + '</div>' +
        '<div class="mem-card-text">' + esc(row.text) + '</div>' +
        '<div class="mem-card-footer">' +
          '<span class="mem-tag tag-type">' + esc(row.source_type) + '</span>' +
          (row.source_path ? '<span class="mem-card-path">' + esc(row.source_path) + '</span>' : '') +
        '</div>' +
      '</div>'
    ).join('');
  } catch(e) {
    container.innerHTML = '<div class="mem-empty">// error: ' + esc(e.message) + '</div>';
  }
}

function setTable(el, table) {
  selectedTable = table;
  document.querySelectorAll('.table-pill').forEach(p => p.classList.toggle('active', p.dataset.table === table));
}

function simCol(d) {
  if (d < 0.35) return 'var(--green)';
  if (d < 0.55) return 'var(--amber)';
  return 'var(--red)';
}

async function searchMemory() {
  const q = document.getElementById('mem-query').value.trim();
  if (!q) return;
  const container = document.getElementById('mem-results');
  container.innerHTML = '<div class="mem-empty">// searching…</div>';
  try {
    const r = await fetch(API + '/memory/search?q=' + encodeURIComponent(q) + '&table=' + selectedTable + '&limit=10');
    const data = await r.json();
    if (!data.length) { container.innerHTML = '<div class="mem-empty">// no results</div>'; return; }
    container.innerHTML = data.map(res => {
      const pct = Math.max(0, Math.min(100, Math.round((1 - res.distance) * 100)));
      const col = simCol(res.distance);
      return '<div class="mem-card">' +
        '<div class="mem-card-text">' + esc(res.text) + '</div>' +
        '<div class="mem-card-footer">' +
          '<span class="mem-tag tag-type">' + esc(res.source_type) + '</span>' +
          (res.table ? '<span class="mem-tag tag-table">' + esc(res.table) + '</span>' : '') +
          '<div class="sim-wrap">' +
            '<span class="sim-pct">' + pct + '%</span>' +
            '<div class="sim-bar"><div class="sim-fill" style="width:' + pct + '%;background:' + col + '"></div></div>' +
          '</div>' +
        '</div></div>';
    }).join('');
  } catch(e) {
    container.innerHTML = '<div class="mem-empty">// error: ' + esc(e.message) + '</div>';
  }
}
async function storeMemory() {
  const text = document.getElementById('store-text').value.trim();
  if (!text) return;
  const msgEl = document.getElementById('store-msg');
  msgEl.innerHTML = '<div class="alert-msg" style="color:var(--text3)">embedding…</div>';
  try {
    const r = await fetch(API + '/memory/store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        table: document.getElementById('store-table').value,
        source_type: document.getElementById('store-type').value || 'fact',
        source_path: document.getElementById('store-path').value
      })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail);
    msgEl.innerHTML = '<div class="alert-msg alert-ok">stored — ' + d.id.slice(0, 8) + '…</div>';
    document.getElementById('store-text').value = '';
    loadStatus();
  } catch(e) {
    msgEl.innerHTML = '<div class="alert-msg alert-err">error: ' + esc(e.message) + '</div>';
  }
}

// ── System ──
async function loadSystem() {
  const wrap = document.getElementById('sys-wrap');
  try {
    const [healthRes, modelRes] = await Promise.all([
      fetch(API + '/health'),
      fetch(API + '/models')
    ]);
    const health = await healthRes.json();
    const models = await modelRes.json();

    let html = '<div class="sys-card" style="grid-column:1/-1;display:flex;align-items:center;justify-content:space-between"><span style="font-size:.65rem;color:var(--text3);letter-spacing:.1em">SYSTEM HEALTH</span><button class="refresh-btn" onclick="loadSystem()">↻ refresh</button></div>';

    // Service cards
    for (const [svc, info] of Object.entries(health.services || {})) {
      const ok = info.status === 'ok';
      const detail = info.detail || (info.models ? 'Models: ' + info.models.join(', ') : '');
      html += '<div class="sys-card">' +
        '<div class="sys-card-head"><span class="sys-card-title">' + svc + '</span>' +
        '<span class="sys-badge ' + (ok ? 'badge-ok' : 'badge-err') + '">' + (ok ? 'OK' : 'ERR') + '</span></div>' +
        '<div class="sys-detail">' + esc(detail) + '</div></div>';
    }

    // Models card
    const allModels = [...(models.local || []), ...(models.cloud || []).filter(m => m.available)];
    html += '<div class="sys-card full"><div class="sys-card-head"><span class="sys-card-title">Available Models</span><span class="sys-badge badge-ok">' + allModels.length + ' active</span></div>' +
      '<div class="model-list">' +
      allModels.map(m => '<div class="model-row"><span class="model-row-name">' + m.name + '</span>' +
        '<span class="model-row-provider">' + m.provider + '</span>' +
        '<span class="sys-badge ' + (m.speed === 'fast' ? 'badge-ok' : 'badge-warn') + '">' + m.speed + '</span>' +
        '<span class="sys-badge">' + m.cost + '</span></div>'
      ).join('') +
      '</div></div>';

    wrap.innerHTML = html;
  } catch(e) {
    wrap.innerHTML += '<div class="sys-card full"><div class="sys-detail" style="color:var(--red)">Failed to load: ' + esc(e.message) + '</div></div>';
  }
}

// ── Roadmap ──
const ROADMAP = [
  { phase: 'Phase 1A — Foundation', status: 'done', items: [
    { done: true, text: 'Ubuntu 26.04 LTS installed, SSH working' },
    { done: true, text: 'Docker Compose — Postgres, Ollama, Redis, Langfuse' },
    { done: true, text: 'pgvector extension enabled, 4 vector tables created' },
    { done: true, text: 'nomic-embed-text embeddings via Ollama' },
    { done: true, text: 'atlas/db/vector_store.py — store, search, search_all' },
    { done: true, text: 'VECTOR-SEARCH.md documentation written' },
  ]},
  { phase: 'Phase 1B — Core Services', status: 'done', items: [
    { done: true, text: 'PostgreSQL + pgvector running' },
    { done: true, text: 'Ollama running with qwen3:1.7b, qwen3:8b, nomic-embed-text' },
    { done: true, text: 'Redis running' },
    { done: true, text: 'Langfuse deployed (restarting — non-blocking)' },
  ]},
  { phase: 'Phase 1C — Heimdall API', status: 'done', items: [
    { done: true, text: 'FastAPI app — main.py with CORS, startup hooks' },
    { done: true, text: 'POST /chat — memory context injection, multi-provider routing' },
    { done: true, text: 'POST /chat/stream — SSE streaming endpoint' },
    { done: true, text: 'GET /memory/search, POST /memory/store' },
    { done: true, text: 'GET /health — Postgres + Ollama status' },
    { done: true, text: 'GET /models — local + cloud model list' },
    { done: true, text: 'DeepSeek V3 Flash/Pro integration' },
    { done: true, text: 'Groq Llama 4 Scout, Llama 3 70B/8B integration' },
    { done: true, text: 'Tailscale — remote access at 100.113.79.103' },
    { done: true, text: 'Dashboard — chat, memory, system, roadmap panels' },
    { done: true, text: 'Streaming token rendering with marked.js MD' },
  ]},
  { phase: 'Phase 2A — Agent Core', status: 'todo', items: [
    { done: false, text: 'atlas/core/embeddings.py — reusable embedding wrapper' },
    { done: false, text: 'Capability planner — routes requests to correct sub-agents/models' },
    { done: false, text: 'Task queue — async task dispatch with status tracking' },
    { done: false, text: 'Memory consolidation — auto-summarise old chat to vector_chat_summaries' },
  ]},
  { phase: 'Phase 2B — Tools & Integrations', status: 'todo', items: [
    { done: false, text: 'Paperless-ngx — document OCR container' },
    { done: false, text: 'VSCode connector — file ops, terminal, Git via API' },
    { done: false, text: 'Google Calendar / Maps tool integration' },
    { done: false, text: 'Garmin / Apple Health data ingestion' },
    { done: false, text: 'Obsidian Vault sync' },
    { done: false, text: 'n8n workflow automation' },
  ]},
  { phase: 'Phase 3 — Voice & GPU', status: 'todo', items: [
    { done: false, text: 'Wake word detection (Porcupine / openWakeWord)' },
    { done: false, text: 'Whisper STT integration' },
    { done: false, text: 'TTS pipeline (Coqui / Piper)' },
    { done: false, text: 'GPU install (RTX 3090 planned) — ~80 tok/s local inference' },
    { done: false, text: 'Next.js dashboard rebuild with SSR' },
  ]},
];

function renderRoadmap() {
  const wrap = document.getElementById('road-wrap');
  const statusBadge = s => {
    if (s === 'done') return '<span class="phase-status phase-done">COMPLETE</span>';
    if (s === 'wip') return '<span class="phase-status phase-wip">IN PROGRESS</span>';
    return '<span class="phase-status phase-todo">PLANNED</span>';
  };
  wrap.innerHTML = ROADMAP.map(phase =>
    '<div class="road-phase">' +
    '<div class="road-phase-title">' + esc(phase.phase) + statusBadge(phase.status) + '</div>' +
    phase.items.map(item =>
      '<div class="road-item' + (item.done ? ' done-item' : '') + '">' +
      '<div class="road-check ' + (item.done ? 'done' : 'todo') + '">' + (item.done ? '✓' : '') + '</div>' +
      '<div class="road-item-text">' + esc(item.text) + '</div></div>'
    ).join('') +
    '</div>'
  ).join('');
}

// ── Morning Brief ──
async function morningBrief() {
  const btn = document.getElementById('brief-btn');
  const bar = document.getElementById('brief-bar');
  const content = document.getElementById('brief-content');
  btn.textContent = '⏳ loading…';
  btn.disabled = true;
  bar.style.display = 'block';
  content.innerHTML = '<span style="color:var(--text3)">Generating your morning brief…</span>';
  switchTab('chat');
  try {
    const r = await fetch(API + '/brief');
    const d = await r.json();
    content.innerHTML = typeof marked !== 'undefined' ? marked.parse(d.brief) : esc(d.brief);
  } catch(e) {
    content.innerHTML = '<span style="color:var(--red)">Brief failed: ' + esc(e.message) + '</span>';
  }
  btn.textContent = '☀️ Brief';
  btn.disabled = false;
}

// ── Knowledge Graph ──
let graphData = { nodes: [], links: [] };
let graphSimulation = null;
let selectedNode = null;
let showBacklinks = true;

const VAULT_COLORS = {
  personal: '#2196F3',
  youtube: '#F44336',
  wiki: '#4CAF50',
  projects: '#FF9800',
  inbox: '#9E9E9E'
};

async function initGraph() {
  if (graphData.nodes.length === 0) {
    await loadGraphData();
    renderVaultFilters();
    renderGraphStats();
  }
  if (!graphSimulation) {
    initGraphViz();
  }
}

async function loadGraphData() {
  try {
    const [nodesRes, edgesRes] = await Promise.all([
      fetch(API + '/graph/nodes?limit=2000'),
      fetch(API + '/graph/edges?limit=5000&include_backlinks=' + showBacklinks)
    ]);
    const nodes = await nodesRes.json();
    const edges = await edgesRes.json();
    graphData = { nodes, links: edges };
  } catch (e) {
    console.error('Failed to load graph:', e);
    graphData = { nodes: [], links: [] };
  }
}

function renderVaultFilters() {
  const vaults = [...new Set(graphData.nodes.map(n => n.vault))];
  const container = document.getElementById('graph-vault-filters');
  container.innerHTML = vaults.map(v => `
    <label class="vault-toggle">
      <input type="checkbox" checked data-vault="${v}" onchange="filterGraph()">
      <span class="vault-dot vault-${v}"></span>
      <span>${v}</span>
    </label>
  `).join('');
}

async function renderGraphStats() {
  try {
    const res = await fetch(API + '/graph/stats');
    const stats = await res.json();
    const container = document.getElementById('graph-stats');
    container.innerHTML = `
      <div class="graph-stats-row"><span>Notes:</span><span>${stats.total_notes}</span></div>
      <div class="graph-stats-row"><span>Links:</span><span>${stats.total_links}</span></div>
      <div class="graph-stats-row"><span>Isolated:</span><span>${stats.isolated_nodes}</span></div>
    `;
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

function initGraphViz() {
  const container = document.getElementById('graph-viz');
  const width = container.clientWidth;
  const height = container.clientHeight;
  
  // Clear existing
  container.innerHTML = '';
  
  // Create SVG
  const svg = d3.select('#graph-viz')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]);
  
  // Add zoom behavior
  const g = svg.append('g');
  
  svg.call(d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    }));
  
  // Get active vaults
  const activeVaults = [...document.querySelectorAll('#graph-vault-filters input:checked')]
    .map(cb => cb.dataset.vault);
  
  // Filter data
  const filteredNodes = graphData.nodes.filter(n => activeVaults.includes(n.vault));
  const nodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredLinks = graphData.links.filter(l => 
    nodeIds.has(l.source) && nodeIds.has(l.target)
  );
  
  // Scales
  const sizeScale = d3.scaleLinear()
    .domain([0, d3.max(filteredNodes, d => d.connection_count) || 1])
    .range([6, 20]);
  
  // Simulation
  graphSimulation = d3.forceSimulation(filteredNodes)
    .force('link', d3.forceLink(filteredLinks).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => sizeScale(d.connection_count) + 5));
  
  // Links
  const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(filteredLinks)
    .enter().append('line')
    .attr('class', 'link-line');
  
  // Nodes
  const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(filteredNodes)
    .enter().append('g')
    .attr('class', 'node')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('click', (event, d) => selectNode(d));
  
  // Node circles
  node.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => sizeScale(d.connection_count))
    .attr('fill', d => VAULT_COLORS[d.vault] || '#757575');
  
  // Node labels
  node.append('text')
    .attr('class', 'node-label')
    .attr('dx', d => sizeScale(d.connection_count) + 4)
    .attr('dy', '.35em')
    .text(d => d.label)
    .style('font-size', d => Math.max(8, Math.min(12, sizeScale(d.connection_count))) + 'px');
  
  // Update positions
  graphSimulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
  
  function dragstarted(event, d) {
    if (!event.active) graphSimulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  
  function dragended(event, d) {
    if (!event.active) graphSimulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
}

function filterGraph() {
  if (graphSimulation) {
    graphSimulation.stop();
    graphSimulation = null;
  }
  initGraphViz();
}

async function selectNode(node) {
  selectedNode = node;
  const selectionPanel = document.getElementById('graph-selection');
  const nodeInfo = document.getElementById('selected-node-info');
  const connected = document.getElementById('connected-nodes');
  
  nodeInfo.innerHTML = `
    <div style="font-size:.7rem;font-weight:600;color:var(--amber);margin-bottom:.3rem">${node.label}</div>
    <div style="font-size:.6rem;color:var(--text3)">${node.id}</div>
    <div style="font-size:.6rem;color:var(--text2);margin-top:.3rem">
      <span class="vault-dot vault-${node.vault}"></span> ${node.vault} • ${node.connection_count} connections
    </div>
  `;
  
  try {
    const res = await fetch(API + '/graph/related/' + encodeURIComponent(node.id) + '?limit=10');
    const related = await res.json();
    
    connected.innerHTML = related.map(r => `
      <div style="font-size:.6rem;padding:.3rem 0;border-bottom:1px solid var(--border);cursor:pointer" onclick="focusNode('${r.path}')">
        <div style="color:var(--text2)">${r.title}</div>
        <div style="color:var(--text3);font-size:.55rem">
          <span class="vault-dot vault-${r.vault}"></span> ${r.vault} • ${r.link_type}
        </div>
      </div>
    `).join('');
    
    selectionPanel.style.display = 'block';
  } catch (e) {
    connected.innerHTML = '<div style="font-size:.6rem;color:var(--red)">Failed to load connections</div>';
  }
  
  // Highlight in visualization
  d3.selectAll('.node-circle')
    .classed('dim', d => d.id !== node.id)
    .classed('highlight', d => d.id === node.id);
  
  d3.selectAll('.link-line')
    .classed('highlight', d => d.source.id === node.id || d.target.id === node.id);
}

async function focusNode(path) {
  const node = graphData.nodes.find(n => n.id === path);
  if (node) {
    selectNode(node);
    // Center view on node
    const svg = d3.select('#graph-viz svg');
    const width = document.getElementById('graph-viz').clientWidth;
    const height = document.getElementById('graph-viz').clientHeight;
    svg.transition().duration(750).call(
      d3.zoom().transform,
      d3.zoomIdentity.translate(width/2, height/2).scale(1.5).translate(-node.x, -node.y)
    );
  }
}

async function searchGraph() {
  const query = document.getElementById('graph-search').value.trim();
  if (!query) return;
  
  try {
    const res = await fetch(API + '/graph/nodes?query=' + encodeURIComponent(query) + '&limit=10');
    const nodes = await res.json();
    
    if (nodes.length > 0) {
      // Highlight matching nodes
      d3.selectAll('.node-circle')
        .classed('dim', d => !nodes.some(n => n.id === d.id))
        .classed('highlight', d => nodes.some(n => n.id === d.id));
      
      // If single match, select it
      if (nodes.length === 1) {
        selectNode(nodes[0]);
      }
    }
  } catch (e) {
    console.error('Search failed:', e);
  }
}

function resetGraphZoom() {
  const svg = d3.select('#graph-viz svg');
  const width = document.getElementById('graph-viz').clientWidth;
  const height = document.getElementById('graph-viz').clientHeight;
  svg.transition().duration(750).call(
    d3.zoom().transform,
    d3.zoomIdentity.translate(0, 0).scale(1)
  );
  
  // Reset highlights
  d3.selectAll('.node-circle').classed('dim', false).classed('highlight', false);
  d3.selectAll('.link-line').classed('highlight', false);
  document.getElementById('graph-selection').style.display = 'none';
}

async function toggleBacklinks() {
  showBacklinks = !showBacklinks;
  if (graphSimulation) {
    graphSimulation.stop();
    graphSimulation = null;
  }
  await loadGraphData();
  initGraphViz();
}

async function reindexGraph() {
  if (!confirm('Reindex vault? This may take a moment.')) return;
  
  try {
    const res = await fetch(API + '/graph/reindex', { method: 'POST' });
    const result = await res.json();
    alert(`Reindexed: ${result.vaults_scanned} vaults, ${result.total_links_created} links`);
    await loadGraphData();
    initGraphViz();
  } catch (e) {
    alert('Reindex failed: ' + e.message);
  }
}

// ── Init ──
loadStatus();
loadModelOptions();
loadBrowseCounts();
browseTable('vector_memory');
setInterval(loadStatus, 30000);
</script>
<script src="https://d3js.org/d3.v7.min.js"></script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    return _HTML
