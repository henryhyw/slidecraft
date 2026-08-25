const state = { overview: null, health: null, design: null, providers: [], selectedProjectPath: null, internalVisible: false, selectedAssetFile: null, designEditMode: null, selectedLibrary: null, selectedLibraryItem: null, projectPickerCategory: null, removalResolver: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.reason || "Request failed");
  return payload;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2300);
}

async function openLocalResource(resourceIdValue, button) {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span aria-hidden="true">↗</span> Opening…`;
  try {
    await api("/api/open-resource", {
      method: "POST",
      body: JSON.stringify({ location: state.selectedProjectPath, resource_id: resourceIdValue }),
    });
    showToast("Opened in the default app");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

async function openLocalFolder(kind, value, button) {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span aria-hidden="true">↗</span> Opening…`;
  try {
    const endpoint = kind === "project" ? "/api/open-project-folder" : "/api/open-library-folder";
    const body = kind === "project" ? { location: value } : { name: value };
    await api(endpoint, { method: "POST", body: JSON.stringify(body) });
    showToast("Opened in Finder");
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

function confirmRemoval({ title, message, confirmLabel = "Remove" }) {
  $("#removal-title").textContent = title;
  $("#removal-message").textContent = message;
  $("#removal-confirm").textContent = confirmLabel;
  $("#removal-dialog").showModal();
  return new Promise(resolve => { state.removalResolver = resolve; });
}

function finishRemovalConfirmation(confirmed) {
  const resolve = state.removalResolver;
  state.removalResolver = null;
  $("#removal-dialog").close();
  if (resolve) resolve(confirmed);
}

function projectCard(project) {
  const progress = project.progress || { label: "Ready to start", deliverable_count: 0 };
  const status = project.available ? progress.label : "Folder unavailable";
  return `<article class="project-card ${project.available ? "" : "unavailable"}" data-project-path="${escapeHtml(project.path)}">
    ${project.available ? `<button class="card-hit-target project-card-open" type="button" aria-label="Open ${escapeHtml(project.name)}"></button>` : ""}
    <h4>${escapeHtml(project.name)}</h4>
    <p>${escapeHtml(project.description || "A local Slidecraft workspace")}</p>
    <code class="project-path" title="${escapeHtml(project.path)}">${escapeHtml(project.path)}</code>
    <div class="project-card-footer">
      <div class="project-meta"><span>${progress.deliverable_count ? `${progress.deliverable_count} presentation files` : "No presentation exported yet"}</span><span class="project-status ${project.available ? "" : "unavailable"}">${escapeHtml(status)}</span></div>
      ${project.available ? `<button class="open-folder-button project-open-folder" type="button" data-project-folder="${escapeHtml(project.path)}"><span aria-hidden="true">↗</span> Open folder</button>` : ""}
    </div>
  </article>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function exactFontFamily(fontName, fallback = "sans-serif") {
  const safeName = String(fontName || "").replace(/[\\"]/g, "").trim();
  return safeName ? `"${safeName}", ${fallback}` : fallback;
}

function renderTypographyLabel(displayFont, bodyFont) {
  const label = $("#typography-label");
  const display = document.createElement("span");
  const separator = document.createElement("span");
  const body = document.createElement("span");
  display.className = "typography-label-font typography-label-display";
  body.className = "typography-label-font typography-label-body";
  separator.className = "typography-label-separator";
  display.textContent = displayFont;
  separator.textContent = "+";
  body.textContent = bodyFont;
  display.style.fontFamily = exactFontFamily(displayFont, "serif");
  body.style.fontFamily = exactFontFamily(bodyFont, "sans-serif");
  label.replaceChildren(display, separator, body);
}

async function loadOverview() {
  state.overview = await api("/api/overview");
  const projects = state.overview.projects;
  const metrics = [
    ["Projects", state.overview.available_project_count, "Available on this Mac"],
    ["Source materials", state.overview.source_material_count, "Documents and files across projects"],
  ];
  $("#metric-grid").innerHTML = metrics.map(item => `<div class="metric-card"><span class="metric-label">${item[0]}</span><strong class="metric-value">${item[1]}</strong><div class="metric-note">${item[2]}</div></div>`).join("");
  await renderLatestPresentation(state.overview.latest_presentation);
  const cards = projects.length ? projects.slice(0, 3).map(projectCard).join("") : `<div class="empty-state">Create your first project to gather materials and start a presentation.</div>`;
  $("#recent-projects").innerHTML = cards;
  $("#all-projects").innerHTML = projects.length ? projects.map(projectCard).join("") : cards;
  bindProjectCards();
  $("#runtime-caption").textContent = `${state.overview.runtime.mode} · ${state.overview.runtime.compute} compute`;
  renderLibraries();
}

async function renderLatestPresentation(presentation) {
  const container = $("#latest-presentation");
  if (!presentation) {
    container.classList.add("is-empty");
    container.innerHTML = `<div class="latest-presentation-copy"><p class="eyebrow">LATEST PRESENTATION</p><h3>Your latest deck will appear here</h3><p>Once an editable PowerPoint is exported, its current slide preview will stay within easy reach.</p></div><div class="latest-presentation-empty" aria-hidden="true"><span>P</span></div>`;
    return;
  }
  container.classList.remove("is-empty");
  let previewUrl = presentation.preview_resource_id
    ? `/api/resource-file?path=${encodeURIComponent(presentation.project_path)}&resource_id=${encodeURIComponent(presentation.preview_resource_id)}`
    : null;
  if (!previewUrl) {
    try {
      const preview = await api(`/api/resource-preview?path=${encodeURIComponent(presentation.project_path)}&resource_id=${encodeURIComponent(presentation.resource_id)}`);
      if (preview.kind === "pages" && preview.images?.length) previewUrl = preview.images[0];
      if (preview.kind === "image") previewUrl = `/api/resource-file?path=${encodeURIComponent(presentation.project_path)}&resource_id=${encodeURIComponent(presentation.resource_id)}`;
    } catch (_) {
      previewUrl = null;
    }
  }
  const displayName = presentation.name.replace(/\.pptx$/i, "").replace(/[_-]+/g, " ");
  container.innerHTML = `<button class="latest-presentation-preview" type="button" aria-label="Preview ${escapeHtml(presentation.name)}">${previewUrl ? `<img src="${escapeHtml(previewUrl)}" alt="Current preview of ${escapeHtml(presentation.name)}">` : `<span class="presentation-file-fallback">P</span>`}</button><div class="latest-presentation-copy"><p class="eyebrow">LATEST PRESENTATION</p><h3>${escapeHtml(displayName)}</h3><p>${escapeHtml(presentation.project_name)}</p><button class="text-button latest-open-project" type="button">Open project</button></div>`;
  container.querySelector(".latest-presentation-preview").addEventListener("click", () => openPreview(presentation.resource_id, presentation.project_path));
  container.querySelector(".latest-open-project").addEventListener("click", () => openProject(presentation.project_path));
}

function bindProjectCards() {
  $$(".project-card[data-project-path]").forEach(card => {
    card.querySelector(".project-card-open")?.addEventListener("click", () => openProject(card.dataset.projectPath));
  });
  $$(".project-open-folder").forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    openLocalFolder("project", button.dataset.projectFolder, button);
  }));
}

function renderFiles(selector, files) {
  $(selector).innerHTML = files.length
    ? files.map(path => `<div class="file-row"><span>◫</span><code>${escapeHtml(path.split("/").pop())}</code></div>`).join("")
    : `<div class="empty-file">Nothing here yet</div>`;
}

async function openProject(path, includeInternal = false) {
  const [detail, resources] = await Promise.all([
    api(`/api/project?path=${encodeURIComponent(path)}&internal=${includeInternal ? "1" : "0"}`),
    api(`/api/resources?path=${encodeURIComponent(path)}`),
  ]);
  state.selectedProjectPath = path;
  state.internalVisible = includeInternal;
  $("#workspace-project-title").textContent = detail.project.name;
  $("#workspace-project-description").textContent = detail.project.description || "Presentation project";
  $("#workspace-project-path").textContent = detail.project.workspace_path;
  $("#workspace-project-path").title = detail.project.workspace_path;
  renderProjectProgress(detail.progress);
  $("#workspace-deliverables").innerHTML = resources.categories.deliverables.length
    ? resources.categories.deliverables.map(item => resourceCard(item, { allowOpen: true })).join("")
    : `<div class="empty-state"><strong>No presentation output yet</strong><span>Your editable PowerPoint and its previews will appear here automatically.</span></div>`;
  bindPreviewCards();
  renderProjectResources(resources);
  navigate("projects");
  $("#projects-list-panel").hidden = true;
  $("#project-workspace-panel").hidden = false;
}

function renderProjectProgress(progress) {
  const milestones = ["Brief", "Plan", "Design", "Editable objects", "PowerPoint"];
  $("#project-progress-label").textContent = progress.label;
  $("#project-progress-note").textContent = progress.status === "complete"
    ? "The editable presentation is available below. You can still ask the Agent to revise any slide."
    : "Continue in your Agent conversation whenever you want to review, revise or continue the presentation.";
  $("#project-progress-track").innerHTML = milestones.map((label, index) => `<div class="progress-node ${index < progress.milestone_index ? "done" : ""} ${index === progress.milestone_index ? "current" : ""}"><span></span><small>${label}</small></div>`).join("");
}

function resourceId(item) {
  return item.resource_id || item.asset_id;
}

function friendlySource(value) {
  const labels = {
    project_sources_folder: "Added to this project",
    user_clarification: "Decision from your conversation",
    visual_reference_library_retrieval: "Selected from Visual References",
    icon_library_retrieval: "Selected from the Icon Library",
    tabler: "Selected from the Tabler icon set",
    local_console_upload: "Uploaded in Slidecraft",
    direct_project_folder: "Added from the project folder",
    user_local_file: "Added by you",
    known_component_library_retrieval: "Selected from Components",
  };
  return labels[value] || "Prepared for this project";
}

function resourceStatus(item) {
  const slides = item.used_by_slide_ids || [];
  if (slides.length) return `Used on ${slides.join(", ")}`;
  if (item.selection_mode || item.retrieval_reason) return "Prepared for this deck";
  return friendlySource(item.provenance);
}

function thumbnail(item) {
  const id = resourceId(item);
  const fileUrl = `/api/resource-file?path=${encodeURIComponent(state.selectedProjectPath)}&resource_id=${encodeURIComponent(id)}`;
  const media = item.media_type || "";
  const suffix = String(item.path || item.stored_path || item.name || "").toLowerCase();
  if (media.startsWith("image/") || /\.(png|jpe?g|gif|webp|svg|bmp)$/.test(suffix)) {
    return `<img src="${fileUrl}" alt="" loading="lazy">`;
  }
  const extension = String(item.name || "FILE").split(".").pop().slice(0, 5).toUpperCase();
  return `<span>${escapeHtml(extension)}</span>`;
}

function resourceCard(item, options = {}) {
  const { category = null, allowOpen = false } = options;
  const title = item.kind === "canonical_icon" ? cleanRole(item.requested_role || item.semantic_role || item.name) : item.name || item.semantic_role || item.resource_id;
  const detail = item.kind === "canonical_icon" ? `${item.name} from ${item.provenance || "the icon collection"}` : item.description || cleanRole(item.semantic_role) || item.retrieval_reason || "Open to preview this item";
  const id = resourceId(item);
  const role = item.requested_role && item.requested_role !== title ? `<span class="resource-role">Purpose: ${escapeHtml(cleanRole(item.requested_role))}</span>` : "";
  const remove = category ? `<button class="resource-remove" type="button" data-resource-category="${escapeHtml(category)}" data-resource-id="${escapeHtml(id)}" aria-label="Remove ${escapeHtml(title)} from this project">×</button>` : "";
  const openFile = allowOpen ? `<button class="resource-open-file" type="button" data-resource-id="${escapeHtml(id)}" aria-label="Open ${escapeHtml(title)} on this computer"><span aria-hidden="true">↗</span> Open file</button>` : "";
  return `<article class="resource-card previewable ${item.kind === "canonical_icon" ? "icon-resource-card" : ""}" data-resource-id="${escapeHtml(id)}">
    <button class="card-hit-target preview-trigger resource-preview-open" type="button" data-resource-id="${escapeHtml(id)}" aria-label="Preview ${escapeHtml(title)}"></button>
    <div class="resource-thumbnail">${thumbnail(item)}</div>
    <div class="resource-copy"><h4>${escapeHtml(title)}</h4><p>${escapeHtml(typeof detail === "string" ? detail : JSON.stringify(detail))}</p>${role}</div>
    <div class="resource-card-footer"><span class="resource-status">${escapeHtml(resourceStatus(item))}</span>${openFile}</div>
    ${remove}
  </article>`;
}

function humanLabel(value) {
  return String(value || "Project material").replaceAll(/[_-]+/g, " ").toLowerCase().replace(/^\w/, character => character.toUpperCase());
}

function cleanRole(value) {
  if (!value) return "";
  return humanLabel(String(value || "").replace(/^stage[_\s-]*\d+[_\s-]*/i, ""));
}

function displayKey(value) {
  const labels = { chrome_content_proposal: "Header and footer", exact_content: "Presentation content", explicit_human_constraints: "Your requirements", run_context: "Project context" };
  return labels[value] || humanLabel(value);
}

function renderMaterials(items) {
  const files = items.filter(item => item.kind === "source_file");
  const decisions = items.filter(item => item.kind === "user_statement");
  const fileCards = files.map(item => resourceCard(item, { allowOpen: true })).join("");
  const decisionCards = decisions.map(item => `<article class="resource-card decision-card"><div class="resource-thumbnail"><span>✓</span></div><div class="resource-copy"><h4>${escapeHtml(humanLabel(item.name))}</h4><p>${escapeHtml(item.value || "")}</p></div><span class="resource-status">Decision from your conversation</span></article>`).join("");
  $("#resource-materials").innerHTML = fileCards + decisionCards || `<div class="empty-state"><strong>No materials yet</strong><span>Add a brief, document or data file to begin.</span></div>`;
  bindPreviewCards();
}

function renderProjectResources(catalog) {
  const categories = catalog.categories;
  const countIds = { materials: "count-materials", visual_assets: "count-visual-assets", visual_references: "count-visual-references", icons: "count-icons", components: "count-components" };
  Object.entries(countIds).forEach(([key, id]) => { $(`#${id}`).textContent = catalog.counts[key] || 0; });
  renderMaterials(categories.materials);
  ["visual_references", "icons", "components"].forEach(key => {
    const available = catalog.shared_availability?.[key] || 0;
    $(`#resource-${key.replaceAll("_", "-")}`).innerHTML = categories[key].length
      ? categories[key].map(item => resourceCard(item, { category: key })).join("")
      : `<div class="empty-state"><strong>Nothing assigned yet</strong><span>${available ? `${available} available in the shared collection. ` : ""}Choose items here or let the Agent retrieve relevant resources for the deck.</span></div>`;
  });
  $("#asset-grid").innerHTML = categories.visual_assets.length ? categories.visual_assets.map(asset => {
    const policyLabels = { available: "Available when useful", preferred: "Prefer when relevant", required_somewhere: "Must appear somewhere" };
    const policyOptions = Object.entries(policyLabels).map(([value, label]) => `<button type="button" role="option" aria-selected="${asset.usage_policy === value}" data-policy-value="${value}"><span>${label}</span>${asset.usage_policy === value ? "<b>✓</b>" : ""}</button>`).join("");
    return `<article class="asset-card">
    <button class="asset-preview preview-trigger" data-resource-id="${escapeHtml(asset.asset_id)}" aria-label="Preview ${escapeHtml(asset.name)}">${thumbnail(asset)}</button>
    <div class="asset-card-copy"><h4 title="${escapeHtml(asset.name)}">${escapeHtml(asset.name)}</h4><p>${escapeHtml(asset.semantic_role)}</p><span>${escapeHtml(resourceStatus(asset))}</span><button class="asset-open-file" type="button" data-resource-id="${escapeHtml(asset.asset_id)}" aria-label="Open ${escapeHtml(asset.name)} on this computer"><span aria-hidden="true">↗</span> Open file</button></div>
    <div class="asset-policy-control" data-asset-id="${escapeHtml(asset.asset_id)}"><button class="asset-policy-trigger" type="button" aria-haspopup="listbox" aria-expanded="false"><span>${policyLabels[asset.usage_policy] || policyLabels.available}</span><b aria-hidden="true">⌄</b></button><div class="asset-policy-options" role="listbox" hidden>${policyOptions}</div></div>
    <button class="asset-remove" type="button" data-asset-id="${escapeHtml(asset.asset_id)}" aria-label="Remove ${escapeHtml(asset.name)} from this project">×</button>
  </article>`;
  }).join("") : `<div class="empty-state"><strong>No visual assets yet</strong><span>Add a logo, photograph or illustration when you need one.</span></div>`;
  bindPreviewCards();
  bindProjectResourceRemoval();
  $$(".asset-policy-trigger").forEach(trigger => trigger.addEventListener("click", event => {
    event.stopPropagation();
    const control = trigger.closest(".asset-policy-control");
    const menu = control.querySelector(".asset-policy-options");
    const willOpen = menu.hidden;
    $$(".asset-policy-options").forEach(item => { item.hidden = true; });
    $$(".asset-policy-trigger").forEach(item => item.setAttribute("aria-expanded", "false"));
    menu.hidden = !willOpen;
    trigger.setAttribute("aria-expanded", String(willOpen));
  }));
  $$(".asset-policy-options button").forEach(option => option.addEventListener("click", async event => {
    event.stopPropagation();
    const control = option.closest(".asset-policy-control");
    await api("/api/assets", { method: "POST", body: JSON.stringify({ action: "update", location: state.selectedProjectPath, asset_id: control.dataset.assetId, usage_policy: option.dataset.policyValue, actor: "user_console" }) });
    await refreshProjectResources();
    showToast("Preference saved and shared with the Agent");
  }));
  $$(".asset-remove").forEach(button => button.addEventListener("click", async () => {
    const name = button.closest(".asset-card")?.querySelector("h4")?.textContent || "this visual asset";
    const confirmed = await confirmRemoval({
      title: `Remove ${name}?`,
      message: "It will no longer be available to this presentation. Its source file will remain in the project folder, so it can be restored later.",
      confirmLabel: "Remove from project",
    });
    if (!confirmed) return;
    await api("/api/assets", { method: "POST", body: JSON.stringify({ action: "remove", location: state.selectedProjectPath, asset_id: button.dataset.assetId, actor: "user_console" }) });
    await refreshProjectResources();
    showToast("Visual asset removed. Its source file is preserved.");
  }));
}

async function refreshProjectResources() {
  const resources = await api(`/api/resources?path=${encodeURIComponent(state.selectedProjectPath)}`);
  renderProjectResources(resources);
}

function bindProjectResourceRemoval() {
  $$(".resource-remove").forEach(button => button.addEventListener("click", async event => {
    event.stopPropagation();
    const name = button.closest(".resource-card")?.querySelector("h4")?.textContent || "this resource";
    const confirmed = await confirmRemoval({
      title: `Remove ${name}?`,
      message: "It will be removed from this project. The original item will stay in the shared collection and can be added again later.",
      confirmLabel: "Remove from project",
    });
    if (!confirmed) return;
    await api("/api/project-resources", { method: "POST", body: JSON.stringify({
      action: "remove",
      location: state.selectedProjectPath,
      category: button.dataset.resourceCategory,
      resource_id: button.dataset.resourceId,
      actor: "user_console",
    }) });
    await refreshProjectResources();
    showToast("Removed from this project. The shared collection is unchanged.");
  }));
}

function bindPreviewCards() {
  $$(".preview-trigger[data-resource-id]").forEach(element => {
    element.addEventListener("click", () => openPreview(element.dataset.resourceId));
  });
}

function tablePreview(sheets) {
  return sheets.map(sheet => `<section class="preview-sheet"><h4>${escapeHtml(sheet.name)}</h4><div class="table-scroll"><table>${sheet.rows.map(row => `<tr>${row.map(value => `<td>${escapeHtml(value)}</td>`).join("")}</tr>`).join("")}</table></div></section>`).join("");
}

function structuredPreview(value, depth = 0) {
  if (value === null || value === undefined) return "";
  if (["string", "number", "boolean"].includes(typeof value)) return `<p>${escapeHtml(value)}</p>`;
  if (Array.isArray(value)) return `<div class="structured-list">${value.map((item, index) => `<div class="structured-item">${typeof item === "object" ? structuredPreview(item, depth + 1) : `<span>${escapeHtml(item)}</span>`}</div>`).join("")}</div>`;
  const hiddenKeys = new Set(["schema_version", "slide_id", "deck_id"]);
  const entries = Object.entries(value).filter(([key]) => !hiddenKeys.has(key) && !key.endsWith("_path") && !key.endsWith("_id"));
  return `<div class="structured-object">${entries.map(([key, item]) => `<section><h4>${escapeHtml(displayKey(key))}</h4>${structuredPreview(item, depth + 1)}</section>`).join("")}</div>`;
}

async function openPreview(id, projectPath = state.selectedProjectPath) {
  const dialog = $("#preview-dialog");
  $("#preview-stage").innerHTML = `<div class="preview-loading">Preparing preview…</div>`;
  dialog.showModal();
  try {
    const preview = await api(`/api/resource-preview?path=${encodeURIComponent(projectPath)}&resource_id=${encodeURIComponent(id)}`);
    const isIcon = preview.category === "icons";
    $("#preview-title").textContent = isIcon ? cleanRole(preview.requested_role || preview.semantic_role || preview.name) : preview.name;
    $("#preview-category").textContent = humanLabel(preview.category).toUpperCase();
    $("#preview-description").textContent = isIcon ? `${preview.name} from ${preview.provenance || "the icon collection"}` : preview.description || "";
    $("#preview-stage").classList.toggle("icon-preview", isIcon);
    const fileUrl = `/api/resource-file?path=${encodeURIComponent(projectPath)}&resource_id=${encodeURIComponent(id)}`;
    renderPreview(preview, fileUrl);
  } catch (error) {
    $("#preview-stage").innerHTML = `<div class="empty-state"><strong>Preview unavailable</strong><span>${escapeHtml(error.message)}</span></div>`;
  }
}

function renderLibraries() {
  if (!state.overview) return;
  const visible = state.overview.libraries.filter(item => ["visual_references", "icons", "components"].includes(item.name));
  const symbols = { visual_references: "▧", icons: "◇", components: "▦" };
  const names = { visual_references: "Visual Inspiration", icons: "Icon Collection", components: "Reusable Components" };
  const descriptions = {
    visual_references: "Whole-slide examples that guide visual quality without supplying content",
    icons: "Canonical icons that remain clean and editable",
    components: "Reusable maps, diagrams and structured elements",
  };
  $("#library-grid").innerHTML = visible.map(item => `<article class="library-card" data-library="${item.name}"><button class="card-hit-target library-card-open" type="button" aria-label="Open ${names[item.name]}"></button><div class="library-symbol">${symbols[item.name]}</div><h4>${names[item.name]}</h4><p>${descriptions[item.name]}</p><code class="library-path" title="${escapeHtml(item.path)}">${escapeHtml(item.path)}</code><span class="library-count">${item.item_count ? `${item.item_count} ${item.item_count === 1 ? "item" : "items"}` : "No items yet"}</span><div class="library-card-actions"><button class="open-folder-button library-open-folder" type="button" data-library-folder="${item.name}"><span aria-hidden="true">↗</span> Open folder</button><span class="library-card-hint">Open collection <b aria-hidden="true">›</b></span></div></article>`).join("");
  $$(".library-card[data-library]").forEach(card => {
    card.querySelector(".library-card-open")?.addEventListener("click", () => openLibrary(card.dataset.library));
  });
  $$(".library-open-folder").forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    openLocalFolder("library", button.dataset.libraryFolder, button);
  }));
}

