import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

function harness() {
  const nodes = new Map(), listeners = new Map();
  const node = selector => {
    if (!nodes.has(selector)) {
      const classes = new Set();
      nodes.set(selector, {
        innerHTML: '', textContent: '', hidden: false, dataset: {}, open: false,
        showCount: 0, addEventListener() {},
        showModal() { this.open = true; this.showCount++; },
        close() { this.open = false; },
        classList: {
          remove: value => classes.delete(value),
          toggle(value) { if (classes.has(value)) { classes.delete(value); return false; } classes.add(value); return true; },
          contains: value => classes.has(value),
        },
      });
    }
    return nodes.get(selector);
  };
  const document = {
    activeElement: null,
    querySelector: selector => selector === 'dialog[open]' ? [...nodes.values()].find(n => n.open) : node(selector),
    querySelectorAll: () => [],
    addEventListener(type, fn) { if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(fn); },
  };
  const context = vm.createContext({ document, setTimeout: () => 1, clearTimeout() {} });
  for (const file of ['app.js', 'authoring.js', 'session-panel.js']) {
    vm.runInContext(readFileSync(new URL(`../webapp/ui/${file}`, import.meta.url), 'utf8'), context);
  }
  const run = code => vm.runInContext(code, context);
  const click = async button => { for (const listener of listeners.get('click')) await listener({target:{closest:()=>button}}); };
  const button = (dataset={}, id='') => ({dataset, id, hasAttribute: name => name.slice(5) in dataset});
  return {context, document, node, listeners, run, click, button};
}

test('Panel initializes once and opens a decorated editor once', async () => {
  const h = harness();
  assert.equal(h.listeners.get('DOMContentLoaded').length, 1);
  h.run('var opened=0, decorated=0; openStyleEditor=async()=>opened++; decorateChoices=()=>decorated++;');
  await h.click(h.button({edit:'guidance',session:'true'}));
  assert.equal(h.run('opened'), 1);
  assert.equal(h.run('decorated'), 1);
});

test('image preview opens once and resets zoom on reopening', async () => {
  const h = harness(), preview=h.button({preview:'/image.png',title:'Design'});
  await h.click(preview);
  assert.equal(h.node('#preview-dialog').showCount, 1);
  await h.click(h.button({},'zoom-preview'));
  assert.equal(h.node('#preview-body').classList.contains('zoomed'), true);
  await h.click(preview);
  assert.equal(h.node('#preview-body').classList.contains('zoomed'), false);
  assert.equal(h.node('#zoom-preview').textContent, 'Zoom in');
});

test('stage follows Agent progress and rollback without taking over manual browsing', () => {
  const h = harness();
  h.run("var snapshot={presentation:{current_stage:'plan'}, stages:['plan','style','design','powerpoint'].map(id=>({id}))}; var advance=stage=>{snapshot.presentation.current_stage=stage;followWorkflowStage(snapshot)};");
  h.run("advance('plan'); advance('design');");
  assert.equal(h.run('activeStage'), 'design');
  h.run("advance('plan');");
  assert.equal(h.run('activeStage'), 'plan');
  h.run("activeStage='style'; advance('powerpoint');");
  assert.equal(h.run('activeStage'), 'style');
  h.run("activeStage='powerpoint'; previewVersion={stage:'powerpoint',value:'older'}; advance('design');");
  assert.equal(h.run('activeStage'), 'powerpoint');
});

test('refresh defers while editing and adopts fresh settings before rendering', async () => {
  const h = harness();
  h.run("state.run={path:'/run',values:{density:'old'}}; var snapshots=0; var renderedDensity; api=async path=>path.startsWith('/api/panel?')?{revision:'new',downloads:[],stages:[{id:'style'}],presentation:{current_stage:'style'}}:{path:'/run',values:{density:'fresh'}}; renderPanel=()=>{snapshots++;renderedDensity=state.run.values.density};");
  h.node('#editor-dialog').open=true;
  await h.run('refreshPanel(true)');
  assert.equal(h.run('snapshots'), 0);
  h.node('#editor-dialog').open=false;
  h.document.activeElement={matches: selector=>selector.includes('select')};
  await h.run('refreshPanel(true)');
  assert.equal(h.run('snapshots'), 0);
  h.document.activeElement=null;
  await h.run('refreshPanel(true)');
  assert.equal(h.run('snapshots'), 1);
  assert.equal(h.run('renderedDensity'), 'fresh');
});

