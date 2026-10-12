'use strict';
const $ = (s, root=document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const uid = () => crypto.randomUUID();
let library=[], meta, searchIndex=new Map(), snapshot, view='excerpts', selected=null, episodeId=null, lastEpisodeId=null, dirty=false;
const emptyFilters=()=>({search:'',stage:'',genre:'',review:'',collection:'',schoolCore:false,scene:'',imagery:'',season:'',emotion:''});
let filters=emptyFilters(), page=1;
let toastTimer;
async function api(path, options={}) {
  const response=await fetch(path, {...options, headers:{'X-FilmOS':'local',...options.headers}});
  const result=await response.json();
  if(!response.ok) throw new Error(result.error || '操作失败');
  return result;
}
function notify(message, error=false){ const node=$('#toast'); node.textContent=message; node.className=error?'error':''; node.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>node.hidden=true,error?12000:4000); }
function guard(){if(!dirty) return true; if(confirm('当前输入尚未保存。放弃这些输入并继续？')){dirty=false;return true;} return false;}
async function reload(){if(!guard())return; [library,snapshot,meta]=await Promise.all([api('/api/library'),api('/api/state'),api('/api/meta')]);searchIndex=new Map(library.map(p=>[p.id,[p.title,p.author,p.text,p.id,...p.collections].join(' ').toLowerCase()]));render();if(selected)showPoem(selected);}
async function save(change){const data=structuredClone(snapshot.data);change(data);snapshot=await api('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:snapshot.version,data})});dirty=false;render();notify('已保存到本地项目');}
function tags(p){return snapshot.data.classifications[p.id] || {...p.draft, notes:'', review:'draft'};}
function episode(){return snapshot.data.episodes.find(e=>e.id===episodeId);}
function poem(id){return library.find(p=>p.id===id);}
function usage(id){return snapshot.data.episodes.filter(e=>e.shots.some(s=>s.poemId===id&&s.included!==false)).length;}
function render(){
  $('#library-count').textContent=library.length;
  $('#active-count').textContent=snapshot.data.episodes.filter(e=>e.status==='active').length;
  $('#archive-count').textContent=snapshot.data.episodes.filter(e=>e.status==='archived').length;
  document.querySelectorAll('[data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav===view));
  if(view==='excerpts') renderExcerpts().catch(e=>notify(e.message,true)); else if(view==='library') renderLibrary(); else if(episodeId && episode())renderEpisode();else renderEpisodes();
}
function renderLibrary(){
  const counts=meta.stages;
  $('#content').innerHTML=`<section class="library-heading"><div><h1>古诗文资料库</h1><p>${meta.total.toLocaleString()} 条收录记录 · 课标教材与课外典籍分开检索</p></div><button id="new-episode" class="primary">新建一期</button></section>
  <div class="scope-tabs">${[['全部','',meta.total],['小学','小学',counts['小学']||0],['初中','初中',counts['初中']||0],['高中','高中',counts['高中']||0],['课外典籍','课外',counts['课外']||0]].map(([name,val,num])=>`<button data-stage="${val}" class="scope-tab ${filters.stage===val&&!filters.schoolCore?'active':''}">${name}<span>${num.toLocaleString()}</span></button>`).join('')}<button id="high-core" class="scope-tab ${filters.schoolCore?'active':''}">高中课标推荐<span>72</span></button></div>
  <div class="library-tools"><div class="search-row"><input id="search" aria-label="搜索诗词" placeholder="搜索篇名、作者或原句，例如：蜀道难、苏轼、明月" value="${esc(filters.search)}"><select id="collection" aria-label="典籍来源"><option value="">全部来源 / 典籍</option>${Object.entries(meta.collections).map(([n,c])=>`<option value="${esc(n)}" ${filters.collection===n?'selected':''}>${esc(n)} · ${c}</option>`).join('')}</select><select id="genre" aria-label="体裁"><option value="">全部体裁</option>${['诗','词','曲','文言文','辞赋','蒙学韵文'].map(x=>`<option ${filters.genre===x?'selected':''}>${x}</option>`).join('')}</select></div>
  <div class="facet-row">${[['scene','场景'],['imagery','意象'],['season','时令'],['emotion','情绪字词']].map(([key,cat])=>`<label>${cat}<select id="${key}" aria-label="${cat}线索"><option value="">不限</option>${meta.facets.filter(f=>f.category===cat).map(f=>`<option value="${esc(f.label)}" ${filters[key]===f.label?'selected':''}>${esc(f.label)} · ${f.count}</option>`).join('')}</select></label>`).join('')}<label>人工分类<select id="review" aria-label="分类状态"><option value="">不限</option>${[['unclassified','未人工分类'],['draft','草案待审'],['confirmed','我已确认']].map(([v,t])=>`<option value="${v}" ${filters.review===v?'selected':''}>${t}</option>`).join('')}</select></label><button id="clear-filters">清除筛选</button></div></div>
  <div class="discovery-note">文字线索用于找句子，可能包含比喻、否定或回忆。画面与意境需要结合上下文决定；扩展典籍尚未逐字校勘。</div>
  <div class="result-bar"><span id="result-count"></span><span>点篇名或原句查看全文、摘句</span></div>
  <div class="table-wrap"><table class="library-table"><thead><tr><th>篇目 / 作者</th><th>原句预览</th><th>文字线索</th><th>来源</th></tr></thead><tbody id="cards"></tbody></table></div><div id="pagination"></div>`;
  renderCards();
}
function matchingClue(p){
  for(const [key,cat] of [['scene','场景'],['imagery','意象'],['season','时令'],['emotion','情绪字词']]){
    if(filters[key]){const c=p.clues.find(c=>c.category===cat&&c.label===filters[key]);if(c)return c;}
  }
  return null;
}
function preview(p){
  const clue=matchingClue(p);if(clue)return clue.evidence;
  if(filters.search&&p.text.includes(filters.search)){
    const i=p.text.indexOf(filters.search);return p.text.slice(Math.max(0,i-25),i+90).replace(/\n/g,' ');
  }
  return p.text.replace(/^#+ .*$/gm,'').split('\n').filter(s=>s.trim()&&!s.startsWith('- ')).join(' ').slice(0,110);
}
function filteredRows(){
  const q=filters.search.trim().toLowerCase();
  return library.filter(p=>{
    const t=tags(p),has=Boolean(t.theme||t.scene||t.imagery||t.mood),review=has?t.review:'unclassified';
    if(filters.stage&&p.stage!==filters.stage)return false;
    if(filters.schoolCore&&!(p.stage==='高中'&&p.schoolCore))return false;
    if(filters.collection&&!p.collections.includes(filters.collection))return false;
    if(filters.genre&&p.genre!==filters.genre)return false;
    if(filters.review&&review!==filters.review)return false;
    if(q&&!searchIndex.get(p.id).includes(q)&&!Object.values(t).join(' ').toLowerCase().includes(q))return false;
    for(const [key,cat] of [['scene','场景'],['imagery','意象'],['season','时令'],['emotion','情绪字词']]){
      if(filters[key]&&!p.clues.some(c=>c.category===cat&&c.label===filters[key]))return false;
    }
    return true;
  });
}
function renderCards(){
  const rows=filteredRows(), pages=Math.max(1,Math.ceil(rows.length/50));page=Math.min(page,pages);
  $('#result-count').textContent=`${rows.length.toLocaleString()} 条结果${rows.length?' · '+((page-1)*50+1)+'–'+Math.min(page*50,rows.length):''}`;
  $('#cards').innerHTML=rows.slice((page-1)*50,page*50).map(p=>{
    const t=tags(p),used=usage(p.id),clue=matchingClue(p);
    const labels=clue?[clue,...p.clues.filter(c=>c!==clue)].slice(0,3):p.clues.slice(0,3);
    return `<tr class="${selected===p.id?'selected':''}"><td><button class="title-button" data-poem="${esc(p.id)}">${esc(p.title)}</button><div class="row-author">${esc(p.author)} <span>· ${esc(p.genre)}</span></div>${used?`<span class="used-count">${used} 期使用</span>`:''}</td><td><button class="quote-button" data-poem="${esc(p.id)}">${esc(preview(p))}</button></td><td class="clue-cell">${labels.map(c=>`<span class="plain-tag" title="${esc(c.evidence)}">${esc(c.label)}</span>`).join('')||'<span class="muted">—</span>'}${t.review==='confirmed'?'<small>人工分类已确认</small>':''}</td><td class="source-cell"><span>${p.stage==='课外'?esc(p.collections[0]||'课外'):esc(p.stage)}</span><small>${p.stage==='课外'?'课外扩展 · 待校勘':esc(p.scope)}</small></td></tr>`;
  }).join('')||'<tr><td colspan="4" class="no-results">没有匹配结果。可清除筛选，或减少组合条件。</td></tr>';
  $('#pagination').innerHTML=`<div class="pagination"><span>每页 50 条 · 共 ${pages} 页</span><div><button id="previous-page" ${page===1?'disabled':''}>上一页</button><span>${page} / ${pages}</span><button id="next-page" ${page===pages?'disabled':''}>下一页</button></div></div>`;
}
function showPoem(id){
  selected=id;const p=poem(id),t=tags(p); const node=$('#detail');node.hidden=false;
  node.innerHTML=`<div class="detail-head"><span>原文与摘句 · ${esc(id)}</span><button class="icon" id="close-detail" aria-label="关闭详情">×</button></div><h2>${esc(p.title)}</h2><div class="metadata">${esc(p.author)} · ${esc(p.stage)} · ${esc(p.scope)}</div><p class="source-note">${esc(p.collections.join(' / '))}</p><p class="source-note">${esc(p.notes||'')}</p>${p.curriculumSourceUrl&&/^https?:\/\//.test(p.curriculumSourceUrl)?`<a class="source-note" href="${esc(p.curriculumSourceUrl)}" target="_blank" rel="noreferrer">教学归属来源 ↗</a>`:''}<div class="source" id="source-text">${esc(p.text)}</div><div class="source-note">${esc(p.status)}</div><details><summary>原始记录与出处</summary><pre>${esc(p.sourceText)}</pre><p>${esc(p.sourcePath)}</p>${/^https?:\/\//.test(p.sourceUrl)?`<a href="${esc(p.sourceUrl)}" target="_blank" rel="noreferrer">查看文本来源 ↗</a>`:''}</details>
  <details class="text-clues"><summary>文字线索与命中原句（${p.clues.length}）</summary><p>仅供检索，不代表画面必须出现；注意否定、比喻与上下文。</p>${p.clues.map(c=>`<p><b>${esc(c.category)} · ${esc(c.label)}</b><br>${esc(c.evidence)}</p>`).join('')}</details><form id="quote-form"><div class="section-label">摘取这一期想用的句子</div><label for="quote">可选中上方文字，或复制原句到这里</label><textarea id="quote" name="quote" required placeholder="例如：孤舟蓑笠翁，独钓寒江雪。"></textarea><div class="actions"><button type="button" id="use-selection">填入选中文字</button><button class="primary" type="submit">加入一期作品 ＋</button></div></form>
  <form id="tags-form"><div class="section-label">分类与自己的理解</div><p class="source-note">标签用于找内容，不代表已确定画风。现有试分为助手草案。</p><div class="two">${[['theme','内容主题'],['scene','场景'],['imagery','意象'],['mood','情绪 / 意境']].map(([k,n])=>`<div><label for="tag-${k}">${n}</label><input id="tag-${k}" name="${k}" value="${esc(t[k]||'')}"></div>`).join('')}</div><label for="tag-notes">我的理解与备注</label><textarea id="tag-notes" name="notes">${esc(t.notes||'')}</textarea><label for="tag-review">分类状态</label><select id="tag-review" name="review"><option value="draft">草案待审</option><option value="confirmed" ${t.review==='confirmed'?'selected':''}>我已确认</option></select><div class="actions"><button class="primary">保存分类</button></div></form>`;
  if(view==='library')document.querySelectorAll('[data-poem]').forEach(b=>b.classList.toggle('selected',b.dataset.poem===id));
}
function renderEpisodes(){
  $('#detail').hidden=true;selected=null;
  const archived=view==='archive', list=snapshot.data.episodes.filter(e=>(e.status==='archived')===archived);
  $('#content').innerHTML=`<section class="hero"><h1>${archived?'作品存档':'制作中的作品'}</h1><p>${archived?'这里保留已完成的视频素材与制作记录。诗句仍然可以用于新的意境。':'按意境组织诗句，逐条完成图片、视频，最后交给剪辑师。'}</p>${!archived?'<button class="primary" id="new-episode">新建一期 ＋</button>':''}</section>`+
  (list.length?list.map(e=>`<button class="episode-card" data-episode="${esc(e.id)}"><div class="card-top"><span>${esc(e.mood||'意境待定')}</span><span>${e.status==='archived'?'素材已归档':'制作中'}</span></div><h3>${esc(e.title)}</h3><p>${e.shots.filter(s=>s.included!==false).length} 条诗句 · ${e.shots.filter(s=>s.included!==false&&s.videoId).length} 条已选视频　　查看制作记录 →</p></button>`).join(''):`<div class="empty"><div class="symbol">${archived?'藏':'序'}</div><h2>${archived?'还没有归档作品':'第一期，从一句喜欢的诗开始'}</h2><p>${archived?'每条诗句的视频准备好后，可以导出并归档。':'可以先去资料库选诗句，也可以先给这一期起个名字。'}</p>${!archived?'<button data-nav="library">去选诗句 →</button>':''}</div>`);
}
function mediaBox(shot, kind){
  const version=shot.versions.find(v=>v.id===shot[kind==='image'?'imageId':'videoId']);
  const label=kind==='image'?'采用图片':'采用视频';
  return `<div class="media-box">${label}${version?`${kind==='image'?`<img src="/api/media?path=${encodeURIComponent(version.path)}" alt="采用的诗句意境图片" loading="lazy">`:`<video controls preload="metadata" src="/api/media?path=${encodeURIComponent(version.path)}"></video>`}<small>${esc(version.model||'模型未知')}</small>`:'<p>等待选择采用版本</p>'}</div>`;
}
function renderEpisode(){
  const e=episode(),locked=e.status==='archived';$('#detail').hidden=true;selected=null;
  $('#content').innerHTML=`<section class="hero"><button class="back" id="back-episodes">← ${locked?'作品存档':'制作中的作品'}</button><div class="episode-top"><div><div class="eyebrow">${locked?'ARCHIVED · 视频素材已归档':'POETRY IN THE MAKING'}</div><h1>${esc(e.title)}</h1><p>${esc(e.mood||'意境待定')} · ${e.shots.filter(s=>s.included!==false).length} 条诗句 · ${e.shots.filter(s=>s.included!==false&&s.videoId).length} 条已选视频</p></div>${!locked?'<button id="edit-episode">编辑策划</button>':''}</div>${e.notes?`<p>${esc(e.notes)}</p>`:''}<div class="actions">${!locked?'<button data-nav="excerpts" class="primary">继续选诗句 ＋</button>':''}<button id="export">导出剪辑交付包 ↓</button>${!locked?'<button id="archive">完成素材并归档</button>':''}</div><div class="notice">${locked?'这一期已锁定留存，可随时导出视频素材。新的创作请另建一期。':'每句先做图，再按采用图片与目标模型写视频提示词。看图与生成在 Codex 中协作，配音、BGM 和剪辑后续处理。'}</div></section>`+
  (e.shots.map((s,i)=>`<article class="shot ${s.included===false?'excluded':''}"><div class="shot-head"><span class="shot-num">${String(i+1).padStart(2,'0')}</span><div class="shot-heading"><blockquote>${esc(s.quote)}</blockquote><span class="meta">${esc(poem(s.poemId).title)} · ${esc(poem(s.poemId).author)}</span></div>${!locked?`<div><button data-move="${s.id}" data-dir="-1" ${i===0?'disabled':''} aria-label="诗句上移">↑</button><button data-move="${s.id}" data-dir="1" ${i===e.shots.length-1?'disabled':''} aria-label="诗句下移">↓</button></div>`:''}</div><p class="idea">${esc(s.idea||'画面构想待补充')}</p>${!locked?`<button data-toggle="${s.id}">${s.included===false?'重新选入本期':'移回候选（保留记录）'}</button> <button data-idea="${s.id}">写画面构想</button>`:''}<div class="shot-grid">${mediaBox(s,'image')}${mediaBox(s,'video')}</div><div class="actions">${!locked?`<button class="primary" data-version="${s.id}" data-kind="image">记录生图迭代 ＋</button><button data-version="${s.id}" data-kind="video">记录视频迭代 ＋</button>`:''}<button data-request="${s.id}">整理 Codex 协作请求</button></div><details class="versions"><summary>查看 ${s.versions.length} 个历史版本 · 仅追加，不覆盖</summary>${s.versions.map((v,n)=>`<div class="version"><strong>${v.kind==='image'?'图片':'视频'} · V${n+1}　${esc(v.model||'模型未知')}</strong><pre>${esc(v.prompt)}</pre><div class="version-meta">参数：${esc(v.params||'未知')}<br>参考：${esc(v.reference||'未知')}<br>实际消耗：${esc(v.cost||'未知')}<br>结果与理由：${esc(v.reason||'待评估')}<br>素材：${esc(v.path||'尚无输出')}</div>${v.path?`<div class="actions"><a target="_blank" rel="noreferrer" href="/api/media?path=${encodeURIComponent(v.path)}">查看素材 ↗</a>${!locked?`<button data-adopt="${s.id}" data-vid="${v.id}" ${s.imageId===v.id||s.videoId===v.id?'disabled':''}>${s.imageId===v.id||s.videoId===v.id?'已采用':'采用这个版本'}</button>`:''}</div>`:''}</div>`).join('')||'<p class="source-note">还没有记录版本。</p>'}</details></article>`).join('')||'<div class="empty"><h2>为这一期选入第一句诗</h2><button data-nav="excerpts">打开意境选句 →</button></div>');
}
function modal(title, body){const d=$('#dialog');d.innerHTML=`<div class="dialog-top"><h2>${title}</h2><button class="icon" id="close-dialog" aria-label="关闭对话框">×</button></div>${body}`;d.showModal();}
function closeModal(){ $('#dialog').close(); }
function newEpisodeModal(quote=null){
  const existing=snapshot.data.episodes.filter(e=>e.status==='active');
  modal(quote?'把诗句加入一期':'新建一期作品',`<form id="episode-form" data-poem="${esc(quote?.id||'')}">${quote?`<p class="notice">${esc(quote.text)}</p><textarea name="quote" hidden>${esc(quote.text)}</textarea><label>加入哪一期</label><select name="existing"><option value="">新建一期</option>${existing.map(e=>`<option value="${e.id}" ${e.id===(episodeId||lastEpisodeId)?'selected':''}>${esc(e.title)}</option>`).join('')}</select>`:''}<div id="new-fields"><label for="ep-title">新一期的名称</label><input id="ep-title" name="title" placeholder="例如：一江烟雨"><label for="ep-mood">这一期的意境</label><input id="ep-mood" name="mood" placeholder="例如：烟雨、悠远、宁静"></div><div class="actions"><button class="primary">${quote?'加入并保存':'创建作品'}</button></div></form>`);
  const select=$('select[name=existing]');if(select)$('#new-fields').hidden=Boolean(select.value);
}
function versionModal(sid,kind){
  const s=episode().shots.find(x=>x.id===sid), image=s.versions.find(v=>v.id===s.imageId);
  modal(kind==='image'?'记录一次生图迭代':'记录一次视频迭代',`<form id="version-form" data-shot="${sid}" data-kind="${kind}"><p class="source-note">只记录这次实际输入与结果，不会调用模型。未知信息可留空。</p><label for="v-prompt">完整${kind==='image'?'生图':'图生视频'}提示词</label><textarea id="v-prompt" name="prompt" required placeholder="保存完整输入，方便继续调整和复现"></textarea><div class="two"><div><label for="v-model">模型 / 版本</label><input id="v-model" name="model" placeholder="未知"></div><div><label for="v-cost">本次实际消耗</label><input id="v-cost" name="cost" placeholder="未知；或次数、积分、金额"></div></div><label for="v-params">实际可见参数</label><input id="v-params" name="params" placeholder="画幅、时长等；未知可留空"><label for="v-reference">实际参考输入 / 看图分析</label><textarea id="v-reference" name="reference" placeholder="参考素材路径、使用方式或看图结论">${esc(kind==='video'&&image?image.path:'')}</textarea><label for="v-path">输出素材（可先仅保存提示词）</label><input id="v-path" name="path" placeholder="资产库/…；或通过下方按钮导入"><label for="v-file">导入本地${kind==='image'?'图片':'视频'} · 复制原件到项目</label><input id="v-file" type="file" accept="${kind==='image'?'.png,.jpg,.jpeg,.webp':'.mp4,.mov,.webm'}"><label for="v-reason">效果、问题与采用理由</label><textarea id="v-reason" name="reason" placeholder="哪里符合预期？下一版只调整什么？"></textarea><div class="actions"><button class="primary" id="save-version">保存为新版本</button></div></form>`);
}
function requestModal(sid){
  const e=episode(), s=e.shots.find(x=>x.id===sid),p=poem(s.poemId),im=s.versions.find(v=>v.id===s.imageId),last=s.versions.at(-1);
  const text=`请继续 FilmOS 古诗词项目。\n先读 AGENTS.md 和 doc/看板/使用说明.md。\n本期：${e.title}（${e.id}）；意境：${e.mood||'待定'}。\n诗句编号：${s.id}；来源：${p.id}《${p.title}》${p.author}\n原句：${s.quote}\n画面构想：${s.idea||'待讨论'}\n采用图片：${im?'doc/项目/01-古诗词意境/'+im.path:'尚未采用图片，请先协作确定生图提示词'}\n${im?'请实际查看采用图片，再结合图中主体、构图、可动元素和需要保持的部分，按我指定的视频模型编写图生视频提示词。目标模型未确定时先问清，不能声称已经适配。':'请基于原句上下文与本期意境，协作设计完整生图提示词；不要自动付费生成。'}\n最近记录：${last?JSON.stringify(last,null,2):'无'}\n需要保存时追加版本，保留历史；不要自动标为稳定配方或采用。`;
  modal('发到当前 Codex 对话',`<p class="notice">这里整理上下文；复制后发给 Codex 才会开始协作，不会自动调用模型。</p><textarea class="request-text" id="request-text" readonly>${esc(text)}</textarea><div class="actions"><button class="primary" id="copy-request">复制协作请求</button></div>`);
}
async function handleClick(event){
  const b=event.target.closest('button');if(!b)return;
  if(b.dataset.nav){if(!guard())return;if(episodeId)lastEpisodeId=episodeId;view=b.dataset.nav;episodeId=null;selected=null;$('#detail').hidden=true;render();return;}
  if(b.dataset.stage!==undefined){filters=emptyFilters();filters.stage=b.dataset.stage;page=1;renderLibrary();return;}
  if(b.dataset.poem){if(guard())showPoem(b.dataset.poem);return;}
  if(b.dataset.episode){if(!guard())return;episodeId=b.dataset.episode;render();return;}
  if(b.dataset.version){if(guard())versionModal(b.dataset.version,b.dataset.kind);return;}
  if(b.dataset.request){if(guard())requestModal(b.dataset.request);return;}
  if(b.dataset.toggle){await save(d=>{const s=d.episodes.find(e=>e.id===episodeId).shots.find(s=>s.id===b.dataset.toggle);s.included=s.included===false;});return;}
  if(b.dataset.adopt){await save(d=>{const s=d.episodes.find(e=>e.id===episodeId).shots.find(s=>s.id===b.dataset.adopt),v=s.versions.find(v=>v.id===b.dataset.vid);s[v.kind==='image'?'imageId':'videoId']=v.id;});return;}
  if(b.dataset.move){await save(d=>{const arr=d.episodes.find(e=>e.id===episodeId).shots,i=arr.findIndex(s=>s.id===b.dataset.move),j=i+Number(b.dataset.dir);[arr[i],arr[j]]=[arr[j],arr[i]];});return;}
  if(b.dataset.idea){const s=episode().shots.find(s=>s.id===b.dataset.idea);modal('这句诗的画面构想',`<form id="idea-form" data-shot="${s.id}"><label for="idea">画面、主体与需要保留的诗意</label><textarea id="idea" name="idea">${esc(s.idea)}</textarea><div class="actions"><button class="primary">保存构想</button></div></form>`);return;}
  switch(b.id){
    case 'reload':await reload();notify('已读取最新本地资料');break;
    case 'high-core':filters=emptyFilters();filters.schoolCore=true;filters.stage='高中';page=1;renderLibrary();break;
    case 'clear-filters':filters=emptyFilters();page=1;renderLibrary();break;
    case 'previous-page':page--;renderCards();break;
    case 'next-page':page++;renderCards();break;
    case 'close-detail':if(guard()){$('#detail').hidden=true;selected=null;}break;
    case 'use-selection':{const sel=window.getSelection();if(sel&&$('#source-text').contains(sel.anchorNode)&&sel.toString().trim()){$('#quote').value=sel.toString().trim();dirty=true;}else notify('请先在上方原文中选中文字');break;}
    case 'new-episode':if(guard())newEpisodeModal();break;
    case 'close-dialog':if(guard())closeModal();break;
    case 'back-episodes':if(guard()){episodeId=null;render();}break;
    case 'edit-episode':{const e=episode();modal('本期策划',`<form id="edit-form"><label>作品名称</label><input name="title" required value="${esc(e.title)}"><label>意境</label><input name="mood" value="${esc(e.mood)}"><label>统一画风与交付说明</label><textarea name="notes">${esc(e.notes)}</textarea><div class="actions"><button class="primary">保存策划</button></div></form>`);break;}
    case 'copy-request':await navigator.clipboard.writeText($('#request-text').value);notify('已复制，请发到当前 Codex 对话');break;
    case 'archive':if(confirm('确认每条采用的视频已准备好？归档后将保留这期记录，不能覆盖修改。')){await save(d=>d.episodes.find(e=>e.id===episodeId).status='archived');view='archive';render();}break;
    case 'export':{notify('正在整理采用的视频…');const response=await fetch('/api/export?id='+encodeURIComponent(episodeId));if(!response.ok)throw new Error((await response.json()).error);const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=`${episode().title.replace(/[\\/:*?"<>|]/g,'-')}-剪辑交付包.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);notify('交付包已生成，包含按顺序排列的视频和说明');break;}
  }
}
async function handleSubmit(event){
  const f=event.target;if(!f.matches('form'))return;event.preventDefault();const fields=Object.fromEntries(new FormData(f));
  if(f.id==='quote-form'){const q=fields.quote.trim(),p=poem(selected);if(!q||!p.text.replace(/\s/g,'').includes(q.replace(/\s/g,'')))throw new Error('请摘录对应原文中的连续诗句，并保留原文标点');dirty=false;newEpisodeModal({id:selected,text:q});return;}
  if(f.id==='tags-form'){await save(d=>d.classifications[selected]=fields);showPoem(selected);return;}
  if(f.id==='episode-form'){
    const id=fields.existing||uid();
    await save(d=>{let e=d.episodes.find(e=>e.id===id);if(!e){if(!fields.title.trim())throw new Error('请给新一期起个名字');e={id,title:fields.title.trim(),mood:fields.mood.trim(),notes:'',status:'active',shots:[]};d.episodes.push(e);}const quotes=f.dataset.batch?pendingQuotes:(f.dataset.poem?[{id:f.dataset.poem,text:fields.quote}]:[]);for(const q of quotes)e.shots.push({id:uid(),poemId:q.id,quote:q.text,idea:'',included:true,versions:[],imageId:'',videoId:''});});
    if(f.dataset.batch){excerptBasket.clear();pendingQuotes=[];}closeModal();episodeId=id;view='episodes';render();return;
  }
  if(f.id==='edit-form'){await save(d=>Object.assign(d.episodes.find(e=>e.id===episodeId),fields));closeModal();return;}
  if(f.id==='idea-form'){await save(d=>d.episodes.find(e=>e.id===episodeId).shots.find(s=>s.id===f.dataset.shot).idea=fields.idea);closeModal();return;}
  if(f.id==='version-form'){
    const record={id:uid(),kind:f.dataset.kind,...fields};
    for(const key of ['model','params','reference','cost','reason'])if(!record[key].trim())record[key]='未知';
    await save(d=>d.episodes.find(e=>e.id===episodeId).shots.find(s=>s.id===f.dataset.shot).versions.push(record));closeModal();return;
  }
}
document.addEventListener('click',event=>handleClick(event).catch(e=>notify(e.message,true)));
document.addEventListener('submit',event=>handleSubmit(event).catch(e=>notify(e.message,true)));
document.addEventListener('input',event=>{if(event.target.id==='search'){filters.search=event.target.value;page=1;renderCards();}else if(event.target.closest('form'))dirty=true;});
document.addEventListener('change',async event=>{
  const t=event.target;
  if(['collection','genre','review','scene','imagery','season','emotion'].includes(t.id)){filters[t.id]=t.value;page=1;renderCards();}
  if(t.name==='existing')$('#new-fields').hidden=Boolean(t.value);
  if(t.id==='v-file'&&t.files[0]){
    const button=$('#save-version');button.disabled=true;
    try{const file=t.files[0];if(file.size>200*1024*1024)throw new Error('文件超过200MB，请手动放入资产库，再填写相对路径');const result=await api('/api/assets?name='+encodeURIComponent(file.name),{method:'POST',body:file});$('#v-path').value=result.path;dirty=true;notify('素材已复制到本地资产库，请保存生成版本');}catch(e){notify(e.message,true);}finally{button.disabled=false;}
  }
});
$('#dialog').addEventListener('cancel',event=>{if(!guard())event.preventDefault();});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
reload().catch(e=>{$('#content').textContent='读取失败：'+e.message;notify(e.message,true);});
