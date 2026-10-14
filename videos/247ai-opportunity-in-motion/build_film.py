"""Rebuild the original 24x7 AI launch composition from editable scene definitions."""
from pathlib import Path
import json, html, shutil
ROOT=Path(__file__).resolve().parent

CSS=r"""
@font-face{font-family:Geist;src:url('fonts/geist.woff2') format('woff2');font-weight:100 900;font-display:block}
@font-face{font-family:'Geist Mono';src:url('fonts/geist-mono.woff2') format('woff2');font-weight:100 900;font-display:block}
*{box-sizing:border-box}body{margin:0;background:#080e18;color:#f7faff;font-family:Geist,sans-serif}
h1,h2,h3,p{margin:0}svg{display:block}img{display:block}button{font:inherit}
:root{--night:#080e18;--paper:#f7faff;--ink:#172033;--blue:#284bd8;--sky:#a6d4fc;--mint:#b7dfc5;--muted:#9aa7b8}
.fill{position:absolute;inset:0}.dark{background:var(--night);color:var(--paper)}.light{background:var(--paper);color:var(--ink)}.blue{background:var(--blue);color:var(--paper)}
.grid{background-image:linear-gradient(#a6d4fc0a 1px,transparent 1px),linear-gradient(90deg,#a6d4fc0a 1px,transparent 1px);background-size:96px 96px}
.orb-light{position:absolute;inset:0;background:radial-gradient(ellipse at 76% 50%,#284bd832 0%,transparent 54%);pointer-events:none}
.mono{font-family:'Geist Mono',monospace;font-size:22px;letter-spacing:.1em;text-transform:uppercase;line-height:1.4}
.overline{position:absolute;left:104px;top:162px;color:var(--sky)}
.head{font-size:150px;line-height:.98;letter-spacing:-.065em;font-weight:650}
.display{font-size:205px;line-height:.95;letter-spacing:-.07em;font-weight:650}
.mask{overflow:hidden;padding-bottom:.08em}.mask>span{display:block}
.rail{position:absolute;left:104px;right:104px;bottom:64px;display:flex;align-items:center;justify-content:space-between;border-top:1px solid #a6d4fc33;padding-top:22px;color:#9aa7b8}
.rail.light-rail{border-color:#17203326;color:#526175}.rail.blue-rail{border-color:#ffffff3b;color:#dce6ff}
.smallbrand{position:absolute;top:64px;left:104px;display:flex;align-items:center;gap:13px;font-size:27px;letter-spacing:-.04em;font-weight:600}
.smallbrand img{width:32px;height:32px}.chapter{position:absolute;top:70px;right:104px;color:#9aa7b8}
.line-art{position:absolute;inset:0;pointer-events:none;overflow:visible}.path{fill:none;stroke:var(--sky);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.phone{width:390px;height:700px;position:absolute;border:3px solid #7890b8;border-radius:64px;padding:14px;background:linear-gradient(130deg,#a7bce1,#182238 9%,#07101c 85%,#667c9b);box-shadow:0 60px 110px #0009,18px 15px 0 -10px #121d30;transform-style:preserve-3d}
.phone-screen{width:100%;height:100%;border:1px solid #34445f;border-radius:48px;background:radial-gradient(ellipse at 50% 28%,#244b9045,transparent 60%),#0b1421;position:relative;overflow:hidden}
.phone-notch{width:130px;height:28px;position:absolute;left:115px;top:20px;border-radius:30px;background:#03070e}
.phone-label{position:absolute;top:115px;width:100%;text-align:center;font-size:21px;color:#a6d4fc}
.phone-title{position:absolute;top:157px;width:100%;text-align:center;font-size:42px;letter-spacing:-.05em;font-weight:550}
.phone-circle{position:absolute;left:104px;top:274px;width:150px;height:150px;border-radius:50%;display:grid;place-items:center;background:#183251;border:1px solid #4d79aa}
.phone-circle img{width:75px;height:75px}.phone-actions{position:absolute;bottom:65px;left:52px;right:52px;display:flex;justify-content:space-between}
.action{width:78px;height:78px;border-radius:50%;display:grid;place-items:center;font-size:31px;background:#ffffff12;border:1px solid #ffffff24}
.action.green{background:#b7dfc5;color:#172033;border:0}.phone-home{position:absolute;bottom:17px;left:122px;width:112px;height:5px;border-radius:4px;background:#ebf4ff}
.signal-bar{width:10px;height:120px;background:var(--sky);border-radius:12px;transform-origin:center}.wave{display:flex;gap:10px;align-items:center;height:150px}
.pill{border:1px solid #a6d4fc55;border-radius:99px;padding:14px 24px;font-size:23px;display:inline-flex;gap:12px;align-items:center}
.dot{display:inline-block;width:10px;height:10px;background:var(--mint);border-radius:50%}
.workflow-label{position:absolute;bottom:116px;left:104px;font-family:'Geist Mono',monospace;font-size:17px;color:#9aa7b8;letter-spacing:.08em;text-transform:uppercase}
.panel{background:#101a28;border:1px solid #a6d4fc35;border-radius:36px;box-shadow:0 35px 85px #0005;overflow:hidden}
"""
(ROOT/"assets/film.css").write_text(CSS)
def brand(dark=True):
    return f'<div class="smallbrand"><img data-layout-ignore src="assets/brand/{"mark-on-dark" if dark else "mark"}.svg" alt=""><span>24x7 AI</span></div>'
