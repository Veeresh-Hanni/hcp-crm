const MATERIAL_ALIASES = {
  brochures: ["brochure", "brochures", "leaflet", "leaflets"],
  samples: ["sample", "samples"],
  presentation: ["presentation", "slides", "deck"],
  study: ["study", "paper", "clinical data", "efficacy data"],
};

const DEFAULT_MATERIALS = {
  brochures: false,
  samples: false,
  presentation: false,
  study: false,
};

const toTitleName = (name) =>
  name
    ?.trim()
    .replace(/\s+/g, " ")
    .replace(/\b([a-z])/gi, (m) => m.toUpperCase());

const today = () => new Date().toISOString().slice(0, 10);

function inferDate(text) {
  const lower = text.toLowerCase();
  if (/\b(today|this morning|this afternoon|tonight)\b/.test(lower)) return today();
  if (/\byesterday\b/.test(lower)) {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  }
  const iso = text.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
  if (iso) return iso[1];
  return "";
}

function inferHcpName(text) {
  const match =
    text.match(/\bDr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/) ||
    text.match(/\bdoctor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i);
  return match ? `Dr. ${toTitleName(match[1])}` : "";
}

function inferSentiment(text) {
  const lower = text.toLowerCase();
  if (/\b(negative|unhappy|concerned|skeptical|not interested|declined)\b/.test(lower)) return "negative";
  if (/\b(positive|interested|happy|receptive|enthusiastic|agreed)\b/.test(lower)) return "positive";
  if (/\b(neutral|mixed|no clear)\b/.test(lower)) return "neutral";
  return "";
}

function inferType(text) {
  const lower = text.toLowerCase();
  if (/\b(call|called|phone)\b/.test(lower)) return "call";
  if (/\b(email|emailed)\b/.test(lower)) return "email";
  if (/\b(virtual|zoom|teams|video)\b/.test(lower)) return "virtual";
  if (/\b(met|meeting|visit|visited)\b/.test(lower)) return "visit";
  return "";
}

function inferMaterials(text) {
  const lower = text.toLowerCase();
  return Object.fromEntries(
    Object.entries(MATERIAL_ALIASES).map(([key, aliases]) => [
      key,
      aliases.some((alias) => lower.includes(alias)),
    ])
  );
}

function inferProducts(text) {
  const candidates = new Set();
  const productPattern = /\b(product\s+[A-Z]|[A-Z][a-zA-Z]+(?:Plus|Calm|XR|X|Data)?)\b/g;
  for (const match of text.matchAll(productPattern)) {
    const value = match[1].trim();
    if (!/^Dr\.?$/i.test(value) && !/^Today$/i.test(value)) candidates.add(value);
  }
  const discussed = text.match(/\bdiscussed\s+(.+?)(?:\.|,|\band\b|\bwith\b|\bthe sentiment\b|$)/i);
  if (discussed?.[1]) candidates.add(discussed[1].trim());
  return Array.from(candidates).slice(0, 4).join(", ");
}

function inferNextSteps(text) {
  const match = text.match(/\b(?:next step|follow up|follow-up|bring up|send)\s+(.+?)(?:\.|$)/i);
  return match ? match[0].trim() : "";
}

function parseLogPatch(text) {
  const materials = inferMaterials(text);
  return {
    hcp_name: inferHcpName(text),
    interaction_date: inferDate(text),
    type: inferType(text),
    discussion_product: inferProducts(text),
    sentiment: inferSentiment(text),
    materials_shared: materials,
    discussion_notes: text,
    next_steps: inferNextSteps(text),
  };
}

function parseEditPatch(text) {
  const patch = {};
  const hcpName = inferHcpName(text);
  const sentiment = inferSentiment(text);
  const date = inferDate(text);
  const type = inferType(text);
  const products = inferProducts(text);
  const materials = inferMaterials(text);

  if (hcpName) patch.hcp_name = hcpName;
  if (sentiment) patch.sentiment = sentiment;
  if (date) patch.interaction_date = date;
  if (type) patch.type = type;
  if (products) patch.discussion_product = products;
  if (Object.values(materials).some(Boolean)) patch.materials_shared = materials;
  if (/\b(notes?|discussion)\b/i.test(text)) patch.discussion_notes = text;
  return patch;
}