function optionList(values, selected, labels = {}) {
  return values.map(value => `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(labels[value] || humanLabel(value))}</option>`).join("");
}

async function loadDesign() {
  state.design = await api("/api/design");
  const settings = state.design.settings;
  const profiles = state.design.guidance_profiles;
  const selectedProfile = profiles.find(item => item.profile_id === settings.guidance_profile) || profiles[0];
  $("#guidance-profile").textContent = selectedProfile?.name || humanLabel(settings.guidance_profile);
  $("#guidance-description").textContent = selectedProfile?.description || "How the deck organizes and communicates its argument.";
  const densityLabels = { low: "Spacious", medium: "Balanced", high_consulting: "Information-rich" };
  $("#density-profile-label").textContent = densityLabels[settings.density_profile] || humanLabel(settings.density_profile);
  const densityBars = { low: 2, medium: 4, high_consulting: 6 };
  $("#density-summary-visual").innerHTML = Array.from({ length: densityBars[settings.density_profile] || 4 }, () => "<i></i>").join("");
  renderTypographyLabel(settings.display_font, settings.body_font);
  $("#type-preview-display").style.fontFamily = exactFontFamily(settings.display_font, "serif");
  $("#type-preview-body").style.fontFamily = exactFontFamily(settings.body_font, "sans-serif");
  const colorLabels = { warm_orange: "Warm orange", neutral: "Neutral", custom: "Custom" };
  const iconLabels = { tabler_warm_slot: "Tabler icons on warm tint", tabler_plain: "Plain Tabler icons", custom: "Custom icon style" };
  $("#visual-language-label").textContent = `${colorLabels[settings.color_system] || humanLabel(settings.color_system)} · ${iconLabels[settings.icon_style] || humanLabel(settings.icon_style)}`;
  $("#palette-preview").innerHTML = [settings.primary_color, settings.secondary_color, settings.highlight_color, settings.surface_color].map(color => `<i style="background:${escapeHtml(color)}"></i>`).join("");
  $("#icon-treatment-preview").className = `icon-treatment-preview ${settings.icon_style === "tabler_plain" ? "plain" : ""}`;
}

