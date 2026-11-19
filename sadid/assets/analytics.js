(function(){
  // ---- Tail-risk calculator: runs entirely in the browser ----
  var Z={'0.95':-1.6448536,'0.975':-1.9599640,'0.99':-2.3263479};
  function $(id){return document.getElementById(id)}
  function pct(v){return (v*100).toFixed(2)+'%'}
  var TOKEN=/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?%?$/i;
  function parse(txt){
    // Each entry is read on its own: a trailing % means per cent, anything else is a decimal.
    var raw=txt.split(/[\s,;]+/).filter(Boolean), v=[], bad=[], nPct=0;
    raw.forEach(function(t){
      if(!TOKEN.test(t)){bad.push(t);return}
      var isPct=t.charAt(t.length-1)==='%', n=Number(isPct?t.slice(0,-1):t);
      if(!isFinite(n)){bad.push(t);return}
      if(isPct){n=n/100;nPct++}
      v.push(n);
    });
    return {v:v,bad:bad,nPct:nPct};
  }
  function clearOut(){var c=$('c-out').querySelectorAll('td');for(var i=0;i<c.length;i++)c[i].textContent='-'}
  function run(){
    var d=parse($('c-data').value), v=d.v, n=v.length, msg=$('c-msg'), cells=$('c-out').querySelectorAll('td');
    var conf=$('c-conf').value, a=1-parseFloat(conf), z=Z[conf], need=Math.ceil(2/a);
    if(d.bad.length){clearOut();msg.textContent='Nothing was calculated. '+d.bad.length+' entr'+(d.bad.length>1?'ies':'y')+' could not be read: '+d.bad.slice(0,4).join(', ')+(d.bad.length>4?' and others':'')+'. Correct them and try again.';return}
    if(n<need){clearOut();msg.textContent='Nothing was calculated. At '+(parseFloat(conf)*100)+'% confidence at least '+need+' returns are needed. Found '+n+'.';return}
    var mean=v.reduce(function(x,y){return x+y},0)/n;
    var sd=Math.sqrt(v.reduce(function(x,y){return x+(y-mean)*(y-mean)},0)/(n-1));
    var srt=v.slice().sort(function(x,y){return x-y}), pos=(n-1)*a, lo=Math.floor(pos), q=srt[lo]+(pos-lo)*((srt[lo+1]!==undefined?srt[lo+1]:srt[lo])-srt[lo]);
    var tail=srt.filter(function(x){return x<=q}), es=-tail.reduce(function(x,y){return x+y},0)/tail.length;
    var phi=Math.exp(-z*z/2)/Math.sqrt(2*Math.PI), nvar=-(mean+sd*z), nes=-(mean-sd*phi/a);
    var nums=[mean,sd,q,nvar,es,nes];
    if(nums.some(function(x){return !isFinite(x)})){clearOut();msg.textContent='Nothing was calculated. The values entered do not give a finite result.';return}
    var out=[String(n),pct(mean),pct(sd),pct(-q),pct(nvar),pct(es),pct(nes),String(tail.length),nes>0?(es/nes).toFixed(2):'n/a'];
    for(var i=0;i<cells.length;i++)cells[i].textContent=out[i];
    var notes=[];
    if(d.nPct&&d.nPct<n)notes.push(d.nPct+' entries carried a % sign and were read as per cent. The other '+(n-d.nPct)+' were read as decimals. Check that this mix is intended.');
    else if(d.nPct)notes.push('All entries were read as per cent.');
    else notes.push('All entries were read as decimals, so 0.02 means 2%.');
    if(tail.length<5)notes.push('Only '+tail.length+' observations sit in the tail: treat the tail figures as indicative.');
    msg.textContent=notes.join(' ');
  }
  function sample(){
    // synthetic heavy-tailed monthly returns from a small seeded generator
    var seed=20261118; function r(){seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296}
    function g(){return Math.sqrt(-2*Math.log(r()+1e-12))*Math.cos(2*Math.PI*r())}
    var out=[];for(var i=0;i<120;i++){var c=(g()*g()+g()*g()+g()*g())/3; var t=g()/Math.sqrt(Math.abs(c)+0.35); out.push((0.006+0.032*t).toFixed(4))}
    $('c-data').value=out.join('\n'); run();
  }
  $('c-run').addEventListener('click',run); $('c-data').addEventListener('input',function(){clearOut();$('c-msg').textContent=''}); $('c-conf').addEventListener('change',function(){clearOut();$('c-msg').textContent=''}); $('c-sample').addEventListener('click',sample);
  // ---- Tabs: click, arrow keys, Home and End ----
  var tabs=Array.prototype.slice.call(document.querySelectorAll('.tab'));
  function pick(btn,focus){
    tabs.forEach(function(t){
      var on=t===btn, pn=document.getElementById(t.getAttribute('aria-controls'));
      t.classList.toggle('on',on); t.setAttribute('aria-selected',on?'true':'false'); t.tabIndex=on?0:-1; pn.hidden=!on;
      if(on){var fr=pn.querySelector('iframe[data-src]'); if(fr){fr.src=fr.getAttribute('data-src'); fr.removeAttribute('data-src')}}
    });
    if(focus)btn.focus();
  }
  tabs.forEach(function(t,i){
    t.addEventListener('click',function(){pick(t,false)});
    t.addEventListener('keydown',function(e){
      var n=null;
      if(e.key==='ArrowRight')n=(i+1)%tabs.length; else if(e.key==='ArrowLeft')n=(i-1+tabs.length)%tabs.length;
      else if(e.key==='Home')n=0; else if(e.key==='End')n=tabs.length-1;
      if(n!==null){e.preventDefault();pick(tabs[n],true)}
    });
  });
})();
// ---- Liquidity Delay Explorer: runs entirely in the browser ----
// lxCompute is a pure function so that it can be tested outside the page.
function lxCompute(p){
  // p: {buf, min, d, k, w, inflow[12], outflow[12]}  with d and w as fractions
  var n=p.inflow.length, i, si=[], so=[], base=[], str=[], late=0, beyond=0, later=0;
  for(i=1;i<n;i++)later+=p.outflow[i];
  for(i=0;i<n;i++){
    si.push(p.inflow[i]*(1-p.d)+(i-p.k>=0?p.inflow[i-p.k]*p.d:0));
    so.push(i===0?p.outflow[0]+p.w*later:p.outflow[i]*(1-p.w));
    if(i+p.k<n)late+=p.inflow[i]*p.d; else beyond+=p.inflow[i]*p.d;
  }
  var cb=p.buf, cs=p.buf, fb=0, fs=0, low=Infinity;
  for(i=0;i<n;i++){
    cb+=p.inflow[i]-p.outflow[i]; cs+=si[i]-so[i]; base.push(cb); str.push(cs);
    if(!fb&&cb<p.min)fb=i+1; if(!fs&&cs<p.min)fs=i+1; if(cs<low)low=cs;
  }
  return {si:si,so:so,base:base,str:str,firstBase:fb,firstStress:fs,low:low,extra:Math.max(0,p.min-low),late:late,beyond:beyond};
}
if(typeof module!=='undefined'&&module.exports){module.exports={lxCompute:lxCompute}}
if(typeof document!=='undefined'){(function(){
  function $(id){return document.getElementById(id)}
  if(!$('lx-chart'))return;
  var NS='http://www.w3.org/2000/svg', NUM=/^[-+]?(\d+\.?\d*|\.\d+)$/;
  var DEF={buf:'150',min:'50',d:'30',k:'4',w:'0',inflow:'120, 130, 140, 150, 150, 160, 160, 170, 170, 180, 180, 190',outflow:'150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150'};
  function one(id,name,lo,hi){
    var t=$(id).value.trim(); if(!NUM.test(t))throw name+' is not a number.';
    var v=Number(t); if(v<lo||v>hi)throw name+' must be between '+lo+' and '+hi+'.'; return v;
  }
  function list(id,name){
    var raw=$(id).value.split(/[\s,;]+/).filter(Boolean);
    if(raw.length!==12)throw name+' need exactly 12 values. Found '+raw.length+'.';
    return raw.map(function(t){if(!NUM.test(t))throw name+': "'+t+'" is not a number.'; var v=Number(t); if(v<0)throw name+' cannot be negative.'; return v});
  }
  function fmt(v){return (Math.round(v*10)/10).toLocaleString('en-GB',{minimumFractionDigits:1,maximumFractionDigits:1})}
  function clear(){
    for(var i=1;i<=6;i++)$('lx-o'+i).textContent='-';
    $('lx-rows').textContent=''; var s=$('lx-chart'); while(s.firstChild)s.removeChild(s.firstChild);
  }
  function el(n,a,txt){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;$('lx-chart').appendChild(e);return e}
  function draw(p,r){
    var s=$('lx-chart'); while(s.firstChild)s.removeChild(s.firstChild);
    var all=[p.buf,p.min,0].concat(r.base,r.str), lo=Math.min.apply(null,all), hi=Math.max.apply(null,all);
    if(hi===lo)hi=lo+1; var pad=(hi-lo)*0.08; lo-=pad; hi+=pad;
    var L=70,R=600,T=14,B=250;
    function X(i){return L+i*(R-L)/12} function Y(v){return B-(v-lo)/(hi-lo)*(B-T)}
    var step=Math.pow(10,Math.floor(Math.log10((hi-lo)/4))), m=(hi-lo)/4/step; step*=m<1.5?1:m<3.5?2:m<7.5?5:10;
    for(var v=Math.ceil(lo/step)*step;v<=hi;v+=step){
      el('line',{x1:L,y1:Y(v),x2:R,y2:Y(v),'class':'c-axis'});
      el('text',{x:L-8,y:Y(v)+5,'text-anchor':'end'},Math.round(v).toLocaleString('en-GB'));
    }
    for(var i=0;i<=12;i+=3)el('text',{x:X(i),y:B+26,'text-anchor':'middle'},i===0?'Start':'M'+i);
    el('line',{x1:L,y1:Y(p.min),x2:R,y2:Y(p.min),'class':'l-min'});
    function path(a){return 'M'+X(0).toFixed(1)+' '+Y(p.buf).toFixed(1)+a.map(function(v,i){return ' L'+X(i+1).toFixed(1)+' '+Y(v).toFixed(1)}).join('')}
    el('path',{d:path(r.base),'class':'l-base'}); el('path',{d:path(r.str),'class':'l-stress'});
  }
  function run(){
    var p, msg=$('lx-msg');
    try{
      p={buf:one('lx-buf','Opening buffer',0,1e12),min:one('lx-min','Minimum buffer',0,1e12),d:one('lx-d','Share paid late',0,100)/100,
         k:parseInt($('lx-k').value,10),w:one('lx-w','Share withdrawn',0,100)/100,inflow:list('lx-in','Inflows'),outflow:list('lx-out','Outflows')};
    }catch(e){clear();msg.textContent='Nothing was calculated. '+e;return}
    var r=lxCompute(p), nums=r.base.concat(r.str,[r.low,r.extra,r.late,r.beyond]);
    if(nums.some(function(x){return !isFinite(x)})){clear();msg.textContent='Nothing was calculated. The values entered do not give a finite result.';return}
    $('lx-o1').textContent=r.firstBase?'Month '+r.firstBase:'None';
    $('lx-o2').textContent=r.firstStress?'Month '+r.firstStress:'None';
    $('lx-o3').textContent=fmt(r.low); $('lx-o4').textContent=fmt(r.extra); $('lx-o5').textContent=fmt(r.late); $('lx-o6').textContent=fmt(r.beyond);
    var tb=$('lx-rows'); tb.textContent='';
    for(var i=0;i<12;i++){
      var tr=document.createElement('tr'), cells=['Month '+(i+1),fmt(r.si[i]),fmt(r.so[i]),fmt(r.base[i]),fmt(r.str[i])];
      cells.forEach(function(c,j){var td=document.createElement(j?'td':'th'); if(j)td.className='num'; else td.scope='row'; td.textContent=c; tr.appendChild(td)});
      tb.appendChild(tr);
    }
    draw(p,r);
    msg.textContent=p.buf<p.min?'The opening buffer is already below the minimum.':'';
  }
  function reset(){$('lx-buf').value=DEF.buf;$('lx-min').value=DEF.min;$('lx-d').value=DEF.d;$('lx-k').value=DEF.k;$('lx-w').value=DEF.w;$('lx-in').value=DEF.inflow;$('lx-out').value=DEF.outflow;run()}
  ['lx-buf','lx-min','lx-d','lx-w','lx-in','lx-out'].forEach(function(id){$(id).addEventListener('input',run)});
  $('lx-k').addEventListener('change',run); $('lx-reset').addEventListener('click',reset);
  run();
})()}
