import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('default interface copy avoids internal workflow explanations', () => {
  const files = ['console/index.html', 'console/app.js', 'console/authoring.js', 'console/components.js',
    'ui/app.js', 'ui/authoring.js', 'ui/components.js', 'ui/session-panel.js'];
  for (const file of files) {
    const source = readFileSync(new URL(`../webapp/${file}`, import.meta.url), 'utf8');
    for (const text of ['Work with your Agent', 'Pick up any session', 'The Agent will',
      'teach the Agent', 'The Agent reads', 'workflow checkpoint', 'approval or quality verdict',
      'Separate settings for every session', 'Set your style here.']) {
      assert.ok(!source.includes(text), `${file} contains internal-facing copy: ${text}`);
    }
  }
});

test('product interface copy follows the stable punctuation baseline', () => {
  const files = ['console/index.html', 'console/app.js', 'console/authoring.js', 'console/components.js',
    'ui/app.js', 'ui/authoring.js', 'ui/components.js', 'ui/session-panel.js'];
  for (const file of files) {
    const source = readFileSync(new URL(`../webapp/${file}`, import.meta.url), 'utf8');
    assert.ok(!source.includes('—'), `${file} contains an em dash in product copy`);
    assert.ok(!source.includes('AI chooses'), `${file} uses an implementation-facing choice label`);
  }
});
