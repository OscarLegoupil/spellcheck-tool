const $ = id => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem('spellcheck-token') || '';
if (token) sessionStorage.setItem('spellcheck-token', token);
history.replaceState(null, '', location.pathname);
const jobs = [];
let active = null;
let ignoredRules = [];
const escapeHtml = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
async function api(path, options = {}) {
  const headers = {...options.headers, Authorization: `Bearer ${token}`};
  const response = await fetch(path, {...options, headers});
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try { message = (await response.json()).detail || message; } catch {}
    throw new Error(typeof message === 'string' ? message : 'Invalid request.');
  }
  return response;
}
function settings() {
  const terminology = {};
  for (const line of $('terms').value.split('\n')) {
    const i = line.indexOf('=');
    if (i > 0 && line.slice(i + 1).trim()) terminology[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return {language:$('language').value, english:$('english').value, thorough:$('mode').value === 'thorough',
    glossary:$('glossary').value.split('\n').map(s=>s.trim()).filter(Boolean), terminology,
    ignore_uppercase:$('uppercase').checked, ignore_codes:$('codes').checked, ignore_rules:ignoredRules};
}
function applyProfile(p) {
  $('language').value = ['fi','en','mixed'].includes(p.language) ? p.language : 'mixed';
  $('english').value = p.english === 'en-US' ? 'en-US' : 'en-GB';
  $('mode').value = p.thorough === false ? 'standard' : 'thorough';
  $('glossary').value = (p.glossary || []).join('\n');
  $('terms').value = Object.entries(p.terminology || {}).map(([k,v])=>`${k} = ${v}`).join('\n');
  $('uppercase').checked = p.ignore_uppercase !== false;
  $('codes').checked = p.ignore_codes !== false;
  ignoredRules = p.ignore_rules || [];
}
function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 2000);
}
$('save-profile').onclick = () => saveBlob(new Blob([JSON.stringify(settings(),null,2)], {type:'application/json'}), 'proofreading-profile.json');
$('profile').onchange = async event => { try {applyProfile(JSON.parse(await event.target.files[0].text()));notice('');} catch {notice('This profile could not be read. Choose a valid JSON profile.');} };
$('files').onchange = () => { $('file-list').textContent = [...$('files').files].map(f=>f.name).join(' · '); };
['dragenter','dragover'].forEach(name=>$('drop').addEventListener(name,()=> $('drop').classList.add('drag')));
['dragleave','drop'].forEach(name=>$('drop').addEventListener(name,()=> $('drop').classList.remove('drag')));