async function saveDesignSettings(values) {
  for (const [key, value] of Object.entries(values)) {
    await api("/api/config", { method: "POST", body: JSON.stringify({ key: `design.${key}`, value, scope: "user" }) });
  }
  await Promise.all([loadDesign(), loadOverview()]);
  showToast("Presentation defaults saved");
}

function fontPicker(name, selected, role) {
  return `<fieldset class="font-fieldset"><legend>${escapeHtml(name)}</legend><div class="font-grid">${state.design.font_choices.map(font => `<button type="button" class="font-choice ${font.name === selected ? "selected" : ""}" data-font-role="${role}" data-font="${escapeHtml(font.name)}" style="font-family:'${escapeHtml(font.name)}',sans-serif"><strong>${escapeHtml(font.name)}</strong><span>Ag 你好</span></button>`).join("")}</div></fieldset>`;
}

function openDesignEditor(mode) {
  state.designEditMode = mode;
  const settings = state.design.settings;
  if (mode === "guidance") {
    $("#design-dialog-title").textContent = "Edit communication design";
    const densityLabels = { low: "Spacious", medium: "Balanced", high_consulting: "Information-rich" };
    const densityNotes = { low: "Minimal content with generous whitespace", medium: "A balanced mix of message and evidence", high_consulting: "Dense, structured evidence for executive reading" };
    const densityBars = { low: 2, medium: 4, high_consulting: 6 };
    $("#design-fields").innerHTML = `<input id="design-guidance-profile" type="hidden" value="${escapeHtml(settings.guidance_profile)}"><input id="design-density-profile" type="hidden" value="${escapeHtml(settings.density_profile)}"><fieldset class="visual-fieldset"><legend>Communication approach</legend><div class="guidance-choice-grid">${state.design.guidance_profiles.map(profile => `<button type="button" class="guidance-choice ${profile.profile_id === settings.guidance_profile ? "selected" : ""}" data-profile="${escapeHtml(profile.profile_id)}"><span class="guidance-diagram profile-${escapeHtml(profile.profile_id)}"><i></i><b></b><b></b><em></em></span><strong>${escapeHtml(profile.name)}</strong><p>${escapeHtml(profile.description)}</p></button>`).join("")}</div></fieldset><fieldset class="visual-fieldset"><legend>Information density</legend><div class="density-editor-grid">${state.design.choices.density_profile.map(value => `<button type="button" class="density-editor-choice ${value === settings.density_profile ? "selected" : ""}" data-density="${value}"><span>${Array.from({ length: densityBars[value] }, () => "<i></i>").join("")}</span><strong>${densityLabels[value]}</strong><small>${densityNotes[value]}</small></button>`).join("")}</div></fieldset>`;
    $$(".guidance-choice").forEach(button => button.addEventListener("click", () => {
      $$(".guidance-choice").forEach(item => item.classList.toggle("selected", item === button));
      $("#design-guidance-profile").value = button.dataset.profile;
    }));
    $$(".density-editor-choice").forEach(button => button.addEventListener("click", () => {
      $$(".density-editor-choice").forEach(item => item.classList.toggle("selected", item === button));
      $("#design-density-profile").value = button.dataset.density;
    }));
  } else if (mode === "typography") {
    $("#design-dialog-title").textContent = "Choose typefaces";
    $("#design-fields").innerHTML = `<input id="design-display-font" type="hidden" value="${escapeHtml(settings.display_font)}"><input id="design-body-font" type="hidden" value="${escapeHtml(settings.body_font)}">${fontPicker("Display typeface", settings.display_font, "display")}${fontPicker("Body typeface", settings.body_font, "body")}`;
    $$(".font-choice").forEach(button => button.addEventListener("click", () => {
      $$(`.font-choice[data-font-role="${button.dataset.fontRole}"]`).forEach(item => item.classList.toggle("selected", item === button));
      $(`#design-${button.dataset.fontRole}-font`).value = button.dataset.font;
    }));
  } else {
    $("#design-dialog-title").textContent = "Edit visual language";
    const palettes = [
      { id: "warm_orange", name: "Warm orange", note: "Warm, decisive and editorial", colors: ["#D93900", "#EB8C00", "#E0301E", "#FCE4D6"] },
      { id: "neutral", name: "Neutral", note: "Quiet, analytical and restrained", colors: ["#292929", "#74706B", "#A7A29C", "#F0EEEB"] },
      { id: "custom", name: "Custom", note: "Use your own coordinated palette", colors: [settings.primary_color, settings.secondary_color, settings.highlight_color, settings.surface_color] },
    ];
    $("#design-fields").innerHTML = `<input id="design-color-system" type="hidden" value="${escapeHtml(settings.color_system)}"><input id="design-icon-style" type="hidden" value="${escapeHtml(settings.icon_style)}"><fieldset class="visual-fieldset"><legend>Color system</legend><div class="palette-choice-grid">${palettes.map(palette => `<button type="button" class="palette-choice ${palette.id === settings.color_system ? "selected" : ""}" data-palette="${palette.id}" data-colors='${JSON.stringify(palette.colors)}'><span>${palette.colors.map(color => `<i style="background:${color}"></i>`).join("")}</span><strong>${palette.name}</strong><small>${palette.note}</small></button>`).join("")}</div><div class="custom-color-grid"><label>Primary<input id="design-primary-color" type="color" value="${escapeHtml(settings.primary_color)}"></label><label>Secondary<input id="design-secondary-color" type="color" value="${escapeHtml(settings.secondary_color)}"></label><label>Highlight<input id="design-highlight-color" type="color" value="${escapeHtml(settings.highlight_color)}"></label><label>Soft surface<input id="design-surface-color" type="color" value="${escapeHtml(settings.surface_color)}"></label><label>Text<input id="design-text-color" type="color" value="${escapeHtml(settings.text_color)}"></label></div></fieldset><fieldset class="visual-fieldset"><legend>Icon treatment</legend><div class="icon-style-grid"><button type="button" class="icon-style-choice ${settings.icon_style === "tabler_warm_slot" ? "selected" : ""}" data-icon-style="tabler_warm_slot"><span class="icon-demo slot">◇</span><strong>Warm slot</strong><small>Line icons centred in a tinted allocation</small></button><button type="button" class="icon-style-choice ${settings.icon_style === "tabler_plain" ? "selected" : ""}" data-icon-style="tabler_plain"><span class="icon-demo plain">◇</span><strong>Plain line</strong><small>Clean icons without a visible container</small></button><button type="button" class="icon-style-choice ${settings.icon_style === "custom" ? "selected" : ""}" data-icon-style="custom"><span class="icon-demo custom">◇</span><strong>Custom</strong><small>Project-specific treatment supplied later</small></button></div></fieldset>`;
    $$(".palette-choice").forEach(button => button.addEventListener("click", () => {
      $$(".palette-choice").forEach(item => item.classList.toggle("selected", item === button));
      $("#design-color-system").value = button.dataset.palette;
      const colors = JSON.parse(button.dataset.colors);
      ["primary", "secondary", "highlight", "surface"].forEach((key, index) => { $(`#design-${key}-color`).value = colors[index]; });
    }));
    $$(".custom-color-grid input").forEach(input => input.addEventListener("input", () => {
      $("#design-color-system").value = "custom";
      $$(".palette-choice").forEach(item => item.classList.toggle("selected", item.dataset.palette === "custom"));
    }));
    $$(".icon-style-choice").forEach(button => button.addEventListener("click", () => {
      $$(".icon-style-choice").forEach(item => item.classList.toggle("selected", item === button));
      $("#design-icon-style").value = button.dataset.iconStyle;
    }));
  }
  $("#design-dialog").showModal();
}

