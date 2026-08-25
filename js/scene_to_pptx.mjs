#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");
const JSZip = require("jszip");

function parseArgs(argv) {
  const values = {};
  for (let index = 2; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) throw new Error("Use --input <deck-scenes.json> --output <deck.pptx>");
    values[key.slice(2)] = value;
  }
  if (!values.input || !values.output) throw new Error("Use --input <deck-scenes.json> --output <deck.pptx>");
  return values;
}

function hex(value, fallback = "000000") {
  if (!value || value === "none") return fallback;
  return value.replace("#", "").toUpperCase();
}

function geometry(box, dimensions, slideSize) {
  const [x, y, width, height] = box;
  return {
    x: x * slideSize.width / dimensions[0],
    y: y * slideSize.height / dimensions[1],
    w: width * slideSize.width / dimensions[0],
    h: height * slideSize.height / dimensions[1],
  };
}

function pixelPoints(px, dimensions, slideSize) {
  return Math.max(0, Number(px ?? 0) * slideSize.width * 72 / dimensions[0]);
}

function halfPointFloor(value) {
  return Math.max(0.5, Math.floor((Number(value) + 1e-9) * 2) / 2);
}

function addTextbox(slide, object, dimensions, slideSize) {
  const style = object.style ?? {};
  const pxToPoints = (value) => pixelPoints(value, dimensions, slideSize);
  const margins = style.margins_px ?? [0, 0, 0, 0];
  const officeMargins = Array.isArray(margins)
    ? [margins[1], margins[2], margins[3], margins[0]].map(pxToPoints)
    : pxToPoints(margins);
  const paragraphs = Array.isArray(object.paragraphs) ? object.paragraphs : null;
  const content = paragraphs && object.bullet_style
    ? paragraphs.map((paragraph, index) => ({
        text: `•  ${paragraph}`,
        options: { breakLine: index < paragraphs.length - 1 },
      }))
    : object.text ?? "";
  slide.addText(content, {
    objectName: object.id,
    ...geometry(object.bbox_px, dimensions, slideSize),
    fontFace: style.font_family ?? "Arial",
    fontSize: halfPointFloor(style.font_size_pt ?? pixelPoints(style.font_size_px ?? 20, dimensions, slideSize)),
    bold: style.font_weight === "bold" || Number(style.font_weight) >= 600,
    color: hex(style.color, "111111"),
    align: style.alignment ?? "left",
    valign: style.vertical_alignment === "middle" ? "mid" : style.vertical_alignment ?? "top",
    margin: officeMargins,
    breakLine: false,
    fit: style.autofit === "shrink" ? "shrink" : "none",
    paraSpaceBeforePt: 0,
    paraSpaceAfterPt: pxToPoints(style.paragraph_spacing_px ?? 0),
    lineSpacingMultiple: style.line_spacing_multiple ?? 1,
    wrap: true,
    isTextBox: true,
  });
}

function addShape(slide, object, dimensions, slideSize, pptx) {
  const style = object.style ?? {};
  const box = geometry(object.bbox_px, dimensions, slideSize);
  if (object.shape === "slanted_tab" || object.shape === "slanted_banner") {
    const cut = object.shape === "slanted_tab" ? Math.min(box.w * 0.22, 0.12) : Math.min(box.w * 0.08, 0.24);
    slide.addShape(pptx.ShapeType.custGeom, {
      objectName: object.id,
      ...box,
      points: [
        { x: 0, y: 0, moveTo: true },
        { x: box.w, y: 0 },
        { x: box.w - cut, y: box.h },
        { x: 0, y: box.h },
        { close: true },
      ],
      fill: style.fill === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.fill, "D93900") },
      line: style.stroke === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.stroke, "D93900"), width: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
    });
    return;
  }
  const shapes = {
    rectangle: pptx.ShapeType.rect,
    parallelogram: pptx.ShapeType.parallelogram,
    trapezoid: pptx.ShapeType.trapezoid,
    ellipse: pptx.ShapeType.ellipse,
    rounded_rectangle: pptx.ShapeType.roundRect,
    line: pptx.ShapeType.line,
  };
  const type = shapes[object.shape] ?? pptx.ShapeType.rect;
  const options = {
    objectName: object.id,
    ...box,
    fill: object.shape === "line" || style.fill === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.fill, "FFFFFF") },
    line: style.stroke === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.stroke, "D9D9D9"), width: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
  };
  slide.addShape(type, options);
}

