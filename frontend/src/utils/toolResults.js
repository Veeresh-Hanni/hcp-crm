const DEFAULT_MATERIALS = {
  brochures: false,
  samples: false,
  presentation: false,
  study: false,
};

function compactPatch(patch) {
  return Object.fromEntries(
    Object.entries(patch).filter(([, value]) => {
      if (typeof value === "string") return value.trim();
      if (Array.isArray(value)) return value.length > 0;
      if (value && typeof value === "object") return Object.values(value).some(Boolean);
      return value != null;
    })
  );
}

function normalizeMaterials(materials = {}) {
  return Object.fromEntries(
    Object.entries(materials).map(([key, value]) => [key.toLowerCase().replace(/\s+/g, "_"), Boolean(value)])
  );
}

export function normalizeToolPatch(action) {
  const data = action?.data || {};
  const interaction = data.interaction;

  if (!interaction) return {};

  return compactPatch({
    hcp_name: interaction.hcp_name,
    interaction_date: interaction.interaction_date?.slice(0, 10),
    type: interaction.type,
    sentiment: interaction.sentiment,
    next_steps: interaction.next_steps,
    discussion_product:
      interaction.product_names?.join(", ") || interaction.summary || interaction.discussion_notes,
    discussion_notes: interaction.discussion_notes || interaction.summary,
    materials_shared: normalizeMaterials(interaction.materials_shared),
  });
}

export { DEFAULT_MATERIALS };
