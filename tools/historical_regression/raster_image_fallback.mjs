import fs from "node:fs/promises";
import path from "node:path";


function contentTypeFor(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === ".svg") return "image/svg+xml";
  if (extension === ".jpg" || extension === ".jpeg") return "image/jpeg";
  return "image/png";
}


/**
 * Add one slide understanding image entity as one editable PowerPoint picture object.
 * The caller supplies pxToSlideBox so this helper remains independent of slide size.
 */
export async function addStep4ImageEntity(slide, entity, pxToSlideBox) {
  if (entity.kind !== "image") throw new Error(`Expected image entity, received ${entity.kind}`);
  const imageContract = entity.measurement.image_object;
  if (!imageContract) throw new Error(`Image entity ${entity.id} has no image_object measurement`);

  const exactSource = entity.upstream_asset_mapping?.canonical_file ?? null;
  const sourcePath = exactSource ?? imageContract.screenshot_crop_absolute;
  const bytes = await fs.readFile(sourcePath);
  const position = pxToSlideBox(entity.measurement.layout_bbox.px);
  const picture = slide.images.add({
    blob: new Uint8Array(bytes),
    contentType: contentTypeFor(sourcePath),
    alt: entity.semantic_description ?? entity.role ?? "Reconstructed slide image",
    fit: imageContract.crop_mode === "contain" ? "contain" : "fill",
    position,
  });
  picture.name = `${entity.id}.${exactSource ? "exact_upstream_image" : "screenshot_fallback"}`;
  picture.rotation = imageContract.rotation_degrees ?? 0;
  picture.lockAspectRatio = imageContract.preserve_aspect_ratio ?? true;
  return {
    entityId: entity.id,
    sourcePath,
    route: exactSource ? "canonical_icon_or_image_asset" : "raster_fallback",
    powerpointObject: picture.name,
  };
}
