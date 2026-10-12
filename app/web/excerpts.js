'use strict';
let excerptMeta=null, excerptResult=null, excerptPage=1, excerptRequest=0;
let excerptFilters={q:'',themes:'',moods:'',appeals:'',visuals:'',stage:'',method:'',uses:''};
const excerptBasket=new Map();
let pendingQuotes=[];
const excerptLabels={themes:'内容主题',moods:'意境感受',appeals:'共鸣切入点',visuals:'画面元素',uses:'片段用途'};
function excerptSelect(key,label){
  return `<label>${label}<select data-excerpt-filter="${key}" aria-label="${label}"><option value="">全部</option>${Object.entries(excerptMeta[key]).sort((a,b)=>a[0].includes('待细分')-b[0].includes('待细分')||b[1]-a[1]).map(([n,c])=>`<option value="${esc(n)}" ${excerptFilters[key]===n?'selected':''}>${esc(n)} · ${c.toLocaleString()}</option>`).join('')}</select></label>`;
}
async function renderExcerpts(){
  const request=++excerptRequest;
  $('#detail').hidden=true;
  $('#content').innerHTML='<p class="loading">正在读取本地摘句分类…</p>';
  if(!excerptMeta)excerptMeta=await api('/api/excerpts/meta');
  if(request!==excerptRequest||view!=='excerpts')return;
  $('#excerpt-count').textContent=excerptMeta.excerpts.toLocaleString();
  $('#content').innerHTML=`<section class="library-heading"><div><h1>按意境挑句子</h1><p>${excerptMeta.poems.toLocaleString()}条资料已处理 · ${excerptMeta.excerpts.toLocaleString()}个原文片段 · 可以跨作品组一期</p></div></section>
    <p class="discovery-note">主题、意境与共鸣均是分类提案；“共鸣”表示创作切入点，不是热度排名。先看句子与前后文，再决定画面。</p>
    <div class="excerpt-filters"><input id="excerpt-search" aria-label="搜索原句或作者" placeholder="搜索原句、作品或作者" value="${esc(excerptFilters.q)}">
    ${['themes','moods','appeals'].map(key=>excerptSelect(key,excerptLabels[key])).join('')}</div>
    <div class="excerpt-more-row"><details class="excerpt-more"><summary>更多筛选：画面、用途、学段、分类方法</summary><div class="excerpt-filters">
    ${['visuals','uses'].map(key=>excerptSelect(key,excerptLabels[key])).join('')}
    <label>学段<select data-excerpt-filter="stage" aria-label="选句学段"><option value="">全部</option>${['小学','初中','高中','课外'].map(n=>`<option ${excerptFilters.stage===n?'selected':''}>${n}</option>`).join('')}</select></label>
    <label>分类方法<select data-excerpt-filter="method" aria-label="分类方法"><option value="">全部</option>${Object.entries(excerptMeta.methods).map(([n,c])=>`<option ${excerptFilters.method===n?'selected':''} value="${n}">${n} · ${c.toLocaleString()}</option>`).join('')}</select></label></div></details><button id="clear-excerpt-filters">清除条件</button></div>
    <div id="excerpt-basket"></div><div id="excerpt-result"></div>`;
  renderBasket();await fetchExcerpts();
}
function renderBasket(){
  const node=$('#excerpt-basket');if(!node)return;
  node.innerHTML=`<div class="basket-bar"><span>选句篮 <b>${excerptBasket.size}</b><small>按选择顺序组镜；加入一期后才写入项目</small></span><div><button id="review-basket" ${excerptBasket.size?'':'disabled'}>查看已选</button> <button class="primary" id="add-basket" ${excerptBasket.size?'':'disabled'}>加入一期作品</button></div></div>`;
}
async function fetchExcerpts(){
  const request=++excerptRequest;
  const query=new URLSearchParams({...excerptFilters,page:String(excerptPage)});
  const result=await api('/api/excerpts?'+query);
  if(request!==excerptRequest||view!=='excerpts')return;
  excerptResult=result;excerptPage=result.page;
  $('#excerpt-result').innerHTML=`<div class="result-bar"><span>${result.total.toLocaleString()}个匹配片段</span><span>精读提案优先 · 每页40条</span></div><div class="excerpt-list">${result.rows.map(r=>`<article class="excerpt-row"><label class="excerpt-check"><input type="checkbox" data-excerpt-check="${esc(r.id)}" ${excerptBasket.has(r.id)?'checked':''} aria-label="选择 ${esc(r.quote)}"></label><div class="excerpt-main"><button class="excerpt-quote" data-excerpt-open="${esc(r.id)}">${esc(r.quote)}</button><p class="excerpt-source">《${esc(r.title)}》 · ${esc(r.author)} · ${esc(r.stage)} <span>${esc(r.method)}</span></p><p class="excerpt-tags"><b>${r.moods.map(esc).join(' / ')}</b><span>${r.themes.map(esc).join(' / ')}</span></p><p class="excerpt-appeal">可聊：${r.appeals.map(esc).join(' · ')}</p>${r.cautions.length?`<p class="excerpt-caution">${esc(r.cautions[0])}</p>`:''}</div><button data-excerpt-open="${esc(r.id)}" class="excerpt-read">看上下文</button></article>`).join('')||'<p class="empty">没有匹配片段，请减少筛选条件。</p>'}</div><div class="pagination"><span>共${result.pages}页</span><div><button id="excerpt-prev" ${result.page===1?'disabled':''}>上一页</button><span>${result.page} / ${result.pages}</span><button id="excerpt-next" ${result.page===result.pages?'disabled':''}>下一页</button></div></div>`;
}
function findExcerpt(id){return excerptBasket.get(id)||excerptResult?.rows.find(r=>r.id===id);}
function showExcerpt(row){
  showPoem(row.poemId);
  $('#quote').value=row.quote;
  const panel=document.createElement('section');panel.className='excerpt-analysis';
  panel.innerHTML=`<strong>${esc(row.method)} · 待复核</strong><blockquote>${esc(row.quote)}</blockquote><p>主题：${row.themes.map(esc).join(' / ')}<br>意境：${row.moods.map(esc).join(' / ')}<br>共鸣提案：${row.appeals.map(esc).join(' / ')}</p><p>${esc(row.note)}</p><p>${row.cautions.map(esc).join('；')}</p><details><summary>分类依据</summary>${row.evidence.map(e=>`<p>${esc(e.dimension)} · ${esc(e.label)}：${esc(e.match)}</p>`).join('')||'<p>当前没有足够依据，保留待细分。</p>'}</details><button data-choose-excerpt="${esc(row.id)}">${excerptBasket.has(row.id)?'已在选句篮':'放入选句篮'}</button>`;
  $('#source-text').before(panel);
  const p=poem(row.poemId);const context=p.text.slice(Math.max(0,row.start-100),Math.min(p.text.length,row.end+100));
  panel.insertAdjacentHTML('beforeend',`<details><summary>附近原文</summary><pre>${esc(context)}</pre></details>`);
}
function openBatchModal(){
  pendingQuotes=Array.from(excerptBasket.values()).map(r=>({id:r.poemId,text:r.quote}));
  newEpisodeModal(pendingQuotes[0]);
  const f=$('#episode-form');f.dataset.batch='true';
  $('.notice',f).textContent=pendingQuotes.map((q,i)=>`${i+1}. ${q.text} ——《${poem(q.id).title}》`).join('\n');
  $('h2',$('#dialog')).textContent=`把${pendingQuotes.length}条摘句加入同一期`;
}
document.addEventListener('change',event=>{
  const t=event.target;
  if(t.dataset.excerptFilter){excerptFilters[t.dataset.excerptFilter]=t.value;excerptPage=1;fetchExcerpts().catch(e=>notify(e.message,true));}
  if(t.dataset.excerptCheck){const r=findExcerpt(t.dataset.excerptCheck);if(t.checked)excerptBasket.set(r.id,r);else excerptBasket.delete(r.id);renderBasket();}
});
let excerptSearchTimer;
document.addEventListener('input',event=>{if(event.target.id==='excerpt-search'){excerptFilters.q=event.target.value;excerptPage=1;clearTimeout(excerptSearchTimer);excerptSearchTimer=setTimeout(()=>fetchExcerpts().catch(e=>notify(e.message,true)),180);}});
document.addEventListener('click',async event=>{
  const b=event.target.closest('button');if(!b)return;
  try{
    if(b.dataset.excerptOpen){if(guard())showExcerpt(findExcerpt(b.dataset.excerptOpen));return;}
    if(b.dataset.chooseExcerpt){const r=findExcerpt(b.dataset.chooseExcerpt);excerptBasket.set(r.id,r);b.textContent='已在选句篮';renderBasket();const c=document.querySelector(`[data-excerpt-check="${CSS.escape(r.id)}"]`);if(c)c.checked=true;return;}
    if(b.dataset.removeExcerpt){excerptBasket.delete(b.dataset.removeExcerpt);renderBasket();closeModal();await fetchExcerpts();return;}
    if(b.id==='review-basket'){modal('当前已选句子',Array.from(excerptBasket.values()).map((r,i)=>`<p>${i+1}. ${esc(r.quote)}<br><small>《${esc(r.title)}》 ${esc(r.author)}</small> <button data-remove-excerpt="${esc(r.id)}">移出选句篮</button></p>`).join(''));}
    if(b.id==='add-basket'&&guard())openBatchModal();
    if(b.id==='clear-excerpt-filters'){excerptFilters=Object.fromEntries(Object.keys(excerptFilters).map(k=>[k,'']));excerptPage=1;await renderExcerpts();}
    if(b.id==='excerpt-prev'||b.id==='excerpt-next'){excerptPage+=b.id==='excerpt-prev'?-1:1;await fetchExcerpts();$('#excerpt-result')?.scrollIntoView({block:'start'});}
  }catch(e){notify(e.message,true);}
});
