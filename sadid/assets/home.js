(function(){
  // Left tail of two densities, x in standard deviations.
  var svg=document.getElementById('tail'), NS='http://www.w3.org/2000/svg';
  var x0=-6, x1=-2.2, yMax=0.036, L=44, R=546, T=24, B=250;
  function X(x){return L+(x-x0)/(x1-x0)*(R-L)}
  function Y(y){return B-Math.min(y,yMax)/yMax*(B-T)}
  function normal(x){return Math.exp(-x*x/2)/Math.sqrt(2*Math.PI)}
  function t3(x){return 2/Math.PI/Math.pow(1+x*x,2)} // Student-t, 3 d.f., rescaled to unit variance
  function el(n,a,txt){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;svg.appendChild(e);return e}
  var pn=[],pt=[],i,x;
  var gn=[],gt=[];
  for(i=0;i<=110;i++){x=x0+(x1-x0)*i/110;pn.push([X(x),Y(normal(x))]);pt.push([X(x),Y(t3(x))]);if(t3(x)>normal(x)){gn.push(pn[i]);gt.push(pt[i])}}
  function line(p){return p.map(function(q,j){return (j?'L':'M')+q[0].toFixed(1)+' '+q[1].toFixed(1)}).join(' ')}
  // Shaded gap between the curves
  var gap=line(gt)+' '+gn.slice().reverse().map(function(q){return 'L'+q[0].toFixed(1)+' '+q[1].toFixed(1)}).join(' ')+' Z';
  el('path',{d:gap,'class':'c-gap'});
  el('line',{x1:L,y1:B,x2:R,y2:B,'class':'c-axis'});
  for(i=-6;i<=-3;i++){
    el('line',{x1:X(i),y1:B,x2:X(i),y2:B+5,'class':'c-axis'});
    el('text',{x:X(i),y:B+19,'text-anchor':'middle','class':'c-text'},i+'σ');
  }
  el('text',{x:L,y:B+40,'class':'c-text'},'Daily return, in standard deviations');
  // 99% VaR under the normal model
  var v=-2.326;
  el('line',{x1:X(v),y1:T+14,x2:X(v),y2:B,'class':'c-var'});
  el('text',{x:X(v)-6,y:T+10,'text-anchor':'end','class':'c-text acc'},'1% quantile, normal model');
  el('path',{d:line(pn),'class':'c-normal'});
  el('path',{d:line(pt),'class':'c-heavy'});
  el('text',{x:X(-4.2),y:Y(t3(-4.2))-12,'text-anchor':'middle','class':'c-text tl'},'Heavy-tailed model');
  el('text',{x:X(-2.62),y:Y(0.027),'text-anchor':'end','class':'c-text'},'Normal model');


  function $(id){return document.getElementById(id)}
  // ---- Contact form: sends through Web3Forms once an access key is set ----
  var CF_KEY='';   // paste the Web3Forms access key between the quotes
  var cform=$('cform'), cmsg=$('cf-msg'), csend=$('cf-send');
  if(CF_KEY){$('cf-pending').hidden=true}else{csend.disabled=true}
  cform.addEventListener('submit',function(e){
    e.preventDefault();
    if(!CF_KEY){cmsg.textContent='The form is not connected yet, so nothing was sent.';return}
    if($('cf-bot').checked)return;
    var need=[['cf-name','your name'],['cf-subject','a subject'],['cf-message','a message'],['cf-email','your email address']];
    for(var i=0;i<need.length;i++){if(!$(need[i][0]).value.trim()){cmsg.textContent='Please enter '+need[i][1]+'.';$(need[i][0]).focus();return}}
    if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test($('cf-email').value.trim())){cmsg.textContent='Please check the email address.';$('cf-email').focus();return}
    var body={access_key:CF_KEY,from_name:'Sadid website',subject:'['+$('cf-topic').value+'] '+$('cf-subject').value.trim(),topic:$('cf-topic').value,
      name:$('cf-name').value.trim(),email:$('cf-email').value.trim(),phone:$('cf-phone').value.trim(),message:$('cf-message').value.trim()};
    csend.disabled=true; cmsg.textContent='Sending...';
    fetch('https://api.web3forms.com/submit',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(body)})
      .then(function(r){return r.json().then(function(j){return {ok:r.ok&&j.success,j:j}})})
      .then(function(x){
        if(x.ok){cform.reset();cmsg.textContent='Thank you. Your message has been sent.'}
        else{cmsg.textContent='Your message could not be sent. Please try again in a moment.'}
        csend.disabled=false})
      .catch(function(){cmsg.textContent='Your message could not be sent. Check your connection and try again.';csend.disabled=false});
  });
})();
