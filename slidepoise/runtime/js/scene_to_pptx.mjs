#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");

function parseArgs(argv) {
  const values = {};
  for (let index = 2; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) throw new Error("Use --input <presentation.json> --output <slide.pptx>");
    values[key.slice(2)] = value;
  }
  if (!values.input || !values.output) throw new Error("Use --input <presentation.json> --output <slide.pptx>");
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
    italic: Boolean(style.italic),
    charSpacing: pxToPoints(style.char_spacing_px ?? 0),
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

function addShape(slide, object, dimensions, slideSize, pptx, postprocessHints) {
  const style = object.style ?? {};
  const box = geometry(object.bbox_px, dimensions, slideSize);
  const shapes = {
    rectangle: pptx.ShapeType.rect,
    parallelogram: pptx.ShapeType.parallelogram,
    trapezoid: pptx.ShapeType.trapezoid,
    ellipse: pptx.ShapeType.ellipse,
    rounded_rectangle: pptx.ShapeType.roundRect,
    line: pptx.ShapeType.line,
  };
  const type = shapes[object.shape] ?? pptx.ShapeType.rect;
  if (object.shape === "rounded_rectangle" && Number.isFinite(Number(object.round_rect_adjustment))) {
    postprocessHints.round_rect_adjustments[object.id] = Number(object.round_rect_adjustment);
  }
  const options = {
    objectName: object.id,
    ...box,
    fill: object.shape === "line" || style.fill === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.fill, "FFFFFF") },
    line: style.stroke === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.stroke, "D9D9D9"), width: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
  };
  slide.addShape(type, options);
}

function gradientCoordinates(direction) {
  if (direction === "top_left_to_bottom_right") return { x1: "0%", y1: "0%", x2: "100%", y2: "100%" };
  if (direction === "top_right_to_bottom_left") return { x1: "100%", y1: "0%", x2: "0%", y2: "100%" };
  if (direction === "bottom_right_to_top_left") return { x1: "100%", y1: "100%", x2: "0%", y2: "0%" };
  return { x1: "0%", y1: "100%", x2: "100%", y2: "0%" };
}

