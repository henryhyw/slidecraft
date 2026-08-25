import fs from "node:fs/promises";
import path from "node:path";

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, item, index, all) => {
  if (item.startsWith("--")) pairs.push([item.slice(2), all[index + 1]]);
  return pairs;
}, []));

if (!args.step4 || !args.contract || !args.outputStep4 || !args.outputContract || !args.assetDir || !args.report) {
  throw new Error("Required flags are --step4, --contract, --outputStep4, --outputContract, --assetDir, and --report");
}

const LIBRARY_ROOT = path.resolve(args.libraryRoot ?? path.join(process.cwd(), "assets/tabler"));
const manifest = JSON.parse(await fs.readFile(path.join(LIBRARY_ROOT, "manifest.json"), "utf8"));
const catalog = new Map(manifest.assets.map((asset) => [asset.icon_id, asset]));

const ROLE_DEFAULTS = {
  intent_to_structure_diagram: "hierarchy-3",
  semantic_planning: "hierarchy-3",
  visual_reference_icon: "template",
  visual_references: "template",
  pictogram_reference_icon: "icons",
  pictogram_icon_references: "icons",
  user_icon_reference: "cloud-upload",
  user_provided_icons: "cloud-upload",
  style_rule_icon: "palette",
  style_rules: "palette",
  generative_ai_icon: "photo-spark",
  generated_image: "photo-spark",
  semantic_graph_icon: "affiliate",
  semantic_mapping: "affiliate",
  measurement_geometry_icon: "ruler-measure",
  pixel_level_measurement: "ruler-measure",
  known_element_icon: "layout-dashboard",
  known_element_reconstruction: "layout-dashboard",
  novel_element_icon: "vector-bezier-2",
  new_redesigned_reconstruction: "vector-bezier-2",
  editable_pptx_file: "file-type-ppt",
};

const KEYWORDS = {
  "hierarchy-3": ["semantic", "planning", "hierarchy", "structure", "node"],
  template: ["template", "page", "layout", "reference"],
  icons: ["icon", "pictogram", "library", "asset"],
  "cloud-upload": ["user", "uploaded", "provided", "asset", "cloud"],
  palette: ["style", "color", "brand", "palette", "typography"],
  "photo-spark": ["image", "generation", "visual", "spark", "ai"],
  affiliate: ["semantic", "mapping", "graph", "relationship", "node"],
  "ruler-measure": ["pixel", "measure", "geometry", "boundary", "ruler"],
  "layout-dashboard": ["known", "layout", "native", "reconstruction", "component"],
  "vector-bezier-2": ["new", "redesigned", "vector", "geometry", "bezier", "fitting"],
  "file-type-ppt": ["powerpoint", "pptx", "editable", "output", "file"],
};

function words(value) {
  return new Set(String(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/).filter(Boolean));
}

function rankedCandidates(entity) {
  const terms = words(`${entity.role} ${entity.semantic_description ?? ""}`);
  return [...catalog.keys()].map((iconId) => {
    const matched = (KEYWORDS[iconId] ?? []).filter((term) => terms.has(term));
    const preferred = ROLE_DEFAULTS[entity.role] === iconId;
    return { icon_id: iconId, score: matched.length * 5 + (preferred ? 40 : 0), matched_concepts: matched };
  }).sort((a, b) => b.score - a.score || a.icon_id.localeCompare(b.icon_id));
}

function tablerIdFromAssetId(assetId) {
  const prefix = "TABLER_OUTLINE_";
  if (!assetId?.startsWith(prefix)) return null;
  return assetId.slice(prefix.length).toLowerCase().replaceAll("_", "-");
}

function containBox(target) {
  const [x, y, width, height] = target;
  const side = Math.min(width, height);
  return [x + (width - side) / 2, y + (height - side) / 2, side, side].map((value) => Number(value.toFixed(2)));
}

const step4 = JSON.parse(await fs.readFile(args.step4, "utf8"));
const contract = JSON.parse(await fs.readFile(args.contract, "utf8"));
const upstreamAssets = new Map((step4.upstream_handoff?.selected_assets ?? []).map((asset) => [asset.internal.asset_id, asset.internal]));
const icons = step4.entities.filter((entity) => entity.kind === "icon");
const used = new Set();
const selections = [];