async function loadProviders() {
  const payload = await api("/api/providers");
  state.providers = payload.providers;
  const adapterLabels = { openai: "OpenAI API", "custom-openai-compatible": "Compatible endpoint" };
  $("#provider-list").innerHTML = state.providers.map(provider => `<button class="provider-row" type="button" data-provider-role="${provider.role}"><div><strong>${escapeHtml(provider.label)}</strong><span>${provider.selection_policy === "force_configured" ? "Connected service for every image" : "Agent app first"}</span></div><div><b>${escapeHtml(adapterLabels[provider.configured_adapter] || humanLabel(provider.configured_adapter))} · ${escapeHtml(provider.model)}</b><small>${provider.base_url ? escapeHtml(provider.base_url) : provider.credential_available ? "Key saved securely" : `Key from ${escapeHtml(provider.api_key_env)}`}</small></div><span class="provider-row-hint">Configure <b aria-hidden="true">›</b></span></button>`).join("");
  $$(".provider-row[data-provider-role]").forEach(button => button.addEventListener("click", () => openProvider(button.dataset.providerRole)));
}

function openProvider(role) {
  const provider = state.providers.find(item => item.role === role);
  $("#provider-role").value = role;
  $("#provider-dialog-title").textContent = provider.label;
  $$("input[name='provider-policy']").forEach(input => { input.checked = input.value === provider.selection_policy; });
  setProviderAdapter(provider.configured_adapter);
  $("#provider-model").value = provider.model || "";
  $("#provider-base-url").value = provider.base_url || "";
  $("#provider-credential").value = "";
  $("#provider-credential").type = "password";
  $("#provider-credential-toggle").textContent = "Show";
  $("#provider-test-status").textContent = "";
  $("#provider-remove-credential").hidden = provider.credential_source !== "system_keychain";
  $("#provider-credential-note").textContent = provider.credential_source === "system_keychain"
    ? "A key is saved securely in your system keychain. Enter a new key only when you want to replace it."
    : provider.credential_source === "environment"
      ? `Using the ${provider.api_key_env} environment variable. You can save a different key for Slidecraft here.`
      : "No key is available yet. A saved key is kept in your system keychain and is never returned to this page.";
  $("#provider-dialog").showModal();
}