test('design and reconstruction expose adaptive canvas and evidence regions', () => {
  const h = harness();
  h.run("sessionSnapshot={stages:[{id:'design',has_content:true,image:{url:'/design.png',label:'Design'}},{id:'powerpoint',has_content:true}],downloads:[{url:'/slide.pptx',name:'slide.pptx'}],developer:[],preview_job:{state:'failed'}}");
  assert.match(h.run('analysisContent()'), /stage-canvas/);
  assert.match(h.run('analysisContent()'), /stage-inspector/);
  assert.match(h.run('powerpointContent()'), /Preview unavailable/);
  assert.match(h.run('powerpointContent()'), /slide.pptx/);
});

test('stale preview is refreshed even when its file is newer than the PowerPoint', async () => {
  const h = harness();
  h.run(`state.run={path:'/run'};var requests=[];api=async(path,body)=>{
    if(body){requests.push(path);return {}};
    if(path.startsWith('/api/panel?'))return {revision:'r',preview_source:{name:'slide.pptx',version:2},downloads:[],stages:[{id:'powerpoint',image:{may_be_older_than_pptx:false}}],preview_job:{state:'stale',source_version:1},presentation:{current_stage:'powerpoint'}};
    return {path:'/run'};
  };renderPanel=()=>{};`);
  await h.run('refreshPanel()');
  assert.equal(h.run('requests[0]'), '/api/panel/preview');
});