def rail(n,name,dark=True,blue=False):
    return f'<div class="rail {"blue-rail" if blue else "" if dark else "light-rail"}"><span class="mono">{n:02d} / {name}</span><span class="mono">Opportunity in motion</span></div>'
def wave(prefix,count=23,color=""):
    return '<div class="wave">'+''.join(f'<i id="{prefix}-{i}" class="signal-bar" style="height:{24+((i*19+31)%97)}px;{color}"></i>' for i in range(count))+'</div>'
def draw(tl,selector,start,duration=1.2):
    return f"""{{const path=document.querySelector("{selector}");const length=path.getTotalLength();{tl}.fromTo(path,{{strokeDasharray:length,strokeDashoffset:length}},{{strokeDashoffset:0,duration:{duration},ease:"power3.inOut"}},{start});}}"""
def enter(tl,selector,start,y=70,d=.8):
    return f'{tl}.fromTo("{selector}",{{y:{y},opacity:0}},{{y:0,opacity:1,duration:{d},ease:"power3.out"}},{start});'
def fade(tl,selector,start,d=.5):
    return f'{tl}.fromTo("{selector}",{{opacity:0}},{{opacity:1,duration:{d}}},{start});'
scenes=[]
def scene(n,name,fill,markup,css,js):
    cid=f"s{n:02d}"
    source=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{name}</title></head><body><template>