function setProviderAdapter(adapter) {
  $("#provider-adapter").value = adapter;
  $$(".provider-adapter-choice").forEach(button => button.classList.toggle("selected", button.dataset.adapter === adapter));
  $(".provider-endpoint-field").hidden = adapter !== "custom-openai-compatible";
}

const libraryNames = { visual_references: "Visual Inspiration", icons: "Icon Collection", components: "Reusable Components" };
const libraryDescriptions = {
  visual_references: "Whole-slide precedents that guide visual quality, density and composition. Their content is never reused.",
  icons: "Canonical icons that can be retrieved and restored cleanly.",
  components: "Editable maps, diagrams and other reusable presentation elements.",
};

async function openProjectPicker(category) {
  state.projectPickerCategory = category;
  state.selectedLibrary = category;
  $("#project-picker-title").textContent = `Choose ${libraryNames[category]}`;
  $("#project-picker-description").textContent = `${libraryDescriptions[category]} Selections are saved to this project and shared with the Agent.`;
  $("#project-picker-grid").innerHTML = `<div class="preview-loading">Loading collection…</div>`;
  $("#project-picker-dialog").showModal();
  await refreshProjectPicker();
}

async function refreshProjectPicker() {
  const category = state.projectPickerCategory;
  const library = await api(`/api/project-library-options?path=${encodeURIComponent(state.selectedProjectPath)}&category=${encodeURIComponent(category)}`);
  $("#project-picker-grid").innerHTML = library.items.length ? library.items.map(item => {
    const fileUrl = `/api/library-file?name=${encodeURIComponent(category)}&item_id=${encodeURIComponent(item.item_id)}`;
    const preview = item.media_type.startsWith("image/") ? `<img src="${fileUrl}" alt="" loading="lazy">` : `<span>${escapeHtml(item.filename.split(".").pop().slice(0, 5).toUpperCase())}</span>`;
    return `<article class="project-picker-item ${item.selected ? "selected" : ""}"><button class="project-picker-preview" type="button" data-library-item="${escapeHtml(item.item_id)}">${preview}</button><div><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.description || "The Agent can complete retrieval details later")}</p></div><button class="project-picker-add" type="button" data-library-item="${escapeHtml(item.item_id)}" ${item.selected ? "disabled" : ""}>${item.selected ? "Added" : "Add"}</button></article>`;
  }).join("") : `<div class="empty-state"><strong>This collection is empty</strong><span>Add reusable resources here or ask your Agent to prepare them.</span></div>`;
  $$(".project-picker-preview").forEach(button => button.addEventListener("click", () => openLibraryPreview(button.dataset.libraryItem)));
  $$(".project-picker-add:not(:disabled)").forEach(button => button.addEventListener("click", async () => {
    await api("/api/project-resources", { method: "POST", body: JSON.stringify({
      action: "add",
      location: state.selectedProjectPath,
      category,
      item_id: button.dataset.libraryItem,
      actor: "user_console",
    }) });
    await Promise.all([refreshProjectPicker(), refreshProjectResources()]);
    showToast("Added to this project and shared with the Agent");
  }));
}