function current() {return jobs.find(j=>j.id===active);}
function renderTabs() {
  $('empty').hidden = jobs.length > 0; $('reviews').hidden = jobs.length === 0;
  $('tabs').replaceChildren(...jobs.map(j=>{
    const button = document.createElement('button');button.textContent=j.filename;
    button.className=j.id===active?'active':'';button.onclick=()=>{active=j.id;renderTabs();render();};return button;
  }));
}
function selected(job) {return job.result.findings.filter(f=>f.selected && f.suggestions.length);}
function updateCount() {
  const node=$('selection-count');if(node)node.textContent=`${selected(current()).length} selected`;
}
function context(segment, finding) {
  const a=Math.max(0,finding.start-85),b=Math.min(segment.text.length,finding.end+85);
  return `${a?'…':''}${escapeHtml(segment.text.slice(a,finding.start))}<mark>${escapeHtml(finding.original)}</mark>${escapeHtml(segment.text.slice(finding.end,b))}${b<segment.text.length?'…':''}`;
}
function renderFindings() {
  const job=current(),r=job.result,category=$('category').value;
  const segments=Object.fromEntries(r.segments.map(s=>[s.id,s]));
  const findings=r.findings.filter(f=>category==='all'||f.category===category||(category==='unresolved'&&!f.suggestions.length));
  $('findings').innerHTML = findings.map(f=>{
    const segment=segments[f.segment_id];
    return `<article class="finding ${f.selected?'':'off'}" data-id="${f.id}">
      <input aria-label="Include this correction" type="checkbox" ${f.selected?'checked':''} ${f.suggestions.length?'':'disabled'}>
      <div><div class="finding-top"><span>${escapeHtml(segment.location)} · ${segment.language==='fi'?'FI':'EN'}</span><span class="badge">${escapeHtml(f.category)}</span></div>
      <p class="context">${context(segment,f)}</p>
      <div class="replacement">${f.suggestions.length?`<span>→</span><select aria-label="Correction">${f.suggestions.map(s=>`<option ${s===f.correction?'selected':''}>${escapeHtml(s)}</option>`).join('')}</select>`:'<span class="muted">No reliable correction available · review only</span>'}</div>
      <details><summary>Details & preferences</summary><p>${escapeHtml(f.message||f.rule.replaceAll('_',' ').toLowerCase())}</p><p>${escapeHtml(f.engine)} · ${escapeHtml(f.rule)}</p>${f.category==='spelling'?'<button type="button" data-action="accept">Accept this word</button>':''}<button type="button" data-action="rule">Ignore this rule</button></details>
      </div></article>`;
  }).join('') || '<div class="complete-empty">No findings in this category.</div>';
  for (const node of $('findings').querySelectorAll('.finding')) {
    const finding=r.findings.find(f=>f.id===node.dataset.id);
    node.querySelector('input').onchange=e=>{finding.selected=e.target.checked;node.classList.toggle('off',!finding.selected);updateCount();};
    const select=node.querySelector('select');if(select)select.onchange=e=>{finding.correction=e.target.value;};
    node.querySelector('[data-action="rule"]').onclick=()=>{
      ignoredRules=[...new Set([...ignoredRules,finding.rule])];
      for(const f of r.findings)if(f.rule===finding.rule)f.selected=false;
      renderFindings();updateCount();
    };
    const accept=node.querySelector('[data-action="accept"]');if(accept)accept.onclick=()=>{
      $('glossary').value=[...new Set([...$('glossary').value.split('\n'),finding.original])].filter(Boolean).join('\n');
      for(const f of r.findings)if(f.category==='spelling'&&f.original.toLocaleLowerCase()===finding.original.toLocaleLowerCase())f.selected=false;
      renderFindings();updateCount();
    };
  }
}
function render() {
  const job=current();if(!job)return;
  if(job.state==='failed') {
    $('result').innerHTML=`<div class="progress"><h2>Review could not finish</h2><p>${escapeHtml(job.error)}</p><button class="secondary" id="remove">Remove review</button></div>`;
    $('remove').onclick=removeCurrent;return;
  }
  if(job.state!=='complete') {
    $('result').innerHTML=`<div class="progress"><p class="eyebrow">${job.state==='queued'?'QUEUED':'CHECKING'}</p><h2>${escapeHtml(job.filename)}</h2><progress ${job.total?`value="${job.done}" max="${job.total}"`:''}></progress><p>${job.total?`${job.done} / ${job.total} text sections · ${escapeHtml(job.location)}`:'Preparing the document and starting engines…'}</p><button class="secondary" id="cancel">Cancel review</button></div>`;
    $('cancel').onclick=()=>api(`/api/reviews/${job.id}`,{method:'DELETE'});return;
  }
  const r=job.result,unresolved=r.findings.filter(f=>!f.suggestions.length).length;
  $('result').innerHTML=`<div class="result-head"><p class="eyebrow">REVIEW COMPLETE</p><h2>${escapeHtml(job.filename)}</h2>
    <div class="metrics"><span><b>${r.findings.length}</b>possible issues</span><span><b>${r.segments.length}</b>sections checked</span><span><b>${unresolved}</b>without a correction</span></div>
    ${r.warnings.length?`<details class="coverage"><summary>${r.warnings.length} coverage ${r.warnings.length===1?'notice':'notices'}</summary><ul>${r.warnings.map(w=>`<li>${escapeHtml(w)}</li>`).join('')}</ul></details>`:''}
    <div class="actions"><button class="primary" id="download">Download annotated ${r.kind==='pdf'?'PDF':'Word'}</button><button class="secondary" id="report">Export review data</button><button class="secondary" id="remove">Remove</button></div>
    <div class="filters"><select id="category" aria-label="Filter findings"><option value="all">All findings</option><option value="spelling">Spelling</option><option value="grammar">Grammar</option><option value="typography">Typography</option><option value="terminology">Terminology</option><option value="unresolved">Without correction</option></select><button class="secondary" id="clear">Clear selection</button><span id="selection-count"></span></div></div><div id="findings"></div>`;
  $('category').onchange=renderFindings;
  $('clear').onclick=()=>{r.findings.forEach(f=>f.selected=false);renderFindings();updateCount();};
  $('remove').onclick=removeCurrent;
  $('report').onclick=()=>saveBlob(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}),job.filename+'.review.json');
  $('download').onclick=async()=>{
    const button=$('download');button.disabled=true;notice('');
    try {
      const choices=selected(job).map(f=>({id:f.id,correction:f.correction||f.suggestions[0]}));
      const response=await api(`/api/reviews/${job.id}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({choices})});
      const name=job.filename.replace(/\.(pdf|docx)$/i,'_reviewed.$1');saveBlob(await response.blob(),name);
    }catch(e){notice(e.message);}finally{button.disabled=false;}
  };
  renderFindings();updateCount();
}
async function removeCurrent() {
  const job=current();await api(`/api/reviews/${job.id}`,{method:'DELETE'});
  jobs.splice(jobs.indexOf(job),1);active=jobs[0]?.id;renderTabs();if(active)render();
}
async function poll(job) {
  while(!['complete','failed'].includes(job.state)) {
    await new Promise(resolve=>setTimeout(resolve,800));
    try {
      Object.assign(job,await (await api(`/api/reviews/${job.id}`)).json());
      if(job.result)job.result.findings.forEach(f=>{f.correction=f.suggestions[0]||'';});
      if(active===job.id)render();
    } catch(e){job.state='failed';job.error=e.message;if(active===job.id)render();}
  }
}
$('form').onsubmit=async event=>{
  event.preventDefault();notice('');$('run').disabled=true;
  try {
    for(const file of $('files').files) {
      const body=new FormData();body.append('file',file);body.append('settings',JSON.stringify(settings()));
      const job=await (await api('/api/reviews',{method:'POST',body})).json();job.state='queued';jobs.push(job);active=job.id;renderTabs();render();poll(job);
    }
    $('files').value='';$('file-list').textContent='';
  }catch(e){notice(e.message);}finally{$('run').disabled=false;}
};
api('/api/status').then(r=>r.json()).then(s=>{
  $('engine-status').textContent=`Finnish ${s.engines.finnish?'✓ ready':'— run Setup.cmd'} · English ${s.engines.english?'✓ ready':'— run Setup.cmd'}`;
}).catch(e=>notice(e.message));