<style>@font-face{{font-family:Geist;src:url("assets/fonts/geist.woff2");font-weight:100 900}}@font-face{{font-family:"Geist Mono";src:url("assets/fonts/geist-mono.woff2");font-weight:100 900}}#{cid}-root{{position:absolute;inset:0;width:100%;height:100%;overflow:hidden}}{css}</style>
<div id="{cid}-root" data-composition-id="{cid}" data-width="1920" data-height="1080" data-duration="8">
<div class="fill {fill}">{markup}</div></div>
<script>(function(){{const t{n:02d}=gsap.timeline({{paused:true}});{js}window.__timelines["{cid}"]=t{n:02d};}})();</script>
</template></body></html>"""
    path=f"compositions/scenes/{cid}-{name.lower().replace(' ','-')}.html"
    (ROOT/path).write_text(source)
    scenes.append((cid,path,name))
# 1 — make the after-hours promise clear before the brand reveal.
markup=brand()+'''<div class="fill grid"></div><div class="orb-light"></div>
<div id="s01-copy" style="position:absolute;left:104px;top:290px;width:1030px;z-index:3">
<div class="mask"><span id="s01-line1" class="head">Doors close.</span></div>
<div class="mask"><span id="s01-line2" class="head" style="color:#a6d4fc">AI still answers.</span></div></div>
<div id="s01-kicker" class="overline mono">The call after closing.</div>
<div id="s01-phone" class="phone" style="left:1320px;top:165px">
<div class="phone-screen"><div class="phone-notch"></div><div class="phone-label mono">Incoming call</div><div class="phone-title">After-hours caller</div>
<div id="s01-circle" class="phone-circle"><img data-layout-ignore src="assets/brand/mark-on-dark.svg" alt=""></div>
<div class="phone-actions"><div class="action">···</div><div class="action green">↗</div></div><div class="phone-home"></div></div></div>
<svg class="line-art" viewBox="0 0 1920 1080"><circle id="s01-ring" cx="1515" cy="510" r="240" class="path" style="stroke:#a6d4fc;stroke-width:2"/><circle id="s01-ring2" cx="1515" cy="510" r="325" class="path" style="stroke:#284bd8;stroke-width:2"/></svg>
<div id="s01-time" class="pill mono" style="position:absolute;left:105px;top:700px"><span class="dot"></span>After-hours calls answered.</div>'''+rail(1,"The moment")
js=enter("t01","#s01-line1",.25,175,1)+enter("t01","#s01-line2",2.2,175,1)+fade("t01","#s01-kicker",.1)
js+='t01.fromTo("#s01-phone",{rotationY:-35,rotationZ:10,y:220,opacity:0,transformPerspective:1600},{rotationY:-18,rotationZ:6,y:0,opacity:1,duration:1.8,ease:"power3.out"},2.6);'
js+=draw("t01","#s01-ring",.1,2)+draw("t01","#s01-ring2",1.5,2.5)+enter("t01","#s01-time",4.3,35)
js+='t01.fromTo("#s01-circle",{scale:1},{scale:1.12,duration:.25,yoyo:true,repeat:3,ease:"sine.inOut"},5);t01.to("#s01-ring2",{scale:4,transformOrigin:"1515px 510px",opacity:.1,duration:.6,ease:"power3.in"},7.4);'
scene(1,"The moment","dark",markup,"",js)
# 2 — cobalt introduction, giant wordmark and ring-to-mark transformation.
markup='''<div id="s02-ring" style="position:absolute;left:660px;top:205px;width:600px;height:600px;border:2px solid #ffffff55;border-radius:50%"></div>
<div id="s02-mark" style="position:absolute;left:208px;top:310px;width:210px;height:210px"><img data-layout-ignore src="assets/brand/mark-on-dark.svg" style="width:100%;height:100%" alt=""></div>
<div id="s02-brand" class="display" style="position:absolute;left:470px;top:295px;font-size:240px"><span>24x7</span> <span style="color:#b7dfc5">AI</span></div>
<div id="s02-top" class="mono" style="position:absolute;left:470px;top:235px;color:#dce6ff">Meet your AI front desk.</div>
<div class="mask" style="position:absolute;left:470px;top:590px;height:105px;width:1300px"><div id="s02-ready" style="font-size:68px;letter-spacing:-.045em">Calls answered. Appointments booked.</div></div>
<svg class="line-art" viewBox="0 0 1920 1080"><path id="s02-line" d="M104 805 H1450 Q1640 805 1920 510" class="path" style="stroke:#b7dfc5;stroke-width:3"/></svg>'''+rail(2,"The answer",blue=True)
js='t02.fromTo("#s02-ring",{scale:2.5,opacity:0},{scale:1,opacity:1,duration:1.4,ease:"power3.out"},0);t02.to("#s02-ring",{scale:.1,opacity:0,duration:1,ease:"power3.inOut"},1.6);'
js+='t02.fromTo("#s02-mark",{x:550,scale:.4,rotation:-25,opacity:0},{x:0,scale:1,rotation:0,opacity:1,duration:1.2,ease:"power3.out"},1.1);'
js+=enter("t02","#s02-brand",1.8,180,1)+fade("t02","#s02-top",.6)+enter("t02","#s02-ready",4.3,120,1)+draw("t02","#s02-line",5.8,1.5)
scene(2,"The answer","blue",markup,"",js)
# 3 — phone and real captured website converge.
markup=brand()+'''<div class="fill grid"></div><div class="orb-light"></div>
<div id="s03-title" style="position:absolute;left:104px;top:157px;font-size:88px;font-weight:600;letter-spacing:-.055em">Wherever they call.</div>
<div id="s03-phone" class="phone" style="left:305px;top:300px;width:300px;height:530px;border-radius:48px">
<div class="phone-screen" style="border-radius:34px"><div class="phone-notch" style="left:85px;width:100px;height:20px;top:16px"></div>
<div class="phone-label mono" style="top:85px;font-size:16px">Business number</div><div class="phone-title" style="top:130px;font-size:32px">Connected.</div>
<div class="phone-circle" style="left:72px;top:225px;width:125px;height:125px"><img data-layout-ignore src="assets/brand/mark-on-dark.svg" style="width:65px" alt=""></div><div class="phone-home" style="left:85px;bottom:15px;width:100px"></div></div></div>
<div id="s03-web" class="panel" style="position:absolute;left:1200px;top:295px;width:510px;height:540px;padding:22px;background:#0b1421">
<img src="assets/product/website-crop.png" alt="24x7 AI public website" style="width:100%;height:430px;object-fit:cover;object-position:top">
<div class="pill" style="margin-top:10px;background:#d1e9fe;color:#172033;font-size:22px;border:0"><img data-layout-ignore src="assets/brand/mark.svg" style="width:25px;height:25px" alt="">Website voice button</div></div>
<svg class="line-art" viewBox="0 0 1920 1080"><path id="s03-route" d="M606 570 H780 Q820 570 820 610 V680 Q820 730 870 730 H1050 Q1100 730 1100 680 V610 Q1100 570 1140 570 H1200" class="path" style="stroke:#284bd8;stroke-width:5"/></svg>
<div id="s03-voice" style="position:absolute;left:765px;top:430px">'''+wave("s03-wave",20)+'''</div>
<div id="s03-phone-label" class="mono" style="position:absolute;left:330px;top:855px;color:#a6d4fc">Your phone.</div>
<div id="s03-web-label" class="mono" style="position:absolute;left:1310px;top:855px;color:#a6d4fc">Your website.</div>
<div id="s03-one" style="position:absolute;left:730px;top:765px;width:460px;text-align:center;font-size:36px;letter-spacing:-.03em">One natural conversation.</div>'''+rail(3,"Answer everywhere")
js=enter("t03","#s03-title",.1)
js+='t03.fromTo("#s03-phone",{x:-250,rotationY:30,rotationZ:-8,opacity:0,transformPerspective:1800},{x:0,rotationY:12,rotationZ:-4,opacity:1,duration:1.3,ease:"power3.out"},.6);'
js+='t03.fromTo("#s03-web",{x:250,rotationY:-25,rotationZ:7,opacity:0,transformPerspective:1800},{x:0,rotationY:-12,rotationZ:3,opacity:1,duration:1.3,ease:"power3.out"},2);'
js+=enter("t03","#s03-phone-label",1)+enter("t03","#s03-web-label",2.7)+draw("t03","#s03-route",3.4,1)+fade("t03","#s03-voice",4.1)+enter("t03","#s03-one",5.3,30)
for i in range(20):js+=f't03.fromTo("#s03-wave-{i}",{{scaleY:.15}},{{scaleY:{.35+(i*7%8)/10},duration:.35,yoyo:true,repeat:9,ease:"sine.inOut"}},{4.1+i*.018});'
scene(3,"Everywhere","dark",markup,"",js)
# 4 — an adapted, widest-word grid slot cycles in place.
markup=brand(False)+'''<div class="overline mono" style="color:#284bd8">It knows how your business works.</div>
<div id="s04-your" class="display" style="position:absolute;left:104px;top:300px;font-size:220px">Your</div>
<div id="s04-slot" style="position:absolute;left:665px;top:285px;height:260px;width:1120px;overflow:hidden;display:grid">
<div id="s04-hours" class="display s04-token">hours.</div><div id="s04-services" class="display s04-token">services.</div><div id="s04-way" class="display s04-token">way.</div></div>
<div id="s04-knowledge" style="position:absolute;left:110px;top:670px;display:flex;gap:24px">
<div id="s04-k1" class="pill" style="border-color:#17203336">Opening hours</div><div id="s04-k2" class="pill" style="border-color:#17203336">Services &amp; prices</div><div id="s04-k3" class="pill" style="border-color:#17203336">Policies &amp; workflows</div></div>
<svg class="line-art" viewBox="0 0 1920 1080"><path id="s04-line" d="M110 610 H1150 C1250 610 1270 680 1350 680 S1450 590 1530 590 S1660 660 1816 660" class="path" style="stroke:#284bd8;stroke-width:5"/></svg>
<div id="s04-footer" style="position:absolute;left:110px;top:810px;font-size:34px;letter-spacing:-.025em;color:#526175">Relevant answers. In your voice.</div>'''+rail(4,"Business knowledge",False)
css='.s04-token{grid-area:1/1;color:#284bd8;font-size:220px;line-height:1.15;width:max-content}'
js=enter("t04","#s04-your",.15,190,1)+enter("t04","#s04-hours",.35,250,.9)
js+='t04.fromTo("#s04-services",{y:260,opacity:0},{y:0,opacity:1,duration:.65,ease:"power3.out"},2.2);t04.to("#s04-hours",{y:-260,opacity:0,duration:.65,ease:"power3.inOut"},2.2);t04.fromTo("#s04-way",{y:260,opacity:0},{y:0,opacity:1,duration:.65,ease:"power3.out"},4.1);t04.to("#s04-services",{y:-260,opacity:0,duration:.65,ease:"power3.inOut"},4.1);'
js+=enter("t04","#s04-k1",1.4,30)+enter("t04","#s04-k2",2.9,30)+enter("t04","#s04-k3",4.8,30)+draw("t04","#s04-line",5.3,1.4)+enter("t04","#s04-footer",6.3,24)
scene(4,"Your business","light",markup,css,js)
# 5 — a real workflow, deliberately illustrated, not fabricated app UI.
markup=brand(False)+'''<div id="s05-question" style="position:absolute;left:104px;top:180px;width:900px;font-size:82px;letter-spacing:-.05em;line-height:1.08">“Are you free<br aria-hidden="true">tomorrow?”</div>
<div id="s05-card" style="position:absolute;left:1200px;top:180px;width:500px;height:610px;background:#eaf0fa;border:2px solid #cfdaed;border-radius:36px;padding:36px;box-shadow:0 40px 100px #17203316">
<div class="mono" style="color:#526175">Availability</div><div style="font-size:42px;letter-spacing:-.04em;margin-top:14px">Tomorrow</div>
<div class="s05-days"><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span></div>
<div id="s05-slots"><div class="s05-slot" style="color:#66758b">09:00 <span>Unavailable</span></div><div id="s05-chosen" class="s05-slot" style="background:#f7faff;border-color:#284bd8;color:#284bd8">10:00 <span>Available</span></div><div class="s05-slot">11:30 <span>Available</span></div></div>
<div id="s05-scan" style="position:absolute;left:20px;right:20px;top:180px;height:120px;border-radius:24px;background:linear-gradient(transparent,#284bd812,transparent);border-top:2px solid #284bd8"></div></div>
<div id="s05-booked" class="display" style="position:absolute;left:104px;top:530px;font-size:148px;color:#284bd8">You're booked.</div>
<div id="s05-confirm" class="pill" style="position:absolute;left:104px;top:735px;background:#b7dfc5;color:#172033;border:0;font-size:32px;padding:22px 32px"><svg width="35" height="35" viewBox="0 0 40 40"><path id="s05-check" d="M8 21 L17 30 L33 10" fill="none" stroke="#172033" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>Tomorrow · 10:00 AM</div>
<div class="workflow-label" style="color:#526175">Illustrative booking workflow</div>'''+rail(5,"Conversation → booking",False)
# Avoid br inside text: render question as separate block lines.
markup=markup.replace('“Are you free<br aria-hidden="true">tomorrow?”','<div>“Are you free</div><div>tomorrow?”</div>')
css='.s05-days{display:flex;justify-content:space-between;margin-top:38px;padding:0 10px;font-family:"Geist Mono",monospace;font-size:24px;color:#526175}.s05-slot{display:flex;justify-content:space-between;margin-top:18px;border:1px solid #cad5e7;border-radius:18px;padding:21px 23px;font-family:"Geist Mono",monospace;font-size:25px}.s05-slot span{font-family:Geist,sans-serif;font-size:21px}'
js=enter("t05","#s05-question",.15,65,1)
js+='t05.fromTo("#s05-card",{x:180,y:100,rotationY:-22,rotationZ:6,opacity:0,transformPerspective:1800},{x:0,y:0,rotationY:-8,rotationZ:2,opacity:1,duration:1.3,ease:"power3.out"},1.5);t05.fromTo("#s05-scan",{y:0,opacity:0},{y:220,opacity:1,duration:1.4,ease:"power2.inOut"},2.7);t05.to("#s05-scan",{opacity:0,duration:.3},4.1);t05.to("#s05-chosen",{backgroundColor:"#b7dfc5",color:"#172033",borderColor:"#b7dfc5",scale:1.05,duration:.6,ease:"power3.out"},4.2);'
js+=enter("t05","#s05-booked",4.4,130,1)+enter("t05","#s05-confirm",5.2,35)+draw("t05","#s05-check",5.7,.65)
scene(5,"Booked","light",markup,css,js)
# 6 — causal drawn route, output nodes rather than a logo wall.
markup=brand()+'''<div class="fill grid"></div><div id="s06-title" class="head" style="position:absolute;left:104px;top:170px;font-size:115px">Keep the next step moving.</div>
<div id="s06-request" class="panel" style="position:absolute;left:105px;top:420px;width:440px;height:330px;padding:34px">
<div class="mono" style="color:#a6d4fc">Request captured</div><div style="font-size:49px;letter-spacing:-.045em;line-height:1.05;margin-top:35px">A customer.<div>A clear next step.</div></div><div class="pill" style="margin-top:30px;font-size:20px"><span class="dot"></span>Context included</div></div>
<svg class="line-art" viewBox="0 0 1920 1080"><path id="s06-route" d="M545 580 H730 Q790 580 790 520 V430 Q790 380 840 380 H1540 Q1600 380 1600 440 V710 Q1600 770 1540 770 H1130 Q1070 770 1070 710 V640 Q1070 580 1130 580 H1815" class="path" style="stroke:#a6d4fc;stroke-width:5"/><circle id="s06-pulse" cx="545" cy="580" r="9" fill="#b7dfc5"/></svg>
<div id="s06-n1" class="s06-node" style="left:850px;top:285px"><div class="s06-icon">▦</div><div>Calendar</div><p>Book the time.</p></div>
<div id="s06-n2" class="s06-node" style="left:1330px;top:515px"><div class="s06-icon">↗</div><div>Email</div><p>Send the confirmation.</p></div>
<div id="s06-n3" class="s06-node" style="left:860px;top:680px"><div class="s06-icon">≡</div><div>Records</div><p>Keep the context.</p></div>
<div id="s06-footer" class="mono" style="position:absolute;left:105px;top:835px;color:#a6d4fc">Connected to the tools you already use.</div>
<div class="workflow-label">Illustrative connected workflow · setup varies by connection</div>'''+rail(6,"Conversation → action")
css='.s06-node{position:absolute;background:#101a28;border:1px solid #a6d4fc55;border-radius:24px;padding:25px 32px 26px 90px;min-width:355px;font-size:35px;letter-spacing:-.03em;box-shadow:0 16px 40px #0003}.s06-node p{font-size:21px;color:#9aa7b8;margin-top:7px;letter-spacing:0}.s06-icon{position:absolute;left:25px;top:29px;font-size:40px;color:#b7dfc5}'
js=enter("t06","#s06-title",.1)+enter("t06","#s06-request",.5,90,1)+draw("t06","#s06-route",1.7,3.6)+enter("t06","#s06-n1",2.4,50)+enter("t06","#s06-n2",3.4,50)+enter("t06","#s06-n3",4.6,50)+enter("t06","#s06-footer",6,25)
js += fade("t06","#s06-pulse",1.7,.1)
js += 'const route=document.querySelector("#s06-route"),pulse=document.querySelector("#s06-pulse"),travel={p:0};const routeLength=route.getTotalLength();t06.to(travel,{p:1,duration:3.6,ease:"power3.inOut",onUpdate:()=>{const point=route.getPointAtLength(travel.p*routeLength);pulse.setAttribute("cx",point.x);pulse.setAttribute("cy",point.y);}},1.7);'
scene(6,"Keep it moving","dark",markup,css,js)
# 7 — owner control, three stations share an actual camera journey.
markup=brand()+'''<div class="orb-light"></div><div id="s07-title" class="head" style="position:absolute;left:104px;top:165px;font-size:110px">Your business. Your control.</div>
<div id="s07-world" style="position:absolute;left:105px;top:385px;width:1710px;height:405px">
<div id="s07-instructions" class="panel s07-panel" style="left:0"><div class="mono" style="color:#a6d4fc">01 / Set instructions</div><div class="s07-panel-title">Make it yours.</div><div class="s07-quote" id="s07-quote">“Check availability before booking. Capture callback details after hours.”</div></div>
<div id="s07-test" class="panel s07-panel" style="left:585px"><div class="mono" style="color:#a6d4fc">02 / Test the experience</div><div class="s07-panel-title">Hear it work.</div><div style="margin-top:35px">'''+wave("s07-bar",18)+'''</div></div>
<div id="s07-review" class="panel s07-panel" style="left:1170px"><div class="mono" style="color:#a6d4fc">03 / Review conversations</div><div class="s07-panel-title">Keep the context.</div><div id="s07-recording" style="display:flex;align-items:center;gap:14px;margin-top:42px"><div style="width:55px;height:55px;border-radius:50%;background:#b7dfc5;color:#172033;display:grid;place-items:center;font-size:23px">▶</div><div style="flex:1;height:2px;background:#a6d4fc;position:relative"><span style="position:absolute;width:10px;height:10px;border-radius:50%;background:#b7dfc5;top:-4px;left:38%"></span></div></div><p style="font-size:25px;color:#9aa7b8;margin-top:27px">Recordings · transcripts · call logs</p></div></div>
<div class="workflow-label">Illustrative owner workflow</div>'''+rail(7,"Set · test · review")
css='.s07-panel{position:absolute;top:0;width:540px;height:405px;padding:34px}.s07-panel-title{font-size:49px;letter-spacing:-.045em;margin-top:30px;line-height:1.06}.s07-quote{font-size:28px;letter-spacing:-.015em;line-height:1.35;color:#c8d8e9;margin-top:26px}'
js=enter("t07","#s07-title",.1)+enter("t07","#s07-instructions",.5,70)
js+='t07.fromTo("#s07-world",{x:70,y:-60,scale:1.45,transformOrigin:"0% 0%"},{x:70,y:-60,scale:1.45,duration:.01},0);t07.to("#s07-world",{x:-700,duration:.85,ease:"power3.inOut"},2.15);t07.to("#s07-world",{x:-1545,duration:.85,ease:"power3.inOut"},3.95);t07.to("#s07-world",{x:0,y:0,scale:1,duration:1.1,ease:"power3.inOut"},6.15);'
js+=enter("t07","#s07-test",2.2,85)+enter("t07","#s07-review",4,85)+fade("t07","#s07-recording",5.1)
for i in range(18):js+=f't07.fromTo("#s07-bar-{i}",{{scaleY:.1}},{{scaleY:{.3+(i*5%8)/10},duration:.3,yoyo:true,repeat:7,ease:"sine.inOut"}},{2.8+i*.02});'
scene(7,"Your control","dark",markup,css,js)
# 8 — kinetic emotional payoff with contrasting scale and a single open frame.
markup='''<div id="s08-top" class="mono" style="position:absolute;left:104px;top:125px;color:#dce6ff">You do what you do best.</div>
<div class="mask" style="position:absolute;left:104px;top:280px;width:1710px;height:200px"><div id="s08-less" class="head" style="font-size:170px">Less interruption.</div></div>
<div class="mask" style="position:absolute;left:104px;top:485px;width:1710px;height:195px"><div id="s08-more" class="head" style="font-size:170px;color:#b7dfc5">More room.</div></div>
<div id="s08-work" style="position:absolute;left:110px;top:720px;font-size:61px;letter-spacing:-.04em">For the work you love.</div>
<svg class="line-art" viewBox="0 0 1920 1080"><path id="s08-frame" d="M1840 900 V180 Q1840 80 1740 80 H1600 M80 900 H1400 Q1550 900 1550 760 V690" fill="none" stroke="#a6d4fc" stroke-width="3" stroke-linecap="round"/></svg>'''+rail(8,"Room for your work",blue=True)
js=fade("t08","#s08-top",.2)+enter("t08","#s08-less",.5,220,.9)+enter("t08","#s08-more",2.5,220,1)+enter("t08","#s08-work",4.2,60,1)+draw("t08","#s08-frame",5.1,1.5)
scene(8,"More room","blue",markup,"",js)
# 9 — the official mark is the endpoint, not a new invented logo.
markup='''<div class="fill grid"></div><div class="orb-light"></div>
<svg class="line-art" viewBox="0 0 1920 1080"><circle id="s09-ring" cx="960" cy="380" r="170" class="path" style="stroke:#284bd8;stroke-width:3"/></svg>
<div id="s09-mark" style="position:absolute;left:870px;top:280px;width:180px;height:180px"><img data-layout-ignore src="assets/brand/mark-on-dark.svg" style="width:100%;height:100%" alt="24x7 AI"></div>
<div id="s09-brand" style="position:absolute;left:0;right:0;top:500px;text-align:center;font-size:150px;letter-spacing:-.07em;font-weight:650">24x7 <span style="color:#a6d4fc">AI</span></div>
<div id="s09-cta" style="position:absolute;left:0;right:0;top:700px;text-align:center;font-size:54px;letter-spacing:-.035em">Hear what happens next.</div>
<div id="s09-url" class="pill" style="position:absolute;left:765px;top:805px;width:390px;justify-content:center;font-size:35px;color:#b7dfc5;border-color:#b7dfc566">247ai.live <span style="margin-left:20px">↗</span></div>
<div id="s09-note" class="mono" style="position:absolute;left:0;right:0;top:100px;text-align:center;color:#9aa7b8">Your after-hours AI front desk.</div>'''
js='t09.fromTo("#s09-ring",{scale:3,opacity:0,transformOrigin:"960px 380px"},{scale:1,opacity:1,duration:1.2,ease:"power3.out"},0);t09.to("#s09-ring",{scale:.4,opacity:0,duration:1,ease:"power3.inOut"},1.2);'
js+='t09.fromTo("#s09-mark",{scale:.5,rotation:-25,opacity:0},{scale:1,rotation:0,opacity:1,duration:1.2,ease:"power3.out"},.7);'
js+=enter("t09","#s09-brand",1.3,100,1)+enter("t09","#s09-cta",2.7,45,.8)+enter("t09","#s09-url",3.7,30,.7)+fade("t09","#s09-note",4.4)
scene(9,"Hear it","dark",markup,"",js)
# Master edit and root audio. Static clip timing is owned by HyperFrames.
voice_durations=[4.022857,6.243265,5.537,4.728,4.127,5.146,5.093,3.892,3.631]
voice_starts=[1.1,8.6,16.7,24.5,32.6,40.5,48.5,56.7,64.6]
pts=[{"t":0,"v":.5}]
for st,dur in zip(voice_starts,voice_durations):
    pts.extend([{"t":max(0,st-.25),"v":.5},{"t":st,"v":.19},{"t":st+dur,"v":.19},{"t":st+dur+.45,"v":.5}])
pts.extend([{"t":70.1,"v":.5},{"t":72,"v":0}])
pts.sort(key=lambda x:x["t"])
auto=html.escape(json.dumps({"version":1,"lanes":[{"target":"volume","points":pts}]}),quote=True)
master_fx=html.escape(json.dumps({"version":1,"nodes":[{"type":"limiter","id":"peak","label":"Master peak ceiling","params":{"limit":-1.5,"attack":5,"release":80,"level_out":0}}]}),quote=True)
master=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>24x7 AI — Opportunity in motion</title><link rel="stylesheet" href="assets/film.css"><script src="assets/vendor/gsap.min.js"></script><style>#main-root{{position:relative;width:100%;height:100%;overflow:hidden}}.scene-host{{position:absolute;inset:0}}</style></head><body><div id="main-root" data-fx-chain="{master_fx}" data-composition-id="main" data-width="1920" data-height="1080" data-duration="72" data-fps="30">'
for i,(cid,path,name) in enumerate(scenes):
    master+=f'<div id="{cid}-host" class="scene-host clip" data-composition-id="{cid}" data-composition-src="{path}" data-start="{i*8}" data-duration="8" data-track-index="0" data-width="1920" data-height="1080" data-label="{html.escape(name)}"></div>'
master+=f'<audio id="original-score" src="assets/audio/score-mix.wav" data-start="0" data-duration="72" data-track-index="2" data-volume="0.5" data-automation="{auto}"></audio>'
for i,(st,dur) in enumerate(zip(voice_starts,voice_durations),1):
    master+=f'<audio id="voice-{i:02d}" src="assets/audio/voice-{i:02d}.mp3" data-start="{st}" data-duration="{dur}" data-track-index="1" data-volume="0.82"></audio>'
for st in [8,16,24,32,40,48,56,64]:
    master+=f'<audio id="sweep-{st}" src="assets/audio/transition.wav" data-start="{st-.20}" data-duration=".55" data-track-index="3" data-volume=".16"></audio>'
for st in [9.3,36.9,65.7]:
    master+=f'<audio id="chime-{st}" src="assets/audio/resolve.wav" data-start="{st}" data-duration="1.2" data-track-index="4" data-volume=".22"></audio>'
master+='</div><script>const main=gsap.timeline({paused:true});main.to({}, {duration:72});window.__timelines["main"]=main;</script></body></html>'
(ROOT/"index.html").write_text(master)
# Metadata and separate optional subtitles.
meta={"name":"24x7 AI — Opportunity in motion","description":"An original 72-second product launch film. Nine editable motion scenes, original score and narration.","duration":72,"width":1920,"height":1080,"fps":30}
(ROOT/"meta.json").write_text(json.dumps(meta,indent=2))
(ROOT/"edit.json").write_text(json.dumps({"duration":72,"fps":30,"scenes":[{"id":s[0],"source":s[1],"start":i*8,"duration":8,"name":s[2]} for i,s in enumerate(scenes)],"voice_starts":voice_starts},indent=2))
def stamp(s):
    ms=round(s*1000); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
lines=["Your doors are closed. Customers still get answers.","Twenty-four seven AI answers calls, helps customers, and books appointments.","On your phone. On your website. A real conversation, in real time.","Your hours. Your services. Your way of doing things.","From “Are you free tomorrow?” to “You're booked.”","Capture the request. Connect your tools. Keep the next step moving.","You set the instructions. Test the experience. Review the conversations.","Less interruption. More room for the work you love.","Twenty-four seven AI. Hear what happens next."]
(ROOT/"renders/captions.srt").write_text("\n\n".join(f"{i+1}\n{stamp(st)} --> {stamp(st+d)}\n{line}" for i,(st,d,line) in enumerate(zip(voice_starts,voice_durations,lines)))+"\n")
print("Built nine editable scenes and a 72-second master.")

\n