async function openLibrary(name) {
  state.selectedLibrary = name;
  $("#library-dialog-title").textContent = libraryNames[name];
  $("#library-dialog-description").textContent = libraryDescriptions[name];
  $("#library-item-grid").innerHTML = `<div class="preview-loading">Loading collection…</div>`;
  $("#library-dialog").showModal();
  await refreshLibrary();
}

function libraryThumbnail(item) {
  const preview = item.preview_path ? "&preview=1" : "";
  const url = `/api/library-file?name=${encodeURIComponent(state.selectedLibrary)}&item_id=${encodeURIComponent(item.item_id)}${preview}`;
  if (item.preview_path) return `<img src="${url}" alt="" loading="lazy">`;
  if (item.media_type.startsWith("image/")) return `<img src="${url}" alt="" loading="lazy">`;
  return `<span>${escapeHtml(item.name.split(".").pop().slice(0, 5).toUpperCase())}</span>`;
}

async function refreshLibrary() {
  const library = await api(`/api/library-items?name=${encodeURIComponent(state.selectedLibrary)}`);
  $("#library-location").value = library.path;
  $("#library-count").textContent = `${library.item_count} ${library.item_count === 1 ? "item" : "items"}`;
  $("#library-item-grid").innerHTML = library.items.length ? library.items.map(item => `<article class="library-item"><button class="library-item-preview" data-library-item="${item.item_id}" aria-label="Preview ${escapeHtml(item.name)}">${libraryThumbnail(item)}</button><div class="library-item-copy"><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.description || "Description can be completed later by your Agent")}</p><span>${item.tags?.length ? escapeHtml(item.tags.join(" · ")) : `${formatBytes(item.size_bytes)} · ${item.metadata_status === "ready" ? "Ready for retrieval" : "Needs details"}`}</span></div><div class="library-item-actions"><button class="library-item-edit" data-library-item="${item.item_id}" aria-label="Edit details for ${escapeHtml(item.name)}">•••</button><button class="library-item-remove" data-library-item="${item.item_id}" data-library-item-name="${escapeHtml(item.name)}" aria-label="Remove ${escapeHtml(item.name)}">×</button></div></article>`).join("") : `<div class="empty-state"><strong>This collection is empty</strong><span>Add files here and your Agent can complete their retrieval details later.</span></div>`;
  $$(".library-item-preview").forEach(button => button.addEventListener("click", () => openLibraryPreview(button.dataset.libraryItem)));
  $$(".library-item-edit").forEach(button => button.addEventListener("click", () => openLibraryMetadata(library.items.find(item => item.item_id === button.dataset.libraryItem))));
  $$(".library-item-remove").forEach(button => button.addEventListener("click", async () => {
    const confirmed = await confirmRemoval({
      title: `Delete ${button.dataset.libraryItemName}?`,
      message: "This removes the file from the shared collection. Projects that already selected it keep their project record, though the original library file will no longer be available.",
      confirmLabel: "Delete from collection",
    });
    if (!confirmed) return;
    await api("/api/library-items", { method: "POST", body: JSON.stringify({ action: "delete", name: state.selectedLibrary, item_id: button.dataset.libraryItem }) });
    await Promise.all([refreshLibrary(), loadOverview()]);
    showToast("Resource removed");
  }));
}