function addImage(slide, object, dimensions, slideSize) {
  let imageSource = { path: object.source_path };
  if (object.recolor && String(object.source_path).toLowerCase().endsWith(".svg")) {
    const color = String(object.recolor);
    const svg = fs.readFileSync(object.source_path, "utf8")
      .replaceAll("currentColor", color)
      .replaceAll("#000000", color)
      .replaceAll("#000", color)
      .replaceAll('stroke="black"', `stroke="${color}"`)
      .replaceAll('fill="black"', `fill="${color}"`);
    imageSource = { data: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}` };
  }
  let box = geometry(object.bbox_px, dimensions, slideSize);
  if (String(object.source_path).toLowerCase().endsWith(".svg") && object.preserve_aspect_ratio !== false) {
    const svg = fs.readFileSync(object.source_path, "utf8");
    const viewBox = svg.match(/viewBox=["']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)\s*["']/i);
    const width = svg.match(/\bwidth=["']([\d.]+)(?:px)?["']/i);
    const height = svg.match(/\bheight=["']([\d.]+)(?:px)?["']/i);
    const ratio = viewBox ? Number(viewBox[1]) / Number(viewBox[2]) : width && height ? Number(width[1]) / Number(height[1]) : null;
    if (ratio && Number.isFinite(ratio) && ratio > 0) {
      const fittedWidth = Math.min(box.w, box.h * ratio);
      const fittedHeight = fittedWidth / ratio;
      box = { x: box.x + (box.w - fittedWidth) / 2, y: box.y + (box.h - fittedHeight) / 2, w: fittedWidth, h: fittedHeight };
    }
  }
  slide.addImage({
    ...imageSource,
    objectName: object.id,
    altText: object.selected_asset_id ?? object.semantic_role ?? object.id,
    ...box,
  });
}

function addTable(slide, object, dimensions, slideSize) {
  const structure = object.structure ?? {};
  const rawRows = structure.rows ?? object.rows ?? structure.data ?? [];
  const rows = rawRows.map((row) => row.map((cell) => {
    if (cell && typeof cell === "object" && !Array.isArray(cell)) {
      const options = { ...(cell.options ?? {}) };
      if (cell.rowSpan ?? cell.rowspan) options.rowSpan = cell.rowSpan ?? cell.rowspan;
      if (cell.colSpan ?? cell.colspan) options.colSpan = cell.colSpan ?? cell.colspan;
      return { text: String(cell.text ?? cell.value ?? ""), options };
    }
    return String(cell ?? "");
  }));
  if (!rows.length) throw new Error(`Native table ${object.id} has no authored row data`);
  const style = object.style ?? {};
  const box = geometry(object.bbox_px, dimensions, slideSize);
  const options = {
    objectName: object.id,
    ...box,
    border: { type: "solid", color: hex(style.stroke, "B8B8B8"), pt: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
    fill: { color: hex(style.fill, "FFFFFF") },
    color: hex(style.color, "111111"),
    fontFace: style.font_family ?? "Arial",
    fontSize: halfPointFloor(style.font_size_pt ?? pixelPoints(style.font_size_px ?? 16, dimensions, slideSize)),
    margin: pixelPoints(style.cell_margin_px ?? 6, dimensions, slideSize),
    valign: style.vertical_alignment === "middle" ? "mid" : style.vertical_alignment ?? "top",
    autoFit: false,
    autoPage: false,
  };
  const columnWidths = structure.column_widths_px ?? structure.columns_px;
  if (Array.isArray(columnWidths) && columnWidths.length) {
    const values = columnWidths.length === rows[0].length + 1
      ? columnWidths.slice(1).map((value, index) => Number(value) - Number(columnWidths[index]))
      : columnWidths.map(Number);
    const total = values.reduce((sum, value) => sum + value, 0);
    if (total > 0 && values.length === rows[0].length) options.colW = values.map((value) => box.w * value / total);
  }
  const rowHeights = structure.row_heights_px ?? structure.rows_px;
  if (Array.isArray(rowHeights) && rowHeights.length) {
    const values = rowHeights.length === rows.length + 1
      ? rowHeights.slice(1).map((value, index) => Number(value) - Number(rowHeights[index]))
      : rowHeights.map(Number);
    const total = values.reduce((sum, value) => sum + value, 0);
    if (total > 0 && values.length === rows.length) options.rowH = values.map((value) => box.h * value / total);
  }
  slide.addTable(rows, options);
}

function addChart(slide, object, dimensions, slideSize, pptx) {
  const structure = object.structure ?? {};
  const aliases = { column: pptx.ChartType.bar, bar: pptx.ChartType.bar, line: pptx.ChartType.line, pie: pptx.ChartType.pie, doughnut: pptx.ChartType.doughnut, area: pptx.ChartType.area, scatter: pptx.ChartType.scatter };
  const type = aliases[String(structure.type ?? object.chart_type ?? "bar").toLowerCase()] ?? pptx.ChartType.bar;
  const series = (structure.series ?? []).map((item) => ({
    name: String(item.name ?? "Series"),
    labels: (item.labels ?? structure.categories ?? []).map(String),
    values: (item.values ?? []).map(Number),
  }));
  if (!series.length) throw new Error(`Editable chart ${object.id} has no authored series data`);
  const style = object.style ?? {};
  slide.addChart(type, series, {
    objectName: object.id,
    ...geometry(object.bbox_px, dimensions, slideSize),
    showTitle: Boolean(structure.title),
    title: structure.title ?? "",
    showLegend: structure.show_legend !== false,
    showValue: Boolean(structure.show_values),
    chartColors: structure.colors?.map((value) => hex(value)) ?? undefined,
    showCatName: false,
    showSerName: false,
    border: { color: hex(style.stroke, "FFFFFF"), pt: style.stroke === "none" ? 0 : 0.5 },
  });
}

function addFreeform(slide, object, dimensions, slideSize, pptx) {
  const box = geometry(object.bbox_px, dimensions, slideSize);
  const contourCandidates = object.contours_px ?? [];
  const largestContour = contourCandidates.length
    ? [...contourCandidates].sort((left, right) => right.length - left.length)[0]
    : [];
  const raw = object.points ?? object.contour ?? object.structure?.points ?? object.structure?.contour ?? largestContour;
  if (raw.length < 3) throw new Error(`Freeform ${object.id} has insufficient fitted geometry`);
  const sourceBox = object.bbox_px;
  const points = raw.map((point, index) => {
    const x = Array.isArray(point) ? point[0] : point.x;
    const y = Array.isArray(point) ? point[1] : point.y;
    const local = object.coordinates === "local" || (x <= sourceBox[2] && y <= sourceBox[3]);
    const nx = local ? Number(x) / Math.max(1, sourceBox[2]) : (Number(x) - sourceBox[0]) / Math.max(1, sourceBox[2]);
    const ny = local ? Number(y) / Math.max(1, sourceBox[3]) : (Number(y) - sourceBox[1]) / Math.max(1, sourceBox[3]);
    return { x: Math.max(0, Math.min(box.w, nx * box.w)), y: Math.max(0, Math.min(box.h, ny * box.h)), moveTo: index === 0 };
  });
  points.push({ close: true });
  const style = object.style ?? {};
  slide.addShape(pptx.ShapeType.custGeom, {
    objectName: object.id,
    ...box,
    points,
    fill: style.fill === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.fill, "FFFFFF") },
    line: style.stroke === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.stroke, "D93900"), width: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
  });
}

function addLine(slide, start, end, dimensions, slideSize, style, arrowAtEnd, pptx, name) {
  const x1 = start[0] * slideSize.width / dimensions[0];
  const y1 = start[1] * slideSize.height / dimensions[1];
  const x2 = end[0] * slideSize.width / dimensions[0];
  const y2 = end[1] * slideSize.height / dimensions[1];
  slide.addShape(pptx.ShapeType.line, {
    objectName: name,
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.abs(x2 - x1),
    h: Math.abs(y2 - y1),
    flipH: x2 < x1,
    flipV: y2 < y1,
    line: {
      color: hex(style.color, "D93900"),
      width: Math.max(1, pixelPoints(style.width_px ?? 3, dimensions, slideSize)),
      dash: style.dash === "dashed" ? "dash" : "solid",
      endArrowType: arrowAtEnd ? "triangle" : "none",
      beginArrowType: "none",
    },
  });
}

function addOrthogonalRoute(slide, start, end, dimensions, slideSize, style, arrowAtEnd, pptx, name, terminalAxis = null) {
  if (Math.abs(start[0] - end[0]) < 1 || Math.abs(start[1] - end[1]) < 1) {
    addLine(slide, start, end, dimensions, slideSize, style, arrowAtEnd, pptx, name);
    return;
  }
  const bend = arrowAtEnd && terminalAxis === "horizontal" ? [start[0], end[1]] : [end[0], start[1]];
  addLine(slide, start, bend, dimensions, slideSize, style, false, pptx, `${name}__A`);
  addLine(slide, bend, end, dimensions, slideSize, style, arrowAtEnd, pptx, `${name}__B`);
}

function normalizedOneToOnePoints(object) {
  const source = [...object.sources_px[0]];
  const target = [...object.targets_px[0]];
  const constraints = object.routing_constraints ?? {};
  const tolerance = Number(constraints.axis_alignment_tolerance_px ?? 8);
  const route = String(object.route ?? "straight");
  if (!route.includes("curved") && constraints.collapse_aligned_one_to_one !== false) {
    if (Math.abs(source[0] - target[0]) <= tolerance) {
      const sharedX = (source[0] + target[0]) / 2;
      return [[sharedX, source[1]], [sharedX, target[1]]];
    }
    if (Math.abs(source[1] - target[1]) <= tolerance) {
      const sharedY = (source[1] + target[1]) / 2;
      return [[source[0], sharedY], [target[0], sharedY]];
    }
  }
  const points = [source, ...(object.junctions_px ?? []).map((point) => [...point]), target];
  if (constraints.snap_near_axis_segments !== false) {
    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      if (Math.abs(previous[0] - current[0]) <= tolerance) current[0] = previous[0];
      if (Math.abs(previous[1] - current[1]) <= tolerance) current[1] = previous[1];
    }
  }
  const unique = points.filter((point, index) => index === 0 || Math.abs(point[0] - points[index - 1][0]) > 0.01 || Math.abs(point[1] - points[index - 1][1]) > 0.01);
  return unique.filter((point, index) => {
    if (index === 0 || index === unique.length - 1) return true;
    const previous = unique[index - 1];
    const next = unique[index + 1];
    const vertical = Math.abs(previous[0] - point[0]) < 0.01 && Math.abs(point[0] - next[0]) < 0.01;
    const horizontal = Math.abs(previous[1] - point[1]) < 0.01 && Math.abs(point[1] - next[1]) < 0.01;
    return !(vertical || horizontal);
  });
}

function addConnectorGraph(slide, object, dimensions, slideSize, pptx) {
  const junction = object.junctions_px?.[0] ?? null;
  const orientation = String(object.routing_orientation ?? object.route ?? "").toLowerCase();
  const terminalAxis = orientation.startsWith("vertical") ? "vertical" : "horizontal";
  let segment = 0;
  const nextName = () => `SC_CONNECTOR__${object.id}__${segment++}`;
  const isShared = object.sources_px.length > 1 || object.targets_px.length > 1;
  if (isShared) {
    if (!junction) throw new Error(`Shared connector ${object.id} has no semantic junction`);
    for (const source of object.sources_px) addOrthogonalRoute(slide, source, junction, dimensions, slideSize, object.style, false, pptx, nextName());
    for (const target of object.targets_px) addOrthogonalRoute(slide, junction, target, dimensions, slideSize, object.style, true, pptx, nextName(), terminalAxis);
    return;
  }
  if (object.sources_px.length === 1 && object.targets_px.length === 1) {
    const points = normalizedOneToOnePoints(object);
    for (let index = 1; index < points.length; index += 1) {
      const start = points[index - 1];
      const end = points[index];
      const arrow = index === points.length - 1;
      const axisAligned = Math.abs(start[0] - end[0]) < 0.01 || Math.abs(start[1] - end[1]) < 0.01;
      if (axisAligned) addLine(slide, start, end, dimensions, slideSize, object.style, arrow, pptx, nextName());
      else addOrthogonalRoute(slide, start, end, dimensions, slideSize, object.style, arrow, pptx, nextName(), terminalAxis);
    }
    return;
  }
  const count = Math.min(object.sources_px.length, object.targets_px.length);
  for (let index = 0; index < count; index += 1) {
    const curved = String(object.route).includes("curved");
    const route = object.route === "straight" || curved ? addLine : addOrthogonalRoute;
    const name = `${nextName()}${curved ? "__CURVED" : ""}`;
    route(slide, object.sources_px[index], object.targets_px[index], dimensions, slideSize, object.style, true, pptx, name, terminalAxis);
  }
}

async function convertTaggedLinesToNativeConnectors(output) {
  const zip = await JSZip.loadAsync(fs.readFileSync(output));
  const slidePaths = Object.keys(zip.files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name));
  let converted = 0;
  let textBodiesNormalized = 0;
  for (const slidePath of slidePaths) {
    let xml = await zip.file(slidePath).async("string");
    xml = xml.replace(/<a:bodyPr([^>]*)\/>/g, (_match, attributes) => {
      textBodiesNormalized += 1;
      return `<a:bodyPr${attributes}><a:noAutofit/></a:bodyPr>`;
    });
    xml = xml.replace(/<a:bodyPr([^>]*)><\/a:bodyPr>/g, (_match, attributes) => {
      textBodiesNormalized += 1;
      return `<a:bodyPr${attributes}><a:noAutofit/></a:bodyPr>`;
    });
    xml = xml.replace(/<p:sp>(?:(?!<\/p:sp>)[\s\S])*?<\/p:sp>/g, (block) => {
      if (!/<p:cNvPr[^>]*name="SC_CONNECTOR__[^"]*"/.test(block)) return block;
      converted += 1;
      let convertedBlock = block
        .replace("<p:sp>", "<p:cxnSp>")
        .replace("</p:sp>", "</p:cxnSp>")
        .replace("<p:nvSpPr>", "<p:nvCxnSpPr>")
        .replace("</p:nvSpPr>", "</p:nvCxnSpPr>")
        .replace("<p:cNvSpPr/>", "<p:cNvCxnSpPr/>")
        .replace(/<a:tailEnd type="triangle"\/>/g, '<a:tailEnd type="triangle" w="lg" len="lg"/>')
        .replace(/<a:headEnd type="triangle"\/>/g, '<a:headEnd type="triangle" w="lg" len="lg"/>')
        .replace(block.includes("__CURVED") ? 'prst="line"' : '__NO_MATCH__', 'prst="curvedConnector3"');
      if (!convertedBlock.includes("<a:round/>")) {
        convertedBlock = convertedBlock.replace(/(<a:prstDash[^>]*\/>)/, "$1<a:round/>");
      }
      return convertedBlock;
    });
    const invalidConnector = /<p:cxnSp>(?:(?!<\/p:cxnSp>)[\s\S])*?<p:cNvPr[^>]*name="(?!SC_CONNECTOR__)[^"]*"/.test(xml);
    const unconvertedConnector = /<p:sp>(?:(?!<\/p:sp>)[\s\S])*?<p:cNvPr[^>]*name="SC_CONNECTOR__[^"]*"/.test(xml);
    if (invalidConnector || unconvertedConnector) {
      throw new Error(`Native connector conversion failed structural validation for ${slidePath}`);
    }
    zip.file(slidePath, xml);
  }
  if (converted > 0 || textBodiesNormalized > 0) {
    fs.writeFileSync(output, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  }
  return converted;
}

async function main() {
  const args = parseArgs(process.argv);
  const spec = JSON.parse(fs.readFileSync(args.input, "utf8"));
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Slidecraft";
  pptx.subject = "Editable presentation generated from Slidecraft scene contracts";
  pptx.title = spec.title ?? "Slidecraft presentation";
  pptx.company = spec.company ?? "";
  pptx.lang = spec.language ?? "en-US";
  pptx.theme = {
    headFontFace: spec.theme?.display_font ?? "Georgia",
    bodyFontFace: spec.theme?.body_font ?? "Arial",
    lang: spec.language ?? "en-US",
  };
  const slideSize = { width: 13.333333, height: 7.5 };
  for (const scene of spec.slides) {
    const slide = pptx.addSlide();
    const background = String(scene.background ?? "#FFFFFF");
    slide.background = { color: hex(background.includes("#") ? background : "#FFFFFF", "FFFFFF") };
    const ordered = [...scene.objects].sort((left, right) => (left.z ?? 0) - (right.z ?? 0));
    for (const object of ordered) {
      if (object.kind === "textbox") addTextbox(slide, object, scene.dimensions_px, slideSize);
      else if (object.kind === "shape") addShape(slide, object, scene.dimensions_px, slideSize, pptx);
      else if (object.kind === "image") addImage(slide, object, scene.dimensions_px, slideSize);
      else if (object.kind === "connector_graph") addConnectorGraph(slide, object, scene.dimensions_px, slideSize, pptx);
      else if (object.kind === "table") addTable(slide, object, scene.dimensions_px, slideSize);
      else if (object.kind === "chart") addChart(slide, object, scene.dimensions_px, slideSize, pptx);
      else if (object.kind === "freeform") addFreeform(slide, object, scene.dimensions_px, slideSize, pptx);
      else throw new Error(`Unsupported constructor object kind ${object.kind}`);
    }
    const sources = scene.sources ?? scene.source_references ?? [];
    if (sources.length) slide.addNotes(`[Slidecraft sources]\n${sources.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("\n")}`);
  }
  const output = path.resolve(args.output);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  await pptx.writeFile({ fileName: output });
  await convertTaggedLinesToNativeConnectors(output);
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error}\n`);
  process.exitCode = 1;
});
