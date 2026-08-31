import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../webapp/console/app.js', import.meta.url), 'utf8');
function harness() {
  const nodes = new Map();
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {
      innerHTML: '', textContent: '', hidden: false, dataset: {}, attributes: {},
      addEventListener() {}, remove() {},
      setAttribute(key, value) { this.attributes[key] = value; },
      removeAttribute(key) { delete this.attributes[key]; },
    });
    return nodes.get(selector);
  };
  const controls = ['a', 'b'].map(id => ({ ...node(id), dataset: { profileDefault: id } }));
  const context = vm.createContext({
    document: {
      querySelector: selector => selector === 'dialog[open]' ? [...nodes.values()].find(n => n.open) : node(selector),
      querySelectorAll: selector => selector === '[data-profile-default]' ? controls : [],
      addEventListener() {},
    },
    fetch: () => new Promise(() => {}),
    setTimeout: () => 1, clearTimeout() {},
  });
  vm.runInContext(source, context);
  vm.runInContext("state.overview = {active_profile:'a'}; state.view='design'; toast=()=>{}; refreshOverview=async()=>{}; loadDesign=async()=>{};", context);
  return { context, controls, node, run: code => vm.runInContext(code, context) };
}

test('default selection prevents overlapping writes and restores controls', async () => {
  const h = harness();
  let finish;
  let writes = 0;
  h.context.saveRequest = async () => { writes++; await new Promise(resolve => { finish = resolve; }); };
  h.run('api = saveRequest');
  const pending = h.run("selectDefaultProfile('b')");
  assert.equal(h.controls[1].textContent, 'Applying…');
  assert.ok(h.controls.every(control => control.disabled));
  await h.run("selectDefaultProfile('b')");
  assert.equal(writes, 1);
  h.run("state.overview.active_profile='b'");
  finish();
  await pending;
  assert.equal(h.run('state.defaultSaving'), false);
  assert.equal(h.controls[0].disabled, false);
  assert.equal(h.controls[1].disabled, true);
});

test('failed default selection leaves the old default and remains retryable', async () => {
  const h = harness();
  h.context.saveRequest = async () => { throw new Error('offline'); };
  h.run('api = saveRequest');
  await assert.rejects(h.run("selectDefaultProfile('b')"), /offline/);
  assert.equal(h.run('state.overview.active_profile'), 'a');
  assert.equal(h.run('state.defaultSaving'), false);
  assert.equal(h.controls[1].disabled, false);
  assert.equal(h.controls[1].attributes['aria-busy'], undefined);
});

test('each capability opens a named, bounded detail view', () => {
  const h = harness();
  const dialog = h.node('#preview-dialog');
  dialog.showModal = () => { dialog.open = true; };
  h.run("state.health = Object.keys(capabilityInfo).map(name=>({name,available:true,detail:'Installed'}));");
  for (const name of ['Python', 'OpenCV', 'Node', 'PptxGenJS', 'LibreOffice', 'SAM']) {
    h.run(`openCapability(${JSON.stringify(name)})`);
    assert.equal(h.node('#preview-title').textContent, name);
    assert.ok(h.node('#preview-body').innerHTML.includes('capability-detail'));
    assert.equal(dialog.open, true);
    dialog.open = false;
  }
});

test('SAM progress is visible and terminal failure re-enables installation', async () => {
  const h = harness();
  vm.runInContext(readFileSync(new URL('../webapp/console/authoring.js', import.meta.url), 'utf8'), h.context);
  h.run("state.health = [{name:'SAM',available:false,detail:'Not installed'}];");
  h.context.installStatus = { state: 'running', message: 'Downloading model' };
  h.run('api = async () => installStatus');
  await h.run('pollSamInstall()');
  assert.equal(h.node('#sam-progress').textContent, 'Downloading model');
  assert.equal(h.node('#install-sam').disabled, true);
  assert.ok(h.node('#health-grid').innerHTML.includes('Installing…'));
  h.context.installStatus = { state: 'failed', message: 'Download failed' };
  await h.run('pollSamInstall()');
  assert.equal(h.node('#install-sam').disabled, false);
  assert.equal(h.node('#sam-progress').textContent, 'Download failed');
  assert.ok(!h.node('#health-grid').innerHTML.includes('Installing…'));
});

test('Slide Runs uses the same four stages as the conversation Panel', () => {
  const h = harness();
  h.run(`var runFixture={path:'/tmp/example',name:'Example',created_at:'2026-08-29',requirements:'',panel_stages:[
    {id:'plan',title:'Plan',has_content:true,current:false},
    {id:'style',title:'Style & Assets',has_content:true,current:false},
    {id:'design',title:'Design & Analysis',has_content:true,current:true},
    {id:'powerpoint',title:'PowerPoint',has_content:false,current:false}
  ]}`);
  const card=h.run('runCard(runFixture)');
  for (const label of ['Plan','Style & Assets','Design & Analysis','PowerPoint']) assert.match(card,new RegExp(label.replace('&','&amp;')));
  assert.doesNotMatch(card,/Mark completed|approval or quality verdict|File present|Not created/);
  h.run("state.run={path:'/tmp/example',name:'Example'}");
  h.run('renderRun()');
  assert.match(h.node('#run-detail').innerHTML,/presentation panel/);
  assert.doesNotMatch(h.node('#run-detail').innerHTML,/Session style|Materials|Requirements|Show in Finder/);
});

test('shared Agent changes refresh Console without overwriting an open editor', async () => {
  const h = harness();
  h.run(`var loads=0;state.overview.profiles=[{id:'a'}];state.consoleProfile='a';
    api=async()=>({revision:'changed'});loadDesign=async()=>loads++;`);
  h.node('#editor-dialog').open=true;
  await h.run('refreshSharedFiles()');
  assert.equal(h.run('loads'), 0);
  h.node('#editor-dialog').open=false;
  await h.run('refreshSharedFiles()');
  assert.equal(h.run('loads'), 1);
  await h.run('refreshSharedFiles()');
  assert.equal(h.run('loads'), 1);
});