function openLibraryMetadata(item) {
  state.selectedLibraryItem = item;
  $("#library-metadata-title").textContent = item.name || "Resource details";
  $("#library-metadata-item-id").value = item.item_id;
  $("#library-metadata-name").value = item.name || "";
  $("#library-metadata-description").value = item.description || "";
  $("#library-metadata-tags").value = (item.tags || []).join(", ");
  $("#library-metadata-dialog").showModal();
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

async function openLibraryPreview(itemId) {
  const preview = await api(`/api/library-preview?name=${encodeURIComponent(state.selectedLibrary)}&item_id=${encodeURIComponent(itemId)}`);
  $("#preview-title").textContent = preview.name;
  $("#preview-category").textContent = libraryNames[state.selectedLibrary].toUpperCase();
  $("#preview-description").textContent = preview.description || "";
  $("#preview-stage").classList.toggle("icon-preview", state.selectedLibrary === "icons");
  const fileUrl = `/api/library-file?name=${encodeURIComponent(state.selectedLibrary)}&item_id=${encodeURIComponent(itemId)}`;
  renderPreview(preview, fileUrl);
  $("#preview-dialog").showModal();
}

function renderPreview(preview, fileUrl) {
  if (preview.kind === "image") $("#preview-stage").innerHTML = `<img class="preview-image" src="${fileUrl}" alt="${escapeHtml(preview.name)}">`;
  else if (preview.kind === "embedded_image") $("#preview-stage").innerHTML = `<img class="preview-image" src="${escapeHtml(preview.source)}" alt="${escapeHtml(preview.name)}">`;
  else if (preview.kind === "pdf") $("#preview-stage").innerHTML = `<iframe class="preview-pdf" src="${fileUrl}" title="${escapeHtml(preview.name)}"></iframe>`;
  else if (preview.kind === "pages") $("#preview-stage").innerHTML = `<div class="page-preview-grid">${preview.images.map((source, index) => `<figure><img src="${source}" alt="${escapeHtml(preview.name)} page ${index + 1}"><figcaption>${index + 1}</figcaption></figure>`).join("")}</div>${preview.truncated ? `<p class="preview-note">Showing the first ${preview.page_count} pages.</p>` : ""}`;
  else if (preview.kind === "table") $("#preview-stage").innerHTML = tablePreview(preview.sheets);
  else if (preview.kind === "structured") $("#preview-stage").innerHTML = `<article class="structured-preview">${structuredPreview(preview.value)}</article>`;
  else if (["document", "text"].includes(preview.kind)) $("#preview-stage").innerHTML = `<article class="document-preview">${escapeHtml(preview.text || "No readable text found").replaceAll("\n", "<br>")}</article>`;
  else $("#preview-stage").innerHTML = `<div class="empty-state"><strong>Preview unavailable</strong><span>${escapeHtml(preview.message)}</span><a class="quiet-button" href="${fileUrl}" target="_blank">Open file</a></div>`;
}

async function loadHealth(force = false) {
  $("#health-grid").innerHTML = `<div class="loading-card">Inspecting local capabilities…</div>`;
  state.health = await api(`/api/health${force ? "?refresh=1" : ""}`);
  const powerpointNote = state.health.construction.microsoft_powerpoint_mac
    ? state.health.construction.powerpoint_automation_authorized
      ? "Office render checks ready"
      : "Enable Office render checks"
    : "Install PowerPoint to add Office render checks";
  const samNote = state.health.segmentation.sam2
    ? `Ready with Torch ${state.health.segmentation.torch.version}`
    : state.health.segmentation.torch.installed
      ? "Install SAM 2 to add irregular-shape boundaries"
      : "Install the segmentation extra to add SAM 2";
  const cards = [
    ["OpenCV", state.health.measurement.opencv, state.health.measurement.tesseract_binary ? "OCR ready" : "Install Tesseract to add OCR"],
    ["SAM 2", state.health.segmentation.sam2, samNote],
    ["PowerPoint for Mac", state.health.construction.microsoft_powerpoint_mac, powerpointNote],
    ["Agent connection", state.health.ready_for_host_mode, state.health.slidecraft.platform],
  ];
  $("#health-grid").innerHTML = cards.map(([name, ready, note]) => `<article class="health-card"><div class="library-symbol">${ready ? "✓" : "·"}</div><h4>${name}</h4><p>${escapeHtml(note)}</p><span class="project-status ${ready ? "" : "unavailable"}">${ready ? "Ready" : "Unavailable"}</span></article>`).join("");
  $("#health-checked-at").textContent = `Checked ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function navigate(view) {
  const activeNavigation = $(`.nav-item[data-view="${view}"]`);
  $$(".nav-item").forEach(item => item.classList.toggle("active", item === activeNavigation));
  $$(".view").forEach(item => item.classList.toggle("active", item.id === `view-${view}`));
  const contexts = { overview: "WORKSPACE", projects: "PRESENTATIONS", design: "PRESENTATION DESIGN", resources: "SHARED LIBRARY", system: "LOCAL RUNTIME" };
  const descriptions = {
    projects: "Presentation workspaces stored in folders you control.",
    design: "Set the communication approach, typography, colors and icon treatment used across presentations.",
  };
  $("#view-eyebrow").textContent = contexts[view];
  $("#view-title").textContent = activeNavigation.querySelector(".nav-label").textContent;
  $("#view-description").textContent = descriptions[view] || "";
  $("#view-description").hidden = !descriptions[view];
  if (view === "system") Promise.all([loadHealth(), loadProviders()]).catch(error => showToast(error.message));
}

$$('.nav-item').forEach(button => button.addEventListener('click', () => navigate(button.dataset.view)));
$$('[data-go]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.go)));
$("#new-project-button").addEventListener("click", () => $("#project-dialog").showModal());
$("#health-refresh").addEventListener("click", () => Promise.all([loadHealth(true), loadProviders()]));
$("#upload-asset-button").addEventListener("click", () => {
  if (!state.selectedProjectPath) return showToast("Create a project first");
  $("#asset-file-input").click();
});
$("#upload-material-button").addEventListener("click", () => {
  if (!state.selectedProjectPath) return showToast("Create a project first");
  $("#material-file-input").click();
});
$$('.project-library-choose').forEach(button => button.addEventListener('click', () => openProjectPicker(button.dataset.category)));
$("#project-picker-close").addEventListener("click", () => $("#project-picker-dialog").close());
$("#project-back").addEventListener("click", () => {
  $("#project-workspace-panel").hidden = true;
  $("#projects-list-panel").hidden = false;
  state.selectedProjectPath = null;
});
$$('.resource-tab').forEach(button => button.addEventListener('click', () => {
  $$('.resource-tab').forEach(item => item.classList.toggle('active', item === button));
  $$('.resource-pane').forEach(item => item.classList.toggle('active', item.dataset.resourcePane === button.dataset.resourceTab));
}));
$("#asset-file-input").addEventListener("change", event => {
  state.selectedAssetFile = event.target.files[0] || null;
  if (!state.selectedAssetFile) return;
  $("#selected-file").textContent = state.selectedAssetFile.name;
  $("#asset-role").value = state.selectedAssetFile.name.replace(/\.[^.]+$/, "").replaceAll(/[_-]+/g, " ");
  $("#asset-policy").value = "available";
  $$(".asset-use-choice").forEach(button => button.classList.toggle("selected", button.dataset.policy === "available"));
  $("#asset-dialog").showModal();
});
$("#material-file-input").addEventListener("change", async event => {
  const files = [...event.target.files];
  if (!files.length || !state.selectedProjectPath) return;
  try {
    for (const file of files) {
      await api("/api/materials", { method: "POST", body: JSON.stringify({
        location: state.selectedProjectPath,
        filename: file.name,
        content_base64: await fileBase64(file),
        actor: "user_console",
      }) });
    }
    event.target.value = "";
    await Promise.all([refreshProjectResources(), loadOverview()]);
    showToast(`${files.length} ${files.length === 1 ? "material" : "materials"} added. The current plan is unchanged.`);
  } catch (error) { showToast(error.message); }
});
$("#preview-close").addEventListener("click", () => $("#preview-dialog").close());
$("#library-close").addEventListener("click", () => $("#library-dialog").close());
$$(".asset-use-choice").forEach(button => button.addEventListener("click", () => {
  $("#asset-policy").value = button.dataset.policy;
  $$(".asset-use-choice").forEach(item => item.classList.toggle("selected", item === button));
}));
document.addEventListener("click", event => {
  if (event.target.closest(".asset-policy-control")) return;
  $$(".asset-policy-options").forEach(item => { item.hidden = true; });
  $$(".asset-policy-trigger").forEach(item => item.setAttribute("aria-expanded", "false"));
});
$("#edit-guidance-card").addEventListener("click", () => openDesignEditor("guidance"));
$("#edit-typography-card").addEventListener("click", () => openDesignEditor("typography"));
$("#edit-visual-language-card").addEventListener("click", () => openDesignEditor("visual_language"));
$("#project-form").addEventListener("submit", async event => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const body = Object.fromEntries([...form.entries()].filter(([, value]) => value));
  try {
    await api("/api/projects", { method: "POST", body: JSON.stringify(body) });
    $("#project-dialog").close();
    formElement.reset();
    await loadOverview();
    navigate("projects");
    showToast("Project created");
  } catch (error) { showToast(error.message); }
});
$("#asset-form").addEventListener("submit", async event => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  if (!state.selectedAssetFile || !state.selectedProjectPath) return;
  try {
    await api("/api/assets", { method: "POST", body: JSON.stringify({
      location: state.selectedProjectPath,
      filename: state.selectedAssetFile.name,
      content_base64: await fileBase64(state.selectedAssetFile),
      semantic_role: $("#asset-role").value,
      usage_policy: $("#asset-policy").value,
    }) });
    $("#asset-dialog").close();
    state.selectedAssetFile = null;
    $("#asset-file-input").value = "";
    await openProject(state.selectedProjectPath);
    showToast("Asset added. Existing plans are unchanged.");
  } catch (error) { showToast(error.message); }
});

async function fileBase64(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  bytes.forEach(value => { binary += String.fromCharCode(value); });
  return btoa(binary);
}

$$(".provider-adapter-choice").forEach(button => button.addEventListener("click", () => setProviderAdapter(button.dataset.adapter)));
$("#provider-credential-toggle").addEventListener("click", () => {
  const input = $("#provider-credential");
  input.type = input.type === "password" ? "text" : "password";
  $("#provider-credential-toggle").textContent = input.type === "password" ? "Show" : "Hide";
});

$("#provider-test").addEventListener("click", async () => {
  const status = $("#provider-test-status");
  status.className = "provider-test-status testing";
  status.textContent = "Checking this connection…";
  try {
    const payload = await api("/api/provider-connection-test", { method: "POST", body: JSON.stringify({
      role: $("#provider-role").value,
      configured_adapter: $("#provider-adapter").value,
      model: $("#provider-model").value.trim(),
      base_url: $("#provider-base-url").value.trim(),
      credential: $("#provider-credential").value.trim() || undefined,
    }) });
    status.className = "provider-test-status success";
    status.textContent = `Connected. ${payload.model} is available.`;
  } catch (error) {
    status.className = "provider-test-status error";
    status.textContent = error.message;
  }
});

$("#provider-remove-credential").addEventListener("click", async () => {
  const provider = state.providers.find(item => item.role === $("#provider-role").value);
  const confirmed = await confirmRemoval({
    title: "Remove the saved API key?",
    message: "This removes the saved key from your system keychain. Slidecraft can still use a key supplied through the named environment variable.",
    confirmLabel: "Remove saved key",
  });
  if (!confirmed) return;
  await api("/api/provider-credential", { method: "POST", body: JSON.stringify({ action: "delete", credential_id: provider.credential_id }) });
  $("#provider-dialog").close();
  await loadProviders();
  openProvider(provider.role);
  showToast("Saved API key removed");
});

$("#provider-form").addEventListener("submit", async event => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  const role = $("#provider-role").value;
  try {
    const provider = state.providers.find(item => item.role === role);
    const values = {
      selection_policy: $("input[name='provider-policy']:checked").value,
      configured_adapter: $("#provider-adapter").value,
      model: $("#provider-model").value.trim(),
      base_url: $("#provider-base-url").value.trim(),
    };
    for (const [key, value] of Object.entries(values)) {
      await api("/api/config", { method: "POST", body: JSON.stringify({ key: `providers.${role}.${key}`, value, scope: "user" }) });
    }
    const credential = $("#provider-credential").value.trim();
    if (credential) {
      await api("/api/provider-credential", { method: "POST", body: JSON.stringify({ credential_id: provider.credential_id, credential }) });
    }
    $("#provider-credential").value = "";
    $("#provider-dialog").close();
    await Promise.all([loadProviders(), loadOverview()]);
    showToast("Connection saved");
  } catch (error) { showToast(error.message); }
});

$("#library-save-location").addEventListener("click", async () => {
  try {
    await api("/api/library-location", { method: "POST", body: JSON.stringify({ name: state.selectedLibrary, location: $("#library-location").value.trim() }) });
    await Promise.all([refreshLibrary(), loadOverview()]);
    showToast("Collection location saved");
  } catch (error) { showToast(error.message); }
});
$("#library-open-folder").addEventListener("click", () => {
  if (state.selectedLibrary) openLocalFolder("library", state.selectedLibrary, $("#library-open-folder"));
});
$("#workspace-open-folder").addEventListener("click", () => {
  if (state.selectedProjectPath) openLocalFolder("project", state.selectedProjectPath, $("#workspace-open-folder"));
});

$("#library-add-files").addEventListener("click", () => $("#library-file-input").click());
$("#library-file-input").addEventListener("change", async event => {
  const files = [...event.target.files];
  if (!files.length) return;
  try {
    for (const file of files) {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      bytes.forEach(value => { binary += String.fromCharCode(value); });
      await api("/api/library-items", { method: "POST", body: JSON.stringify({ name: state.selectedLibrary, filename: file.name, content_base64: btoa(binary) }) });
    }
    event.target.value = "";
    await Promise.all([refreshLibrary(), loadOverview()]);
    showToast(`${files.length} ${files.length === 1 ? "file" : "files"} added`);
  } catch (error) { showToast(error.message); }
});

$("#library-metadata-form").addEventListener("submit", async event => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  try {
    const tags = $("#library-metadata-tags").value.split(",").map(value => value.trim()).filter(Boolean);
    await api("/api/library-items", { method: "POST", body: JSON.stringify({
      action: "update",
      name: state.selectedLibrary,
      item_id: $("#library-metadata-item-id").value,
      metadata: {
        name: $("#library-metadata-name").value.trim(),
        description: $("#library-metadata-description").value.trim(),
        tags,
      },
    }) });
    $("#library-metadata-dialog").close();
    await refreshLibrary();
    showToast("Resource details saved");
  } catch (error) { showToast(error.message); }
});

$("#design-form").addEventListener("submit", async event => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  try {
    if (state.designEditMode === "guidance") {
      await saveDesignSettings({
        guidance_profile: $("#design-guidance-profile").value,
        density_profile: $("#design-density-profile").value,
      });
    } else if (state.designEditMode === "typography") {
      await saveDesignSettings({
        display_font: $("#design-display-font").value.trim(),
        body_font: $("#design-body-font").value.trim(),
      });
    } else {
      await saveDesignSettings({
        color_system: $("#design-color-system").value,
        icon_style: $("#design-icon-style").value,
        primary_color: $("#design-primary-color").value,
        secondary_color: $("#design-secondary-color").value,
        highlight_color: $("#design-highlight-color").value,
        surface_color: $("#design-surface-color").value,
        text_color: $("#design-text-color").value,
      });
    }
    $("#design-dialog").close();
  } catch (error) { showToast(error.message); }
});

$("#removal-cancel").addEventListener("click", () => finishRemovalConfirmation(false));
$("#removal-confirm").addEventListener("click", () => finishRemovalConfirmation(true));
$("#removal-dialog").addEventListener("cancel", event => {
  event.preventDefault();
  finishRemovalConfirmation(false);
});

document.addEventListener("click", event => {
  const button = event.target.closest(".resource-open-file, .asset-open-file");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  openLocalResource(button.dataset.resourceId, button);
});

setInterval(async () => {
  if (!state.selectedProjectPath || document.hidden) return;
  try {
    const resources = await api(`/api/resources?path=${encodeURIComponent(state.selectedProjectPath)}`);
    renderProjectResources(resources);
  } catch (_) { /* A temporary folder or network interruption should not disturb the user. */ }
}, 5000);

setInterval(() => {
  if (!document.hidden && $("#view-system").classList.contains("active")) loadHealth().catch(() => {});
}, 60000);

Promise.all([loadOverview(), loadDesign(), loadHealth(), loadProviders()]).catch(error => showToast(error.message));