for (const entity of icons) {
  const upstreamId = entity.upstream_asset_id ?? null;
  const upstream = upstreamAssets.get(upstreamId);
  const exactTablerId = tablerIdFromAssetId(upstreamId);
  if (upstream?.canonical_file) {
    selections.push({ entity, selectedId: upstreamId, iconId: exactTablerId, sourcePath: upstream.canonical_file, mode: "exact_canonical_asset", candidates: rankedCandidates(entity) });
    continue;
  }
  if (exactTablerId && catalog.has(exactTablerId)) {
    selections.push({ entity, selectedId: upstreamId, iconId: exactTablerId, sourcePath: catalog.get(exactTablerId).canonical_file, mode: "exact_canonical_asset", candidates: rankedCandidates(entity) });
    continue;
  }
  const candidates = rankedCandidates(entity);
  const selected = candidates.find((candidate) => !used.has(candidate.icon_id)) ?? candidates[0];
  used.add(selected.icon_id);
  selections.push({ entity, selectedId: `TABLER_OUTLINE_${selected.icon_id.toUpperCase().replaceAll("-", "_")}`, iconId: selected.icon_id, sourcePath: catalog.get(selected.icon_id).canonical_file, mode: "set_level_substitution", candidates });
}

await fs.mkdir(args.assetDir, { recursive: true });
const records = [];
for (const item of selections) {
  const extension = path.extname(item.sourcePath) || ".svg";
  const destination = path.join(args.assetDir, `${item.entity.id}${extension}`);
  await fs.copyFile(item.sourcePath, destination);
  const placement = item.entity.measurement.canonical_asset_placement;
  records.push({
    entity_id: item.entity.id,
    semantic_role: item.entity.role,
    semantic_description: item.entity.semantic_description,
    selection_mode: item.mode,
    upstream_asset_id: item.entity.upstream_asset_id ?? null,
    selected_asset_id: item.selectedId,
    selected_library: item.mode === "exact_canonical_asset" && !item.iconId ? "User-provided canonical asset" : "Tabler Icons Outline",
    selected_icon: item.iconId,
    selected_asset_path: destination,
    alternative_candidates: item.candidates.filter((candidate) => candidate.icon_id !== item.iconId).slice(0, 4),
    target_layout_bbox_px: placement.target_visual_footprint.px,
    target_color: placement.target_color,
    target_rotation_degrees: placement.rotation_degrees,
    intrinsic_viewbox: [0, 0, 24, 24],
    final_svg_bbox_px: containBox(placement.target_visual_footprint.px),
    final_svg_color: placement.target_color,
    preserve_aspect_ratio: true,
    z_order_source: "slide understanding group order and stacking relationships",
  });
}

const recordById = new Map(records.map((record) => [record.entity_id, record]));
for (const entity of step4.entities) {
  if (recordById.has(entity.id)) {
    entity.canonical_asset_mapping = recordById.get(entity.id);
    entity.reconstruction_policy = "canonical_svg_replacement";
  }
}
step4.reconstruction_guidance.icons = "Restore an exact upstream canonical SVG when available. Otherwise insert the coherent Tabler Icons Outline set recorded in canonical_asset_mappings. Generated icon pixels do not become PowerPoint geometry.";
step4.canonical_asset_mappings = records;
contract.fitted_geometry_contracts = (contract.fitted_geometry_contracts ?? []).filter((item) => !recordById.has(item.id));
contract.canonical_asset_mappings = records;
contract.icon_replacement_policy = {
  provider: "Tabler Icons Outline",
  exact_restore_first: true,
  fallback: "joint set-level selection from the configured canonical SVG library",
  generated_icon_pixels_are_geometry_source: false,
  aspect_ratio: "preserve",
  placement_source: "slide understanding target visual footprint",
};

await fs.writeFile(args.outputStep4, JSON.stringify(step4, null, 2) + "\n", "utf8");
await fs.writeFile(args.outputContract, JSON.stringify(contract, null, 2) + "\n", "utf8");
const report = {
  library: "Tabler Icons Outline",
  version: manifest.version,
  license: manifest.license,
  selection_policy: contract.icon_replacement_policy,
  icon_count: records.length,
  exact_restorations: records.filter((record) => record.selection_mode === "exact_canonical_asset").length,
  set_level_substitutions: records.filter((record) => record.selection_mode === "set_level_substitution").length,
  records,
};
await fs.writeFile(args.report, JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ provider: report.library, icon_count: records.length, selected: records.map((record) => [record.entity_id, record.selected_asset_id, record.selection_mode]) }, null, 2));