function applyFillAllTreatment(svg, object) {
  let paint = null;
  let defs = "";
  if (object.recolor_gradient) {
    const gradient = object.recolor_gradient;
    const coords = gradientCoordinates(String(gradient.direction ?? "bottom_left_to_top_right"));
    const gradientId = `scGradient_${String(object.id).replace(/[^A-Za-z0-9_]/g, "_")}`;
    let stops = Array.isArray(gradient.stops) ? gradient.stops : [];
    if (!stops.length) {
      if (!gradient.from || !gradient.to) throw new Error(`Gradient recolor for ${object.id} requires stops or explicit from/to colours`);
      stops = [{ offset: 0, color: gradient.from }, { offset: 1, color: gradient.to }];
    }
    const stopXml = stops.map((stop) => {
      const raw = Number(stop.offset);
      if (!Number.isFinite(raw) || raw < 0 || raw > 1 || !stop.color) throw new Error(`Invalid gradient stop for ${object.id}`);
      return `<stop offset="${raw * 100}%" stop-color="${String(stop.color)}"/>`;
    }).join("");
    defs = `<defs><linearGradient id="${gradientId}" x1="${coords.x1}" y1="${coords.y1}" x2="${coords.x2}" y2="${coords.y2}">${stopXml}</linearGradient></defs>`;
    paint = `url(#${gradientId})`;
  } else if (object.recolor) {
    paint = String(object.recolor);
  }
  if (!paint) return svg;
  let rewritten = svg.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "");
  rewritten = rewritten.replace(/<(path|rect|circle|ellipse|polygon|polyline)\b([^>]*?)(\/?)>/gi, (match, tag, attrs, selfClose) => {
    let cleaned = attrs.replace(/\sfill=(['"]).*?\1/gi, "");
    cleaned = cleaned.replace(/\sstyle=(['"])(.*?)\1/gi, (styleMatch, quote, styleBody) => {
      const next = String(styleBody).replace(/(?:^|;)\s*fill\s*:[^;]*/gi, "").replace(/^;+|;+$/g, "");
      return next ? ` style=${quote}${next}${quote}` : "";
    });
    return `<${tag}${cleaned} fill="${paint}"${selfClose}>`;
  });
  return rewritten.replace(/<svg([^>]*)>/i, (match) => `${match}${defs}`);
}

function addImage(slide, object, dimensions, slideSize) {
  let imageSource = { path: object.source_path };
  const isSvg = String(object.source_path).toLowerCase().endsWith(".svg");
  if ((object.recolor_gradient || object.recolor) && isSvg && object.recolor_mode === "fill_all") {
    const svg = applyFillAllTreatment(fs.readFileSync(object.source_path, "utf8"), object);
    imageSource = { data: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}` };
  } else if (object.recolor_gradient && isSvg) {
    const gradient = object.recolor_gradient ?? {};
    if (!gradient.from || !gradient.to) throw new Error(`Gradient recolor for ${object.id} requires explicit from and to colours from the active profile or semantic map`);
    const from = String(gradient.from);
    const to = String(gradient.to);
    const coords = gradientCoordinates(String(gradient.direction ?? "bottom_left_to_top_right"));
    const gradientId = `scGradient_${String(object.id).replace(/[^A-Za-z0-9_]/g, "_")}`;
    const defs = `<defs><linearGradient id="${gradientId}" x1="${coords.x1}" y1="${coords.y1}" x2="${coords.x2}" y2="${coords.y2}"><stop offset="0%" stop-color="${from}"/><stop offset="100%" stop-color="${to}"/></linearGradient></defs>`;
    let svg = fs.readFileSync(object.source_path, "utf8");
    const paint = `url(#${gradientId})`;
    svg = svg.replace(/<svg([^>]*)>/i, (match) => `${match}${defs}`)
      .replaceAll("currentColor", paint)
      .replace(/#000000\b/gi, paint)
      .replace(/#000\b/gi, paint)
      .replace(/(["'])black\1/gi, (match, quote) => `${quote}${paint}${quote}`);
    imageSource = { data: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}` };
  } else if (object.recolor && isSvg) {
    const color = String(object.recolor);
    const svg = fs.readFileSync(object.source_path, "utf8")
      .replaceAll("currentColor", color)
      .replace(/#000000\b/gi, color)
      .replace(/#000\b/gi, color)
      .replace(/(["'])black\1/gi, (match, quote) => `${quote}${color}${quote}`);
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

function transparentBorder() {
  return { type: "solid", color: "FFFFFF", transparency: 100, pt: 0.1 };
}

function applyComponentTableStyle(rows, tableStyle, dimensions, slideSize) {
  if (!tableStyle || !Object.keys(tableStyle).length) return rows;
  const rowCount = rows.length;
  const colCount = Math.max(0, ...rows.map((row) => row.length));
  const ruleColor = tableStyle.horizontal_rule_color ? hex(tableStyle.horizontal_rule_color) : null;
  const rulePt = Math.max(0.1, Number(tableStyle.horizontal_rule_width_pt ?? 0.5));
  return rows.map((row, r) => row.map((cell, c) => {
    const normalized = cell && typeof cell === "object" && !Array.isArray(cell)
      ? { text: String(cell.text ?? ""), options: { ...(cell.options ?? {}) } }
      : { text: String(cell ?? ""), options: {} };
    const options = normalized.options;
    let fill = tableStyle.body_fill;
    if (r === 0 && tableStyle.header_row_fill) fill = tableStyle.header_row_fill;
    else if (c === 0 && tableStyle.first_column_fill) fill = tableStyle.first_column_fill;
    else if (r > 0 && tableStyle.alternate_row_fill && r % 2 === 0) fill = tableStyle.alternate_row_fill;
    if (fill && !options.fill) options.fill = { color: hex(fill) };
    if (tableStyle.text_color && !options.color) options.color = hex(tableStyle.text_color);
    if (r === 0 && tableStyle.header_bold && options.bold === undefined) options.bold = true;
    if (c === 0 && r === 0 && tableStyle.first_column_bold_header && options.bold === undefined) options.bold = true;
    if (!options.border && (ruleColor || tableStyle.vertical_rules === false || tableStyle.horizontal_rules === false)) {
      const none = transparentBorder();
      const horizontal = ruleColor ? { type: "solid", color: ruleColor, pt: rulePt } : none;
      options.border = [
        tableStyle.horizontal_rules === false ? none : horizontal,
        tableStyle.vertical_rules === false ? none : horizontal,
        tableStyle.horizontal_rules === false ? none : horizontal,
        tableStyle.vertical_rules === false ? none : horizontal,
      ];
    }
    return { text: normalized.text, options };
  }));
}

function addTable(slide, object, dimensions, slideSize) {
  const structure = object.structure ?? {};
  const rawRows = structure.rows ?? object.rows ?? structure.data ?? [];
  let rows = rawRows.map((row) => row.map((cell) => {
    if (cell && typeof cell === "object" && !Array.isArray(cell)) {
      const options = { ...(cell.options ?? {}) };
      if (cell.rowSpan ?? cell.rowspan) options.rowSpan = cell.rowSpan ?? cell.rowspan;
      if (cell.colSpan ?? cell.colspan) options.colSpan = cell.colSpan ?? cell.colspan;
      return { text: String(cell.text ?? cell.value ?? ""), options };
    }
    return String(cell ?? "");
  }));
  if (!rows.length) throw new Error(`Native table ${object.id} has no authored row data`);
  rows = applyComponentTableStyle(rows, structure.table_style ?? {}, dimensions, slideSize);
  const style = object.style ?? {};
  const box = geometry(object.bbox_px, dimensions, slideSize);
  const hasComponentStyle = structure.table_style && Object.keys(structure.table_style).length > 0;
  const options = {
    objectName: object.id,
    ...box,
    border: hasComponentStyle ? transparentBorder() : { type: "solid", color: hex(style.stroke, "B8B8B8"), pt: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
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

function legendPosition(value) {
  const map = { bottom: "b", left: "l", right: "r", top: "t", topRight: "tr", topright: "tr" };
  return map[String(value ?? "").replace(/[_ -]/g, "")] ?? undefined;
}

function addChart(slide, object, dimensions, slideSize, pptx) {
  const structure = object.structure ?? {};
  const aliases = { column: pptx.ChartType.bar, bar: pptx.ChartType.bar, line: pptx.ChartType.line, pie: pptx.ChartType.pie, doughnut: pptx.ChartType.doughnut, area: pptx.ChartType.area, scatter: pptx.ChartType.scatter };
  const typeName = String(structure.type ?? object.chart_type ?? "bar").toLowerCase();
  const type = aliases[typeName] ?? pptx.ChartType.bar;
  const series = (structure.series ?? []).map((item) => ({
    name: String(item.name ?? "Series"),
    labels: (item.labels ?? structure.categories ?? []).map(String),
    values: (item.values ?? []).map(Number),
  }));
  if (!series.length) throw new Error(`Editable chart ${object.id} has no authored series data`);
  const style = object.style ?? {};
  const options = {
    objectName: object.id,
    ...geometry(object.bbox_px, dimensions, slideSize),
    showTitle: Boolean(structure.title),
    title: structure.title ?? "",
    titleFontFace: structure.title_font_family ?? undefined,
    fontFace: structure.data_font_family ?? undefined,
    catAxisLabelFontFace: structure.data_font_family ?? undefined,
    valAxisLabelFontFace: structure.data_font_family ?? undefined,
    legendFontFace: structure.data_font_family ?? undefined,
    showLegend: structure.show_legend !== false,
    legendPos: legendPosition(structure.legend_position),
    showValue: Boolean(structure.show_values),
    showPercent: Boolean(structure.show_percent),
    dataLabelPosition: structure.data_label_position ?? undefined,
    chartColors: structure.colors?.map((value) => hex(value)) ?? undefined,
    showCatName: false,
    showSerName: false,
    border: { color: hex(style.stroke, "FFFFFF"), pt: style.stroke === "none" ? 0 : 0.5 },
  };
  if (Number.isFinite(Number(structure.hole_size))) options.holeSize = Number(structure.hole_size);
  if (Number.isFinite(Number(structure.gap_width_pct))) options.gapWidthPct = Number(structure.gap_width_pct);
  if (structure.bar_grouping) options.barGrouping = String(structure.bar_grouping);
  if (structure.show_value_gridlines === false) options.valGridLine = { color: "FFFFFF", transparency: 100, width: 0.1 };
  else if (structure.show_value_gridlines === true && structure.gridline_color) options.valGridLine = { color: hex(structure.gridline_color), width: 0.75 };
  slide.addChart(type, series, options);
}

function addFreeform(slide, object, dimensions, slideSize, pptx) {
  const box = geometry(object.bbox_px, dimensions, slideSize);
  if (object.path_commands_px?.length) {
    const local = point => ({ x: (point[0] - object.bbox_px[0]) * slideSize.width / dimensions[0], y: (point[1] - object.bbox_px[1]) * slideSize.height / dimensions[1] });
    const points = object.path_commands_px.map(command => {
      if (command.op === "Z") return { close: true };
      const point = local(command.point);
      if (command.op === "M") return { ...point, moveTo: true };
      if (command.op === "L") return point;
      if (command.op === "C") {
        const c1 = local(command.control1), c2 = local(command.control2);
        return { ...point, curve: { type: "cubic", x1: c1.x, y1: c1.y, x2: c2.x, y2: c2.y } };
      }
      throw new Error(`Unsupported authored path operation ${command.op}`);
    });
    const style = object.style ?? {};
    slide.addShape(pptx.ShapeType.custGeom, {
      objectName: object.id, ...box, points,
      fill: { color: hex(style.fill, "FFFFFF"), transparency: style.fill === "none" ? 100 : 0 },
      line: { color: hex(style.stroke, "111111"), width: Math.max(0.1, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)), endArrowType: style.end_arrow_type ?? "none", beginArrowType: "none" },
    });
    return;
  }
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
    line: style.stroke === "none" ? { color: "FFFFFF", transparency: 100 } : { color: hex(style.stroke, "222222"), width: Math.max(0.5, pixelPoints(style.stroke_width_px ?? 1, dimensions, slideSize)) },
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
      color: hex(style.color, "222222"),
      width: Math.max(1, pixelPoints(style.width_px ?? 3, dimensions, slideSize)),
      dash: style.dash === "dashed" ? "dash" : "solid",
      endArrowType: arrowAtEnd ? "triangle" : "none",
      beginArrowType: "none",
    },
  });
}

function addPolylineRoute(slide, points, dimensions, slideSize, style, arrowAtEnd, pptx, nextName) {
  if (!Array.isArray(points) || points.length < 2) return;
  const converted = points.map(point => [
    point[0] * slideSize.width / dimensions[0],
    point[1] * slideSize.height / dimensions[1],
  ]);
  const minX = Math.min(...converted.map(point => point[0]));
  const minY = Math.min(...converted.map(point => point[1]));
  const maxX = Math.max(...converted.map(point => point[0]));
  const maxY = Math.max(...converted.map(point => point[1]));
  const width = Math.max(0.001, maxX - minX);
  const height = Math.max(0.001, maxY - minY);
  const geometryPoints = converted.map((point, index) => ({
    x: point[0] - minX,
    y: point[1] - minY,
    moveTo: index === 0,
  }));
  slide.addShape(pptx.ShapeType.custGeom, {
    objectName: nextName(),
    x: minX,
    y: minY,
    w: width,
    h: height,
    points: geometryPoints,
    fill: { color: "FFFFFF", transparency: 100 },
    line: {
      color: hex(style.color, "222222"),
      width: Math.max(1, pixelPoints(style.width_px ?? 3, dimensions, slideSize)),
      dash: style.dash === "dashed" ? "dash" : "solid",
      endArrowType: arrowAtEnd ? "triangle" : "none",
      beginArrowType: "none",
    },
  });
}

function addGroupingConnector(slide, object, dimensions, slideSize, pptx, nextName) {
  const boxPx = object.grouping_bbox_px;
  if (!Array.isArray(boxPx) || boxPx.length !== 4) throw new Error(`Grouping connector ${object.id} has no grouping_bbox_px`);
  const family = String(object.connector_family ?? "grouping_bracket");
  const side = String(object.grouping_side ?? "right").toLowerCase();
  const base = geometry(boxPx, dimensions, slideSize);
  const gapPx = Number(object.routing_constraints?.minimum_clearance_px ?? 12);
  const gapX = gapPx * slideSize.width / dimensions[0];
  const gapY = gapPx * slideSize.height / dimensions[1];
  const thickness = Math.max(0.5, pixelPoints(object.style?.width_px ?? 3, dimensions, slideSize));
  const isBrace = family === "grouping_brace";
  const authoredDepth = Number(object.grouping_depth_px ?? 0);
  const desiredDepthPx = authoredDepth > 0 ? authoredDepth : Number(isBrace
    ? object.routing_constraints?.grouping_brace_depth_px ?? 34
    : object.routing_constraints?.grouping_bracket_depth_px ?? 22);
  const depthPx = isBrace
    ? desiredDepthPx * Number(object.routing_constraints?.grouping_brace_preset_depth_factor ?? 1.7)
    : desiredDepthPx;
  const depthX = depthPx * slideSize.width / dimensions[0];
  const depthY = depthPx * slideSize.height / dimensions[1];
  let shapeType = isBrace ? pptx.ShapeType.rightBrace : pptx.ShapeType.rightBracket;
  let shapeBox; let rotate = 0; let anchor;
  if (side === "left") {
    shapeType = isBrace ? pptx.ShapeType.leftBrace : pptx.ShapeType.leftBracket;
    shapeBox = { x: Math.max(0, base.x-gapX-depthX), y: base.y, w: depthX, h: base.h };
    anchor = [boxPx[0]-gapPx, boxPx[1]+boxPx[3]/2];
  } else if (side === "top" || side === "bottom") {
    shapeType = isBrace ? pptx.ShapeType.rightBrace : pptx.ShapeType.rightBracket;
    rotate = 90;
    shapeBox = side === "top"
      ? { x: base.x, y: Math.max(0, base.y-gapY-depthY), w: base.w, h: depthY }
      : { x: base.x, y: base.y+base.h+gapY, w: base.w, h: depthY };
    anchor = [boxPx[0]+boxPx[2]/2, side === "top" ? boxPx[1]-gapPx : boxPx[1]+boxPx[3]+gapPx];
  } else {
    shapeBox = { x: base.x+base.w+gapX, y: base.y, w: depthX, h: base.h };
    anchor = [boxPx[0]+boxPx[2]+gapPx, boxPx[1]+boxPx[3]/2];
  }
  const connectorColor = hex(object.style?.color ?? object.style?.stroke ?? "222222");
  slide.addShape(shapeType, {
    objectName: `${object.id}__${isBrace ? "BRACE" : "BRACKET"}`,
    ...shapeBox, rotate,
    // Keep grouping braces/brackets as editable native PowerPoint AutoShapes.
    // Brace presets require a wider bounding box than their visible indentation;
    // the configured calibration factor maps desired visible depth to preset width.
    fill: { color: "FFFFFF", transparency: 100 },
    line: { color: connectorColor, width: thickness },
  });
  if (Array.isArray(object.targets_px) && object.targets_px.length === 1) {
    const directed = Boolean(object.semantic_intent?.directed);
    addLine(slide, anchor, object.targets_px[0], dimensions, slideSize, object.style, directed, pptx, nextName());
  }
}

function addConnectorGraph(slide, object, dimensions, slideSize, pptx) {
  let segment = 0;
  const nextName = () => `SC_CONNECTOR__${object.id}__${segment++}`;
  if (["grouping_bracket", "grouping_brace"].includes(String(object.connector_family ?? ""))) {
    addGroupingConnector(slide, object, dimensions, slideSize, pptx, nextName);
    return;
  }

  // The Python compiler is the sole geometry authority for directional
  // connectors. Rendering does not infer an orientation, add bends, or trace
  // the raster path. If compiled routes are missing, fail rather than silently
  // falling back to an older routing interpretation.
  if (!Array.isArray(object.source_routes_px) || !Array.isArray(object.target_routes_px)) {
    throw new Error(`Connector ${object.id} is missing compiled route geometry`);
  }
  if (object.source_routes_px.length === 0 && object.target_routes_px.length === 0) {
    throw new Error(`Directional connector ${object.id} has no compiled route segments`);
  }
  for (const route of object.source_routes_px) {
    addPolylineRoute(slide, route, dimensions, slideSize, object.style, false, pptx, nextName);
  }
  for (const route of object.target_routes_px) {
    addPolylineRoute(slide, route, dimensions, slideSize, object.style, true, pptx, nextName);
  }
  const junctionStyle = object.junction_style ?? {};
  if (junctionStyle.style === "filled_circle") {
    const diameterPx = Math.max(2, Number(junctionStyle.diameter_px ?? 10));
    const w = diameterPx * slideSize.width / dimensions[0];
    const h = diameterPx * slideSize.height / dimensions[1];
    for (let index = 0; index < (object.junctions_px ?? []).length; index += 1) {
      const point = object.junctions_px[index];
      const cx = point[0] * slideSize.width / dimensions[0];
      const cy = point[1] * slideSize.height / dimensions[1];
      slide.addShape(pptx.ShapeType.ellipse, {
        objectName: `${object.id}__JUNCTION_${index}`,
        x: cx - w / 2, y: cy - h / 2, w, h,
        fill: { color: hex(object.style?.color ?? "222222") },
        line: { color: hex(object.style?.color ?? "222222"), transparency: 100 },
      });
    }
  }
}

function postprocessorPath() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    path.resolve(here, "../scripts/postprocess_pptx.py"),
    path.resolve(here, "../../scripts/postprocess_pptx.py"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

async function convertTaggedLinesToNativeConnectors(output, postprocessHints = {}) {
  const script = postprocessorPath();
  if (!script) return { converted: 0, textBodiesNormalized: 0, skipped: true };
  const python = process.env.PYTHON ?? process.env.PYTHON3 ?? "python3";
  const hintsPath = `${output}.slidepoise-postprocess.json`;
  fs.writeFileSync(hintsPath, JSON.stringify(postprocessHints));
  const result = spawnSync(python, [script, output, "--metadata", hintsPath], { encoding: "utf8" });
  try { fs.unlinkSync(hintsPath); } catch {}
  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || "PowerPoint post-processing failed").trim());
  }
  try {
    return JSON.parse(result.stdout || "{}");
  } catch {
    return { converted: 0, textBodiesNormalized: 0, raw: result.stdout.trim() };
  }
}


function masterText(text, boxPx, style, dimensions, slideSize, align = "left") {
  const box = geometry(boxPx, dimensions, slideSize);
  return { text: { text: String(text ?? ""), options: {
    ...box,
    fontFace: style.font_family ?? "Arial",
    fontSize: halfPointFloor(pixelPoints(style.font_size_px ?? 12, dimensions, slideSize)),
    bold: style.font_weight === "bold",
    color: hex(style.text_color ?? "#4A4A4A", "4A4A4A"),
    align,
    valign: "mid",
    margin: 0,
    breakLine: false,
    fit: "shrink",
    objectName: style.object_name,
  } } };
}

function defineFrameMaster(pptx, scene, slideSize, index) {
  const frame = scene.frame ?? {};
  const header = frame.header ?? {};
  const footer = frame.footer ?? {};
  const dimensions = scene.dimensions_px;
  if (!header.enabled && !footer.enabled) return null;
  const width = dimensions[0];
  const height = dimensions[1];
  const objects = [];
  if (header.enabled && Number(header.height_px ?? 0) > 0) {
    const hh = Number(header.height_px);
    const pad = Number(header.outer_padding_px ?? 40);
    const textH = Math.max(16, hh - 10);
    const y = Math.max(1, (hh - textH) / 2);
    objects.push(masterText(header.left_text, [pad, y, width * 0.48 - pad, textH], { ...header, object_name: "SC_MASTER_HEADER_LEFT" }, dimensions, slideSize, "left"));
    const rightStyle = { ...header, text_color: header.secondary_text_color ?? header.text_color, object_name: "SC_MASTER_HEADER_RIGHT" };
    objects.push(masterText(header.right_text, [width * 0.52, y, width * 0.48 - pad, textH], rightStyle, dimensions, slideSize, "right"));
    objects.push({ line: { ...geometry([pad, hh - 1, width - 2 * pad, 0], dimensions, slideSize), line: { color: hex(header.rule_color ?? "#DED7CF", "DED7CF"), width: Math.max(0.5, pixelPoints(header.rule_width_px ?? 1, dimensions, slideSize)) } } });
    if (Number(header.accent_rule_width_px ?? 0) > 0) {
      objects.push({ line: { ...geometry([pad, hh - 1, Number(header.accent_rule_width_px), 0], dimensions, slideSize), line: { color: hex(header.accent_color ?? "#222222", "222222"), width: Math.max(0.5, pixelPoints(2, dimensions, slideSize)) } } });
    }
  }
  let slideNumber = null;
  if (footer.enabled && Number(footer.height_px ?? 0) > 0) {
    const fh = Number(footer.height_px);
    const top = height - fh;
    const pad = Number(footer.outer_padding_px ?? 40);
    const textH = Math.max(16, fh - 10);
    const y = top + Math.max(1, (fh - textH) / 2);
    objects.push({ line: { ...geometry([pad, top, width - 2 * pad, 0], dimensions, slideSize), line: { color: hex(footer.rule_color ?? "#DED7CF", "DED7CF"), width: Math.max(0.5, pixelPoints(footer.rule_width_px ?? 1, dimensions, slideSize)) } } });
    objects.push(masterText(footer.left_text, [pad, y, width * 0.35, textH], { ...footer, font_weight: footer.left_font_weight ?? footer.font_weight, object_name: "SC_MASTER_FOOTER_LEFT" }, dimensions, slideSize, "left"));
    const centerStyle = { ...footer, text_color: footer.secondary_text_color ?? footer.text_color, object_name: "SC_MASTER_FOOTER_CENTER" };
    objects.push(masterText(footer.center_text, [width * 0.35, y, width * 0.30, textH], centerStyle, dimensions, slideSize, "center"));
    if (footer.slide_number?.enabled) {
      slideNumber = { ...geometry([width - pad - 160, y, 160, textH], dimensions, slideSize), fontFace: footer.font_family ?? "Arial", fontSize: halfPointFloor(pixelPoints(footer.font_size_px ?? 12, dimensions, slideSize)), color: hex(footer.secondary_text_color ?? footer.text_color ?? "#4A4A4A", "4A4A4A"), align: "right", valign: "mid", margin: 0 };
    }
  }
  const title = `SLIDEPOISE_MASTER_${index}`;
  pptx.defineSlideMaster({ title, background: { color: hex(scene.background ?? "#FFFFFF", "FFFFFF") }, objects, slideNumber });
  return title;
}

async function main() {
  const args = parseArgs(process.argv);
  const spec = JSON.parse(fs.readFileSync(args.input, "utf8"));
  const pptx = new pptxgen();
  const scene = spec.slide ?? (Array.isArray(spec.objects) && Array.isArray(spec.dimensions_px) ? spec : null);
  if (!scene || typeof scene !== "object") throw new Error("SlidePoise requires exactly one scene at spec.slide or the document root");
  const dimensions = scene.dimensions_px;
  if (!Array.isArray(dimensions) || dimensions.length !== 2) throw new Error("Scene dimensions_px are required");
  const physicalWidth = 13.333333;
  const physicalHeight = physicalWidth * Number(dimensions[1]) / Number(dimensions[0]);
  pptx.defineLayout({ name: "SLIDEPOISE_CUSTOM", width: physicalWidth, height: physicalHeight });
  pptx.layout = "SLIDEPOISE_CUSTOM";
  pptx.author = "SlidePoise";
  pptx.subject = "Editable single-slide presentation generated from a SlidePoise scene contract";
  pptx.title = spec.title ?? "SlidePoise presentation";
  pptx.company = spec.company ?? "";
  pptx.lang = spec.language ?? "en-US";
  pptx.theme = {
    headFontFace: spec.theme?.display_font ?? "Georgia",
    bodyFontFace: spec.theme?.body_font ?? "Arial",
    lang: spec.language ?? "en-US",
  };
  const slideSize = { width: physicalWidth, height: physicalHeight };
  const postprocessHints = { round_rect_adjustments: {} };
  const masterName = defineFrameMaster(pptx, scene, slideSize, 1);
  const slide = masterName ? pptx.addSlide(masterName) : pptx.addSlide();
  const background = String(scene.background ?? "#FFFFFF");
  slide.background = { color: hex(background.includes("#") ? background : "#FFFFFF", "FFFFFF") };
  const ordered = [...scene.objects].sort((left, right) => (left.z ?? 0) - (right.z ?? 0));
  for (const object of ordered) {
    if (object.kind === "textbox") addTextbox(slide, object, scene.dimensions_px, slideSize);
    else if (object.kind === "shape") addShape(slide, object, scene.dimensions_px, slideSize, pptx, postprocessHints);
    else if (object.kind === "image") addImage(slide, object, scene.dimensions_px, slideSize);
    else if (object.kind === "connector_graph") addConnectorGraph(slide, object, scene.dimensions_px, slideSize, pptx);
    else if (object.kind === "table") addTable(slide, object, scene.dimensions_px, slideSize);
    else if (object.kind === "chart") addChart(slide, object, scene.dimensions_px, slideSize, pptx);
    else if (object.kind === "freeform") addFreeform(slide, object, scene.dimensions_px, slideSize, pptx);
    else throw new Error(`Unsupported constructor object kind ${object.kind}`);
  }
  const sources = scene.sources ?? scene.source_references ?? [];
  if (sources.length) slide.addNotes(`[SlidePoise sources]\n${sources.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("\n")}`);
  const output = path.resolve(args.output);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  await pptx.writeFile({ fileName: output });
  await convertTaggedLinesToNativeConnectors(output, postprocessHints);
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error}\n`);
  process.exitCode = 1;
});
