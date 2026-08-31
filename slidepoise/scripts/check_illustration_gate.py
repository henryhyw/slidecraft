#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from raster_decisions import illustration_gate_errors

def main():
 p=argparse.ArgumentParser(); p.add_argument('--semantic-map',type=Path,required=True); p.add_argument('--approvals',type=Path,required=True); a=p.parse_args()
 semantic=json.loads(a.semantic_map.read_text(encoding='utf-8')); approvals=json.loads(a.approvals.read_text(encoding='utf-8'))
 ids=[str(e.get('id')) for e in semantic.get('entities',[]) if e.get('kind')=='image' and e.get('visual_source_class')=='novel_illustration']
 gate=approvals.get('illustrations',{}) or {}; status=gate.get('status')
 errors=illustration_gate_errors(semantic,approvals)
 if errors: raise SystemExit('\n'.join(errors))
 print(json.dumps({'candidate_ids':ids,'status':status},indent=2))
if __name__=='__main__': main()