function detectIntent(text) {
  const lower = text.toLowerCase();
  if (/\b(compliance|off-label|flag|review)\b/.test(lower)) return "compliance";
  if (/\b(what should|next visit|bring up|suggest|recommend|next best)\b/.test(lower)) return "suggest";
  if (/\b(latest|history|last|who is|look up|lookup)\b/.test(lower)) return "lookup";
  if (/\b(actually|change|correct|edit|sorry|instead|was actually)\b/.test(lower)) return "edit";
  if (/\b(met|visited|called|emailed|discussed|shared|sentiment|sample|brochure)\b/.test(lower)) return "log";
  return "chitchat";
}

function compactPatch(patch) {
  return Object.fromEntries(
    Object.entries(patch).filter(([, value]) => {
      if (typeof value === "string") return value.trim();
      if (value && typeof value === "object") return Object.values(value).some(Boolean);
      return value != null;
    })
  );
}

export function runLocalAgent(text, currentDraft = {}) {
  const intent = detectIntent(text);

  if (intent === "log") {
    const formPatch = compactPatch(parseLogPatch(text));
    return {
      reply: "I extracted the interaction details and updated the form on the left.",
      tool_actions: [{ tool: "log_interaction", status: "ok", data: { form_patch: formPatch } }],
    };
  }

  if (intent === "edit") {
    const formPatch = compactPatch(parseEditPatch(text));
    return {
      reply: Object.keys(formPatch).length
        ? "Updated those fields and kept the rest of the interaction intact."
        : "I need one more detail about what should change.",
      tool_actions: [
        {
          tool: "edit_interaction",
          status: Object.keys(formPatch).length ? "ok" : "needs_clarification",
          data: { form_patch: formPatch },
        },
      ],
    };
  }

  if (intent === "lookup") {
    const name = inferHcpName(text) || currentDraft.hcp_name || "this HCP";
    return {
      reply: `${name}: using the current draft context, I can help review recent notes, sentiment, and planned follow-up.`,
      tool_actions: [{ tool: "lookup_hcp", status: "ok", data: { hcp_name: name } }],
    };
  }

  if (intent === "suggest") {
    const product = currentDraft.discussion_product || "the discussed product";
    return {
      reply: `Suggested next talking point: ask about barriers to adopting ${product} and offer follow-up clinical evidence.`,
      tool_actions: [
        {
          tool: "suggest_next_best_action",
          status: "ok",
          data: { recommended_talking_point: `Discuss adoption barriers for ${product}` },
        },
      ],
    };
  }

  if (intent === "compliance") {
    const flagged = /\b(guarantee|cure|best|better than|off-label)\b/i.test(currentDraft.discussion_notes || text);
    return {
      reply: flagged
        ? "Compliance review flagged language that may need approval review."
        : "Compliance review is clear based on the current draft.",
      tool_actions: [
        {
          tool: "compliance_check",
          status: flagged ? "flagged" : "clear",
          data: { reasons: flagged ? ["Potentially unsupported claim language."] : [] },
        },
      ],
    };
  }

  return {
    reply: "Tell me about an HCP interaction, or ask me to edit the form.",
    tool_actions: [],
  };
}

export function normalizeToolPatch(action) {
  const data = action?.data || {};
  if (data.form_patch) return data.form_patch;

  if (action?.tool === "log_interaction" && data.interaction) {
    const interaction = data.interaction;
    return compactPatch({
      hcp_name: interaction.hcp_name,
      interaction_date: interaction.interaction_date?.slice(0, 10),
      type: interaction.type,
      sentiment: interaction.sentiment,
      next_steps: interaction.next_steps,
      discussion_notes: interaction.summary,
    });
  }

  if (action?.tool === "edit_interaction" && data.interaction) {
    const interaction = data.interaction;
    return compactPatch({
      sentiment: interaction.sentiment,
      discussion_notes: interaction.discussion_notes || interaction.summary,
      next_steps: interaction.next_steps,
    });
  }

  return {};
}

export { DEFAULT_MATERIALS };
