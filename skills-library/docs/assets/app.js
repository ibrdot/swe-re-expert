/* Dependency-free, light-only skill explorer. Content is inserted as text, never HTML. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  async function copy(text, button) {
    const original = button.textContent;
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const field = document.createElement('textarea'); field.value = text;
        field.style.position = 'fixed'; field.style.opacity = '0'; document.body.append(field); field.select();
        const ok = document.execCommand('copy'); field.remove();
        if (!ok) throw new Error('Copy unavailable');
      }
      button.textContent = 'Copied';
      if ($('copy-status')) $('copy-status').textContent = 'Command copied.';
    } catch (_) {
      button.textContent = 'Copy failed';
      if ($('copy-status')) $('copy-status').textContent = 'Copy was blocked. Select and copy the command manually.';
    }
    setTimeout(() => { button.textContent = original; }, 1800);
  }
  document.querySelectorAll('[data-copy-target]').forEach(button => button.addEventListener('click', () => copy($(button.dataset.copyTarget).textContent, button)));
  if (!$('results')) return;
  const params = new URLSearchParams(location.search);
  const state = {sort:params.get('sort') || 'name', saved:params.get('saved') === '1', q:params.get('q') || '', collection:params.get('collection') || 'all', category:params.get('category') || ''};
  let saved = new Set();
  try { const stored=JSON.parse(localStorage.getItem('skill-library-saved') || '[]'); if(Array.isArray(stored)) saved=new Set(stored.filter(x=>typeof x==='string')); } catch (_) {}
  let all = [], limit = 40, filtered = [];
  const el = (tag, cls, text) => { const node = document.createElement(tag); if (cls) node.className = cls; if (text) node.textContent = text; return node; };
  function syncUrl() {
    const query = new URLSearchParams();
    if (state.sort !== 'name') query.set('sort',state.sort);
    if (state.saved) query.set('saved','1');
    if (state.q) query.set('q', state.q);
    if (state.collection !== 'all') query.set('collection', state.collection);
    if (state.category) query.set('category', state.category);
    history.replaceState(null, '', location.pathname + (query.size ? '?' + query.toString() : '') + location.hash);
  }
  function render() {
    const terms = state.q.toLowerCase().trim().split(/\s+/).filter(Boolean);
    filtered = all.filter(s => (state.collection === 'all' || s.collection === state.collection) && (!state.category || s.category === state.category) && terms.every(term => s.search.includes(term)) && (!state.saved || saved.has(s.id)));
    filtered.sort((a,b)=>state.sort==='name-desc'?b.name.localeCompare(a.name):state.sort==='category'?a.category.localeCompare(b.category)||a.name.localeCompare(b.name):a.name.localeCompare(b.name));
    $('saved-count').textContent=String(saved.size);
    $('saved-view').setAttribute('aria-pressed',String(state.saved)); $('all-view').setAttribute('aria-pressed',String(!state.saved));
    document.querySelectorAll('[data-category]').forEach(b=>b.setAttribute('aria-current',b.dataset.category===state.category?'true':'false'));
    $('results').replaceChildren();
    $('results').setAttribute('aria-busy','false');
    $('count').textContent = `${filtered.length.toLocaleString()} of ${all.length.toLocaleString()} guides`;
    if (!filtered.length) $('results').append(el('p','empty','No matching guides. Try a broader search or reset the filters.'));
    const fragment = document.createDocumentFragment();
    filtered.slice(0,limit).forEach(s => {
      const row=el('article','skill-row'), info=el('div','skill-info'), title=el('h2'), link=el('a','',s.name);
      link.href=s.url; title.append(link); info.append(title,el('span','badge',s.category));
      const desc=el('div','skill-desc'); desc.append(el('p','',s.description), el('div','path',s.skill_file));
      const button=el('button','path-copy','Copy path'); button.type='button'; button.setAttribute('aria-label',`Copy path for ${s.name}`);
      button.addEventListener('click',()=>copy(s.skill_file,button));
      const actions=el('div','row-actions'); actions.append(button);
      const detail=el('button','path-copy','Details'); detail.type='button'; detail.setAttribute('aria-label',`View details for ${s.name}`);detail.addEventListener('click',()=>showDetail(s));actions.append(detail);
      const save=el('button','path-copy',saved.has(s.id)?'Saved':'Save');save.type='button';save.setAttribute('aria-pressed',String(saved.has(s.id)));save.setAttribute('aria-label',`Save ${s.name}`);save.addEventListener('click',()=>{if(saved.has(s.id))saved.delete(s.id);else saved.add(s.id);try{localStorage.setItem('skill-library-saved',JSON.stringify([...saved]));}catch(_){}render();});actions.append(save);desc.append(actions);
      const open=el('a','row-link','↗'); open.href=s.url; open.setAttribute('aria-label',`Open ${s.name} guide on GitHub`);
      row.append(info,desc,open); fragment.append(row);
    });
    $('results').append(fragment); $('more').hidden=filtered.length<=limit;
    $('more').textContent=`Show ${Math.min(40, Math.max(0,filtered.length-limit))} more guides`;
    syncUrl();
  }
  function update() {state.sort=$('sort').value;state.q=$('q').value; state.collection=$('collection').value; state.category=$('category').value; limit=40;render();}
  $('sort').addEventListener('change',update);
  $('saved-view').addEventListener('click',()=>{state.saved=true;limit=40;render();});
  $('all-view').addEventListener('click',()=>{state.saved=false;limit=40;render();});
  function showDetail(s){$('detail-title').textContent=s.name;$('detail-category').textContent=s.category+' / '+s.collection_label;$('detail-description').textContent=s.description;$('detail-path').textContent=s.skill_file;$('detail-license').textContent=s.license;$('detail-source').href=s.url;$('detail-copy').onclick=()=>copy(s.skill_file,$('detail-copy'));$('skill-dialog').showModal();}
  $('close-detail').addEventListener('click',()=>$('skill-dialog').close());
  $('skill-dialog').addEventListener('click',e=>{if(e.target===$('skill-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('q').addEventListener('input', update); $('collection').addEventListener('change',update); $('category').addEventListener('change',update);
  $('reset').addEventListener('click',()=>{$('q').value='';$('collection').value='all';$('category').value='';$('sort').value='name';state.saved=false;update();$('q').focus();});
  $('more').addEventListener('click',()=>{const old=limit;limit+=40;render();const next=$('results').children[old];if(next) next.querySelector('a').focus();});
  document.addEventListener('keydown',e=>{if(e.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName) && !e.metaKey && !e.ctrlKey){e.preventDefault();$('q').focus();}if(e.key==='Escape'&&document.activeElement===$('q')){$('q').value='';update();}});
  fetch('api/v1/skills.json').then(r=>{if(!r.ok)throw new Error('Catalogue unavailable');return r.json();}).then(data=>{
    all=data.skills.map(s=>({...s,search:[s.name,s.description,s.path,s.category,s.collection_label].join(' ').toLowerCase()}));
    const every=el('button','','All workflows');every.type='button';every.dataset.category='';every.addEventListener('click',()=>{$('category').value='';update();});$('category-nav').append(every);
    Object.entries(data.categories).forEach(([name,count])=>{const opt=el('option','',`${name} (${count})`);opt.value=name;$('category').append(opt);const b=el('button','',name);b.type='button';b.dataset.category=name;b.append(el('span','',String(count)));b.addEventListener('click',()=>{$('category').value=name;update();});$('category-nav').append(b);});
    if(!Array.from($('collection').options).some(o=>o.value===state.collection))state.collection='all';
    if(!data.categories[state.category])state.category='';
    if(!['name','name-desc','category'].includes(state.sort))state.sort='name';$('sort').value=state.sort;
    $('q').value=state.q; $('collection').value=state.collection;$('category').value=state.category;render();
  }).catch(()=>{ $('results').setAttribute('aria-busy','false');$('count').textContent='Catalogue could not load'; const p=el('p','empty','Unable to load the catalogue. Reload this page, or open ');const a=el('a','','SKILLS.md on GitHub');a.href='https://github.com/ibrdot/ai-agent-skills/blob/main/SKILLS.md';p.append(a);$('results').replaceChildren(p);});
})();
