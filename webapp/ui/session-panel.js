let panelPoll, sessionSnapshot, activeStage, previewVersion, lastWorkflowStage, requestedStage;
const panelStages=['plan','style','design','powerpoint'];
function stageFromLocation(){if(typeof location==='undefined')return null;const value=location.hash.slice(1);return panelStages.includes(value)?value:null}
function rememberStage(stage){if(typeof location==='undefined')return;const url=new URL(location.href);url.hash=stage;history.replaceState(null,'',url)}
async function bootPanel(){await refreshOverview();requestedStage=stageFromLocation();const q=new URLSearchParams(location.search),id=q.get('panel'),legacy=q.get('run');if(id)state.panelBinding=await api(`/api/panel/binding?id=${encodeURIComponent(id)}`);else if(!legacy){state.panelBinding=await api('/api/panel/new',{});const u=new URL(location.href);u.searchParams.set('panel',state.panelBinding.id);history.replaceState(null,'',u)}const selected=state.panelBinding?.run||legacy;if(selected)try{state.run=await api(`/api/run?path=${encodeURIComponent(selected)}`)}catch(e){state.missingRun=e.message}await refreshPanel(true);schedulePanelPoll()}
function schedulePanelPoll(){clearTimeout(panelPoll);panelPoll=setTimeout(async()=>{try{if(!document.hidden){await syncPanelBinding();await refreshPanel()}}catch(_){}finally{schedulePanelPoll()}},1800)}
async function syncPanelBinding(){if(!state.panelBinding)return;const b=await api(`/api/panel/binding?id=${encodeURIComponent(state.panelBinding.id)}`);state.panelBinding=b;if(!b.run||b.run===state.run?.path)return;state.run=await api(`/api/run?path=${encodeURIComponent(b.run)}`);sessionSnapshot=null;activeStage=null;lastWorkflowStage=null;previewVersion=null;renderedStage=null;disclosureStates.clear();state.panelRevision=null;state.missingRun=null}
async function renderPresentationPicker(){if(state.missingRun||state.panelBinding?.run){$('#stage-tabs').innerHTML='';$('#session-content').innerHTML='<div class="session-empty"><h1>Presentation unavailable</h1><p>Share the folder’s new location in the conversation.</p></div>';return}const runs=await api('/api/runs');$('#stage-tabs').innerHTML='';$('#session-content').innerHTML=`<section class="presentation-picker"><h1>${runs.length?'Continue a presentation':'No presentation yet'}</h1>${runs.length?`<div class="presentation-list">${runs.map(r=>`<button class="presentation-choice" data-continue-run="${esc(r.path)}"><span><strong>${esc(r.name)}</strong><small>${esc(date(r.updated_at||r.created_at))}</small></span><span>›</span></button>`).join('')}</div>`:''}<p>${runs.length?'Or describe your next presentation in the conversation.':'Describe what you want to present.'}</p></section>`}
function currentStage(d){const live=d.activity?.current;if(live&&['running','waiting_for_user','paused','failed'].includes(live.status))return live.stage;const map={resources:'style',image:'design',reconstruction:'powerpoint',delivery:'powerpoint'},named=map[d.presentation.current_stage]||d.presentation.current_stage;if(d.stages.some(s=>s.id===named))return named;return[...d.stages].reverse().find(s=>s.has_content)?.id||'plan'}
function followWorkflowStage(d) {
  const next=currentStage(d);
  if(requestedStage&&d.stages.some(stage=>stage.id===requestedStage)){activeStage=requestedStage;requestedStage=null;lastWorkflowStage=next;return}
  if(!activeStage || (next!==lastWorkflowStage && activeStage===lastWorkflowStage && !previewVersion))activeStage=next;
  lastWorkflowStage=next;
}
async function refreshPanel(force=false){
  if(!state.run)return renderPresentationPicker();
  try{
    const d=await api(`/api/panel?run=${encodeURIComponent(state.run.path)}`),changed=d.revision!==state.panelRevision;
    const pptx=d.preview_source||d.downloads.find(f=>f.name.endsWith('.pptx')),rendered=d.stages.find(s=>s.id==='powerpoint')?.image,job=d.preview_job||{};
    if(pptx&&(!rendered||rendered.may_be_older_than_pptx||job.state==='stale')&&job.state!=='running'&&(job.state!=='failed'||job.source_version!==pptx.version))await api('/api/panel/preview',{run:state.run.path});
    if((changed||force)&&!$('dialog[open]')&&!document.activeElement?.matches('input,textarea,select')){
      state.run=await api(`/api/run?path=${encodeURIComponent(state.run.path)}`);
      sessionSnapshot=d;
      followWorkflowStage(d);
      renderPanel();state.panelRevision=d.revision;
    }
  }catch(e){if(!sessionSnapshot)$('#session-content').innerHTML='<div class="panel-notice">Couldn’t update this presentation.</div>'}
}
function panelImage(image,label=''){if(!image)return'';return`<figure class="stage-visual"><button data-preview="${esc(image.url)}" data-title="${esc(label||image.label)}"><img src="${esc(image.url)}" alt="${esc(label||image.label)}"><span class="image-expand">↗</span></button>${label||image.label?`<figcaption>${esc(label||image.label)}</figcaption>`:''}</figure>`}
const planLabels={required_content:'Required content',semantic_relationships:'Relationships',hierarchy:'Information priorities',information_structure:'Information structure',content_structure:'Information structure',visual_obligations:'What must come across',must_include:'Must include',optional_content:'Supporting context',evidence:'Evidence and sources',assumptions:'Assumptions',open_questions:'Open questions',avoid:'Avoid',out_of_scope:'Out of scope',working_title:'Working title',working_supporting_copy:'Supporting copy',slide_role:'Role of this slide',tone:'Tone'};
const visualIntentKeys=['profile','profile_mode','density_intent','visual_direction','explicit_user_visual_requirements','user_required_assets'];
const userGuidanceKeys=['working_title','working_supporting_copy','visual_obligations','must_include','optional_content','tone','avoid','out_of_scope'];
const internalPlanKeys=['supporting_system_note','cross_cutting_principles'];
const stageGuidance={
  plan:{title:'The story this slide needs to tell',description:'Check the message, audience, and ideas. The visual layout comes later.'},
  style:{title:'How the slide should feel',description:'Confirm the visual direction and the materials available for the design.'},
  design:{title:'The proposed slide',description:'Review the full composition first. Supporting design evidence is available when you need it.'},
  powerpoint:{title:'Your editable slide',description:'Download the PowerPoint and compare its preview with the approved design.'},
};
function hasPlanValue(value){return value!==null&&value!==undefined&&value!==''&&(!Array.isArray(value)||value.length>0)&&(typeof value!=='object'||Object.keys(value).length>0)}
function planSection(key,value){return hasPlanValue(value)?`<section class="plan-section"><h2>${esc(planLabels[key]||fieldName(key))}</h2>${readTree(value)}</section>`:''}
function planDisclosure(title,description,content){return content?`<details class="plan-disclosure"><summary><span><strong>${esc(title)}</strong><small>${esc(description)}</small></span></summary><div>${content}</div></details>`:''}
function humanPlanValue(value){return typeof value==='string'?value.replaceAll('_',' '):value}
function organizationContent(structure,secondary,readable){const type=structure?.type||'',kind=type?humanPlanValue(type):'',fallback={sequence:'The ideas follow a deliberate reading order.',comparison:'The slide compares alternatives using a shared frame.',grouped:'Related ideas are organized into clear groups.',system:'The slide explains how connected parts work together.',argument:'The slide builds evidence toward one conclusion.'},note=structure?.user_summary||fallback[type]||'The content is organized to make its logic easy to follow.';return `${hasPlanValue(structure)?`<section class="organization-summary">${kind?`<span>${esc(kind)}</span>`:''}<p>${esc(note)}</p></section>`:''}${['semantic_relationships','hierarchy'].map(key=>hasPlanValue(secondary[key])?planSection(key,readable(secondary[key])):'').join('')}`}
function intentContent(intent){
  if(!Object.keys(intent||{}).length)return emptyStage('Start with the story','The message, audience, and ideas you agree on will appear here.');
  const content=Array.isArray(intent.required_content)?intent.required_content:[];
  const labels=new Map(content.filter(item=>item&&typeof item==='object'&&item.id).map(item=>[item.id,item.idea||item.title||item.label||item.id]));
  const readable=value=>Array.isArray(value)?value.map(readable):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([k,v])=>[k,['from','to','source','target','members'].includes(k)?Array.isArray(v)?v.map(id=>labels.get(id)||id):labels.get(v)||v:readable(v)])):value;
  const sequence=(intent.information_structure||intent.content_structure)?.type==='sequence';
  const blocks=content.map(item=>{
    if(typeof item!=='object'||!item)return `<li><p>${esc(item)}</p></li>`;
    const heading=item.idea||item.title||item.label||item.name;
    const summary=item.meaning||item.description||item.body;
    const rest=Object.fromEntries(Object.entries(item).filter(([key,value])=>!['id','idea','title','label','name','meaning','description','body'].includes(key)&&hasPlanValue(value)));
    return `<li>${heading?`<h3>${esc(heading)}</h3>`:''}${summary?`<p class="plan-item-summary">${esc(summary)}</p>`:''}${Object.keys(rest).length?readTree(rest):''}</li>`;
  }).join('');
  const structure=intent.information_structure||intent.content_structure;
  const handled=new Set(['schema_version','slide_id','status','audience','communication_job','audience_question','dominant_message','slide_role','required_content','information_structure','content_structure',...visualIntentKeys]);
  const secondary=Object.fromEntries(Object.entries(intent).filter(([key])=>!handled.has(key)&&!internalPlanKeys.includes(key)));
  if(Array.isArray(secondary.hierarchy))secondary.hierarchy=secondary.hierarchy.map(id=>labels.get(id)||id);
  const take=keys=>keys.map(key=>[key,secondary[key]]).filter(([,value])=>hasPlanValue(value)).map(([key,value])=>planSection(key,readable(value))).join('');
  const organization=organizationContent(structure,secondary,readable);
  const evidence=take(['evidence','assumptions','open_questions']);
  const guidance=take(userGuidanceKeys);
  return `<div class="intent-content"><section class="intent-hero"><span>Main message</span><h2>${esc(intent.dominant_message||intent.working_title||'Presentation direction')}</h2>${intent.audience_question?`<div><small>Question this slide answers</small><p>${esc(intent.audience_question)}</p></div>`:''}</section><div class="intent-facts">${intent.audience?`<div><span>Audience</span><p>${esc(intent.audience)}</p></div>`:''}${intent.communication_job?`<div><span>Purpose</span><p>${esc(intent.communication_job)}</p></div>`:''}${intent.slide_role?`<div><span>Format</span><p>${esc(humanPlanValue(intent.slide_role))}</p></div>`:''}</div>${blocks?`<section class="plan-section plan-primary"><header><h2>Ideas to include</h2><p>These are the points the finished slide needs to communicate.</p></header><${sequence?'ol':'ul'} class="plan-content-list ${sequence?'is-sequence':''}">${blocks}</${sequence?'ol':'ul'}></section>`:planSection('required_content',intent.required_content)}<div class="plan-support">${planDisclosure('How the story is organized','Structure, relationships, and emphasis.',organization)}${planDisclosure('Evidence and open questions','Sources, assumptions, and points still to resolve.',evidence)}${planDisclosure('Writing and presentation guidance','Titles, tone, constraints, and supporting direction.',guidance)}</div></div>`;
}
function emptyStage(title,message){return`<div class="future-stage"><span></span><h2>${esc(title)}</h2><p>${esc(message)}</p></div>`}
function bobbingDots(){return'<span class="bobbing-dots" role="status"><i></i><i></i><i></i><span class="sr-only">In progress</span></span>'}
function activityContent(stage){const activity=sessionSnapshot.activity||{},current=activity.current,steps=(activity.steps||[]).filter(item=>item.stage===stage),entries=activity.entries||[],stageEntries=entries.filter(item=>item.stage===stage);if(!current&&!stageEntries.length)return'';const latestByStep={};for(const item of entries)latestByStep[item.step]=item;const active=current?.stage===stage?current:null,pending=sessionSnapshot.pending_events?.events?.length||0,complete=steps.filter(step=>latestByStep[step.id]?.status==='complete').length,statusLabel=active?.status==='waiting_for_user'?'Waiting for you':active?.status==='failed'?'Needs attention':active?.status==='paused'?'Paused':active?.status==='complete'?'Complete':'In progress';return`<section class="workflow-activity ${active?'is-live':''}">${active?`<header><div>${active.status==='running'?bobbingDots():`<span class="activity-state ${esc(active.status)}"></span>`}<div><span>${statusLabel}</span><h2>${esc(active.label)}</h2></div></div><p>${esc(active.message||active.purpose)}</p></header>`:''}${pending?`<div class="panel-change"><span></span><div><strong>${pending} ${pending===1?'change':'changes'} saved</strong><small>They will be used before work continues.</small></div></div>`:''}<details class="stage-progress" ${active?'open':''}><summary><span><strong>Stage progress</strong><small>${complete} of ${steps.length} complete</small></span></summary><ol>${steps.map((step,index)=>{const last=latestByStep[step.id],status=last?.status||'upcoming';return`<li class="${esc(status)}"><span>${status==='running'?bobbingDots():status==='complete'?'✓':index+1}</span><div><strong>${esc(step.label)}</strong><small>${esc(step.purpose)}</small></div></li>`}).join('')}</ol></details></section>`}
function versionBar(stage){const versions=sessionSnapshot.versions.filter(v=>v.stages[stage]),saved=sessionSnapshot.stage_selection[stage]||'current',selected=previewVersion?.stage===stage?previewVersion.value:saved;if(!versions.length&&saved==='current')return'';const options=[{id:'current',label:'Latest'},...versions.slice().reverse().map(v=>({id:v.id,label:v.label}))],label=options.find(v=>v.id===selected)?.label||'Latest';return`<div class="version-bar"><div class="version-control"><span>Version</span><details class="version-picker" id="version-picker"><summary aria-label="Choose version"><strong>${esc(label)}</strong><i aria-hidden="true">⌄</i></summary><div class="version-menu" role="listbox" aria-label="Versions">${options.map(option=>`<button role="option" aria-selected="${option.id===selected}" data-preview-version="${esc(option.id)}"><span>${esc(option.label)}</span>${option.id===selected?'<i aria-hidden="true">✓</i>':''}</button>`).join('')}</div></details></div>${selected!==saved?'<button class="quiet-button" id="use-stage-version">Use this version</button>':''}</div>`}
function historyContent(stage){const selected=previewVersion?.stage===stage?previewVersion.value:sessionSnapshot.stage_selection[stage];if(!selected||['current','previous'].includes(selected))return null;const version=sessionSnapshot.versions.find(v=>v.id===selected);if(!version)return null;const files=version.stages[stage]||[],json=files.find(f=>f.data)?.data;if(stage==='plan'&&json)return intentContent(json);const images=files.filter(f=>f.image),downloads=stage==='powerpoint'?files.filter(f=>f.name.toLowerCase().endsWith('.pptx')):[];const labels={style:'Style and materials',design:'Slide design',powerpoint:'PowerPoint preview'};return`<div class="history-files">${images.map(f=>panelImage(f,labels[stage]||f.label)).join('')}${downloads.map(f=>`<a class="history-file" href="${esc(f.url)}" download><strong>Editable PowerPoint</strong><span aria-hidden="true">↓</span></a>`).join('')}${!images.length&&!downloads.length?emptyStage('No preview saved','This version has no reader-facing preview for this stage.'):''}</div>`}
function selectedResources(){return sessionSnapshot.resources.length?`<details class="artifact-group selected-assets"><summary>References and assets <span>${sessionSnapshot.resources.length}</span></summary><div class="retrieved-grid">${sessionSnapshot.resources.map(r=>`<article class="retrieved-asset">${r.url?`<button data-preview="${esc(r.url)}" data-title="${esc(r.name)}"><img src="${esc(r.url)}" alt="${esc(r.name)}"></button>`:'<div class="unavailable-asset"></div>'}<div><h4>${esc(r.name)}</h4>${r.reason?`<p>${esc(r.reason)}</p>`:''}</div></article>`).join('')}</div></details>`:''}
function assetsContent(){return`<section class="session-section"><div class="section-title"><h2>Your assets</h2><label class="asset-add">＋ Add<input id="session-assets" type="file" multiple></label></div>${sessionSnapshot.materials.length?`<div class="asset-list">${sessionSnapshot.materials.map(f=>`<a href="${esc(f.url)}" target="_blank"><strong>${esc(f.name)}</strong><small>${Math.ceil(f.size/1024)} KB</small></a>`).join('')}</div>`:'<p class="stage-empty">Add images, logos, or source files for this presentation.</p>'}</section>`}
function styleContent(){
  const p=state.run.resolved_config.resolved_profile,stage=sessionSnapshot.stages.find(s=>s.id==='style');
  const direction=Object.fromEntries(visualIntentKeys.filter(key=>!['profile','profile_mode'].includes(key)&&hasPlanValue(sessionSnapshot.intent?.[key])).map(key=>[planLabels[key]||fieldName(key),sessionSnapshot.intent[key]]));
  const context=stage?.context?`<section class="style-review"><header><h2>Review before design</h2><p>The style, references, and assets selected for this slide.</p></header>${panelImage(stage.context,stage.style_context?'Style and materials':'Selected references and assets')}${stage.style_direction?planDisclosure('Design notes','The slide-specific direction behind this selection.',readTree(stage.style_direction)):''}</section>`:'';
  return `<section class="style-foundation"><div class="profile-inheritance">${profilePreview(p,state.run.values)}<div><span>Starting style</span><h2>${esc(p.name)}</h2><p>${esc(p.purpose)}</p></div></div>${Object.keys(direction).length?`<details class="foundation-direction"><summary><span><strong>Direction for this slide</strong><small>Requirements that refine the starting style.</small></span></summary><div>${readTree(direction)}</div></details>`:''}</section><div class="session-scope"><strong>Presentation adjustments</strong><span>These choices apply only to this presentation.</span></div><div class="design-settings">${styleCards(state.run,true)}</div>${context}${assetsContent()}${selectedResources()}`;
}
function traceability(groups){const labels={generation:['Inputs used','The approved direction and materials supplied to the design.'],understanding:['How the slide is organized','The meaningful regions, groups, and relationships found in the design.'],measurement:['Measured positions and colors','Pixel evidence used to place and rebuild objects accurately.'],reconstruction:['How the slide was rebuilt','The editable objects and construction evidence behind the PowerPoint.'],review:['Review notes','What was checked and what still needs attention.']};return groups.map(group=>{const files=sessionSnapshot.developer.filter(item=>item.group===group);if(!files.length)return'';const [label,description]=labels[group];return`<details class="artifact-group trace-group"><summary><span><strong>${label}</strong><small>${description}</small></span><em>${files.length}</em></summary>${files.map(f=>`<article class="analysis-item"><h3>${esc(f.label)}</h3>${f.purpose?`<p>${esc(f.purpose)}</p>`:''}<details class="raw-detail"><summary>See details</summary>${f.image?panelImage(f):f.data?readTree(f.data):`<pre>${esc(f.text||'')}</pre>`}</details></article>`).join('')}</details>`}).join('')}
function stageWorkspace(canvas, inspector) {
  return `<div class="stage-workspace"><div class="stage-canvas">${canvas}</div><div class="stage-inspector">${inspector}</div></div>`;
}
function analysisContent(){
  const stage=sessionSnapshot.stages.find(s=>s.id==='design');
  if(!stage.has_content)return emptyStage('Design comes next','The proposed slide will appear after you confirm its style and materials.');
  return stageWorkspace(`<div class="review-prompt"><strong>Review the whole slide first</strong><span>Check the message, hierarchy, and overall feel before opening the supporting evidence.</span></div>${panelImage(stage.image)}`, `${stage.context?`<details class="artifact-group trace-group"><summary><span><strong>Style and materials</strong><small>What the design was asked to use.</small></span></summary>${panelImage(stage.context)}</details>`:''}${traceability(['generation','understanding','measurement','review'])}`);
}
function powerpointContent(){
  const stage=sessionSnapshot.stages.find(s=>s.id==='powerpoint'), job=sessionSnapshot.preview_job||{};
  if(!stage.has_content)return emptyStage('PowerPoint comes after design','The editable slide and its preview will appear after the design is approved.');
  const status=job.state==='running'?`<div class="live-edit">${bobbingDots()}Updating preview</div>`:job.state==='failed'?'<p class="panel-notice" role="status">Preview unavailable. You can still download the PowerPoint.</p>':'';
  return stageWorkspace(`<div class="review-prompt"><strong>Check the editable result</strong><span>Open the PowerPoint after reviewing this rendered preview.</span></div>${status}${panelImage(stage.image)}<div class="delivery-files">${sessionSnapshot.downloads.map(f=>`<a href="${esc(f.url)}" download><strong>${esc(f.name)}</strong><span aria-hidden="true">↓</span></a>`).join('')}</div>`, `${stage.comparison?`<details class="artifact-group trace-group"><summary><span><strong>Compare with the approved design</strong><small>See the original and reconstructed slide together.</small></span></summary>${panelImage(stage.comparison)}</details>`:''}${traceability(['reconstruction','review'])}`);
}
// Preserve expanded evidence and keyboard focus when new artifacts arrive.
const disclosureStates = new Map();
let renderedStage;
function disclosureKey(detail) {
  const parts=[];
  for(let node=detail;node;node=node.parentElement?.closest('details')) {
    parts.unshift(node.querySelector(':scope > summary')?.textContent.replace(/\s+\d+\s*$/, '').trim() || '');
    const article=node.closest('.analysis-item');
    if(article)parts.unshift(article.querySelector('h3')?.textContent || '');
  }
  return parts.join('/');
}
function renderPanel(){
  const d=sessionSnapshot, live=d.activity?.current;
  const stageChanged=renderedStage && renderedStage!==activeStage;
  if(renderedStage)disclosureStates.set(renderedStage,new Map($$('#session-content details').map(el=>[disclosureKey(el),el.open])));
  const focusedStage=document.activeElement?.dataset?.stage;
  $('#stage-tabs').innerHTML=d.stages.map((s,i)=>`<button class="stage-tab ${s.id===activeStage?'active':''} ${s.has_content?'available':''} ${live?.stage===s.id&&live.status==='running'?'working':''}" data-stage="${s.id}" ${s.id===activeStage?'aria-current="step"':''}><span aria-hidden="true">${i+1}</span>${esc(s.title)}${live?.stage===s.id&&live.status==='running'?bobbingDots():''}</button>`).join('');
  const historical=historyContent(activeStage),prior=d.stage_selection[activeStage]==='previous';
  let body=historical;
  if(!body&&activeStage==='plan')body=intentContent(d.intent);
  if(!body&&activeStage==='style')body=styleContent();
  if(!body&&activeStage==='design')body=analysisContent();
  if(!body&&activeStage==='powerpoint')body=powerpointContent();
  const guide=stageGuidance[activeStage];
  $('#session-content').innerHTML=`<header class="stage-heading"><div><span>${esc(d.name)}</span><h1>${esc(guide.title)}</h1><p>${esc(guide.description)}</p></div>${versionBar(activeStage)}</header>${prior?'<div class="superseded-note">You are viewing an earlier version of this stage.</div>':''}<div class="stage-content">${activityContent(activeStage)}${body}</div>`;
  renderedStage=activeStage;
  const previous=disclosureStates.get(activeStage);
  if(previous)for(const detail of $$('#session-content details'))if(previous.has(disclosureKey(detail)))detail.open=previous.get(disclosureKey(detail));
  if(focusedStage)$(`[data-stage="${focusedStage}"]`)?.focus({preventScroll:true});
  if(stageChanged)window.scrollTo({top:0});
  applyPreviews();
}
document.addEventListener('click',e=>attempt(async()=>{
  if(!e.target.closest('.version-picker'))$('#version-picker')?.removeAttribute('open');
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.stage){activeStage=b.dataset.stage;previewVersion=null;rememberStage(activeStage);return renderPanel()}
  if(b.dataset.previewVersion){previewVersion={stage:activeStage,value:b.dataset.previewVersion};return renderPanel()}
  if(b.dataset.continueRun&&!state.run&&!state.panelBinding?.run){state.panelBinding=await api('/api/panel/select',{id:state.panelBinding.id,run:b.dataset.continueRun,revision:state.panelBinding.revision});await syncPanelBinding();return refreshPanel(true)}
  // Shared editor, preview and close actions are registered once in app.js.
  if(b.id==='zoom-preview'){const z=$('#preview-body').classList.toggle('zoomed');b.textContent=z?'Fit':'Zoom in'}
  if(b.id==='use-stage-version'){await api('/api/panel/version',{run:state.run.path,stage:activeStage,version:previewVersion.value});previewVersion=null;toast('Version applied');await refreshPanel(true)}
}));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#version-picker')?.open){$('#version-picker').removeAttribute('open');$('#version-picker summary')?.focus()}});
document.addEventListener('change',e=>attempt(async()=>{if(e.target.id==='session-assets'){for(const f of e.target.files)await api('/api/upload',{run:state.run.path,filename:f.name,content_base64:await fileData(f)});state.run=await api(`/api/run?path=${encodeURIComponent(state.run.path)}`);await refreshPanel(true);toast('Added')}}));
if(typeof window!=='undefined')window.addEventListener('hashchange',()=>{const stage=stageFromLocation();if(stage&&stage!==activeStage&&sessionSnapshot){activeStage=stage;previewVersion=null;renderPanel()}});
document.addEventListener('DOMContentLoaded',()=>attempt(bootPanel));