test('Plan preserves complete semantics and only numbers an explicit sequence', () => {
  const h = harness();
  h.run(`var planFixture={dominant_message:'A clear argument',audience:'Leaders',communication_job:'Support a decision',slide_role:'decision_brief',information_structure:{type:'comparison',description:'Compare two paths'},required_content:[{id:'a',idea:'First option'},{id:'b',idea:'Second option'}],semantic_relationships:[{from:'a',to:'b',relationship:'contrasts with'}],hierarchy:['a','b'],evidence:['Source note'],assumptions:['One assumption'],open_questions:['One question'],avoid:['Generic process framing']}`);
  const comparison=h.run('intentContent(planFixture)');
  assert.match(comparison, /compares alternatives using a shared frame/);
  assert.doesNotMatch(comparison, /Compare two paths/);
  assert.match(comparison, /decision brief/);
  assert.match(comparison, /Relationships/);
  assert.match(comparison, /First option/);
  assert.match(comparison, /Evidence and sources/);
  assert.match(comparison, /The story this slide needs to tell|Main message/);
  assert.match(comparison, /How the story is organized/);
  assert.match(comparison, /Writing and presentation guidance/);
  assert.match(comparison, /<ul class="plan-content-list /);
  h.run("planFixture.information_structure.type='sequence'");
  assert.match(h.run('intentContent(planFixture)'), /<ol class="plan-content-list is-sequence">/);
});

test('Panel explains each stage before exposing supporting evidence', () => {
  const h = harness();
  assert.equal(h.run("stageGuidance.design.title"), 'The proposed slide');
  assert.match(h.run("stageGuidance.powerpoint.description"), /approved design/);
  h.run("sessionSnapshot={developer:[{group:'measurement',label:'Bounds',purpose:'Measured object bounds'}]}");
  const evidence=h.run("traceability(['measurement'])");
  assert.match(evidence, /Measured positions and colors/);
  assert.match(evidence, /Pixel evidence used to place and rebuild objects accurately/);
  assert.match(evidence, /See details/);
});

test('Plan keeps Agent production notes out of the reader-facing review', () => {
  const h = harness();
  h.run(`var internalPlan={dominant_message:'A reader-facing message',required_content:['One idea'],supporting_system_note:'Console implementation detail',cross_cutting_principles:['Internal approval mechanics'],tone:['Clear']}`);
  const content=h.run('intentContent(internalPlan)');
  assert.doesNotMatch(content, /Console implementation detail/);
  assert.doesNotMatch(content, /Internal approval mechanics/);
  assert.match(content, /Clear/);
});

test('Style foundation is rendered as one composed surface', () => {
  const source = readFileSync(new URL('../webapp/ui/session-panel.js', import.meta.url), 'utf8');
  assert.match(source, /style-foundation/);
  assert.match(source, /foundation-direction/);
});

test('Session style cards identify only the settings changed in this presentation', () => {
  const h = harness();
  h.run(`state.run={overrides:{design_overrides:{style:{density:'spacious'}}}};
    var stylePayload={values:{density:'spacious',display_font:'Georgia',body_font:'Arial',primary:'#111111',secondary:'#222222',highlight:'#333333',surface:'#eeeeee'},densities:{spacious:'Spacious'},style_agency:{density:'guided',typography:'guided',palette:'guided'},selected_sets:{icons:[],components:[]}}`);
  const cards = h.run('styleCards(stylePayload,true)');
  assert.equal((cards.match(/Changed for this presentation/g) || []).length, 1);
  assert.equal((cards.match(/Using the saved profile/g) || []).length, 3);
  assert.match(cards, /Information density[\s\S]*Changed for this presentation/);
  assert.match(cards, /Typography[\s\S]*Using the saved profile/);
});

test('Stage progress only appears after work has actually been recorded', () => {
  const h = harness();
  h.run("sessionSnapshot={activity:{current:null,entries:[],steps:[{id:'shape_story',stage:'plan',label:'Shaping the story',purpose:'Organizing the message.'}]},pending_events:{events:[]}}");
  assert.equal(h.run("activityContent('plan')"), '');
  h.run("sessionSnapshot.activity.entries=[{step:'shape_story',stage:'plan',status:'complete'}]");
  assert.match(h.run("activityContent('plan')"), /1 of 1 complete/);
});

test('Version picker previews a saved stage and only applies on request', async () => {
  const h = harness();
  h.run("sessionSnapshot={versions:[{id:'iteration-1',label:'Version 01',stages:{plan:[{data:{dominant_message:'Earlier plan'}}]}}],stage_selection:{plan:'current'}};activeStage='plan';previewVersion=null");
  const picker=h.run("versionBar('plan')");
  assert.match(picker, /version-picker/);
  assert.match(picker, /Version 01/);
  assert.doesNotMatch(picker, /<select/);
  h.run("renderPanel=()=>{}");
  await h.click(h.button({previewVersion:'iteration-1'}));
  assert.equal(h.run('previewVersion.value'), 'iteration-1');
  assert.match(h.run("versionBar('plan')"), /Use this version/);
});

test('Historical stage previews hide internal files', () => {
  const h = harness();
  h.run("sessionSnapshot={versions:[{id:'iteration-1',stages:{style:[{name:'resource-selection.json',data:{internal:true}},{name:'generation-context-sheet.png',label:'Context',image:true,url:'/context.png'}],powerpoint:[{name:'constructor-scene.json',data:{internal:true}},{name:'slide.pptx',url:'/slide.pptx'}]}}],stage_selection:{style:'iteration-1',powerpoint:'iteration-1'}};previewVersion=null");
  const style=h.run("historyContent('style')");
  assert.match(style, /Style and materials/);
  assert.doesNotMatch(style, /resource-selection\.json/);
  const powerpoint=h.run("historyContent('powerpoint')");
  assert.match(powerpoint, /Editable PowerPoint/);
  assert.doesNotMatch(powerpoint, /constructor-scene\.json/);
});

test('Panel stage navigation supports direct Agent handoffs', () => {
  const source = readFileSync(new URL('../webapp/ui/session-panel.js', import.meta.url), 'utf8');
  assert.match(source, /stageFromLocation/);
  assert.match(source, /rememberStage/);
  assert.match(source, /hashchange/);
});
