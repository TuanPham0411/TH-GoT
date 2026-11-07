'use strict';
(() => {
 const $=s=>document.querySelector(s), viewport=$('#realmViewport');
 let reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 document.body.classList.toggle('realm-no-motion',reduced);
 $('#realmMotion').setAttribute('aria-pressed',String(!reduced));
 $('#realmMotion').onclick=()=>{reduced=!reduced;document.body.classList.toggle('realm-no-motion',reduced);$('#realmMotion').setAttribute('aria-pressed',String(!reduced));};
 $('#realmBag').onclick=()=>{const bag=$('#realmBackpack');bag.hidden=!bag.hidden;$('#realmBag').setAttribute('aria-expanded',String(!bag.hidden));if(!bag.hidden)$('#worldProfile').focus();};
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#realmBackpack').hidden=true;$('#realmBag').setAttribute('aria-expanded','false');}});
 $('#realmPanLeft').onclick=()=>viewport.scrollBy({left:-350,behavior:reduced?'instant':'smooth'});
 $('#realmPanRight').onclick=()=>viewport.scrollBy({left:350,behavior:reduced?'instant':'smooth'});
 requestAnimationFrame(()=>{viewport.scrollLeft=(viewport.scrollWidth-viewport.clientWidth)*.48;});
 viewport.addEventListener('keydown',e=>{if(e.target!==viewport)return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();viewport.scrollBy({left:e.key==='ArrowLeft'?-180:180,behavior:reduced?'instant':'smooth'});}});
 // Mouse drag supplements native touch scrolling; interactive landmarks stay clickable.
 let drag=null;
 viewport.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.target.closest('button,a'))return;drag={x:e.clientX,left:viewport.scrollLeft};viewport.setPointerCapture(e.pointerId);});
 viewport.addEventListener('pointermove',e=>{if(drag)viewport.scrollLeft=drag.left+drag.x-e.clientX;});
 viewport.addEventListener('pointerup',()=>drag=null);viewport.addEventListener('pointercancel',()=>drag=null);
 const fireflies=$('.realm-fireflies');for(let i=0;i<28;i++){const dot=document.createElement('i');dot.style.left=(7+(i*31)%87)+'%';dot.style.top=(18+(i*17)%69)+'%';dot.style.setProperty('--duration',(5+i%7)+'s');dot.style.setProperty('--delay',(-i*.7)+'s');fireflies.append(dot);}
 // Original pentatonic score and event sounds, created locally without downloads.
 let ctx,master,timer,on=false,step=0;const notes=[0,7,12,16,19,16,12,7,2,9,14,17,21,17,14,9];
 function voice(freq,at,duration,volume,type='sine'){if(!ctx||!on)return;const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type=type;osc.frequency.value=freq;gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(volume,at+.018);gain.gain.exponentialRampToValueAtTime(.0001,at+duration);osc.connect(gain).connect(master);osc.start(at);osc.stop(at+duration+.03);}
 function play(kind){if(!ctx||!on||document.hidden)return;const t=ctx.currentTime;const pitches=kind==='travel'?[523.25,659.25,783.99,1046.5]:kind==='success'?[659.25,783.99,987.77]:kind==='page'?[280,220]:[392];pitches.forEach((f,i)=>voice(f,t+i*.075,.4,.028,'sine'));}
 function score(){if(!on||document.hidden)return;const t=ctx.currentTime;voice(261.63*2**(notes[step%notes.length]/12),t,1.5,.018,'triangle');if(step%4===0){voice(step%16<8?130.81:146.83,t,2.2,.012);voice(step%16<8?196:220,t,1.9,.008);}step++;}
 async function toggle(){on=!on;try{if(on){ctx ||= new (window.AudioContext||window.webkitAudioContext)();if(!master){master=ctx.createGain();master.gain.value=.65;master.connect(ctx.destination);}await ctx.resume();score();timer=setInterval(score,680);}else{clearInterval(timer);await ctx?.suspend();}}catch{on=false;}$('#realmAudio').setAttribute('aria-pressed',String(on));$('#realmAudio').querySelector('span').textContent=on?'Tắt nhạc':'Âm thanh';}
 $('#realmAudio').onclick=toggle;
 document.addEventListener('realm:travel',()=>{play('travel');$('#realmBackpack').hidden=true;$('#realmBag').setAttribute('aria-expanded','false');});
 document.addEventListener('realm:result',e=>play(e.detail?'success':'retry'));
 $('#storyPrevious').addEventListener('click',()=>play('page'));$('#storyNext').addEventListener('click',()=>play('page'));
 document.addEventListener('visibilitychange',()=>{if(!ctx)return;if(document.hidden)ctx.suspend();else if(on)ctx.resume();});
 window.addEventListener('pagehide',()=>{clearInterval(timer);ctx?.close();});
})();
