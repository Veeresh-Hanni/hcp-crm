import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../api/client";
import {
  draftToInteractionPatch,
  draftToInteractionPayload,
  mergeDraftPatch,
  normalizeToolPatch,
  runLocalAgent,
} from "../utils/localAgent";

const findPrimaryTool = (result) => result.tool_actions?.[0];

async function ensureHcp(name) {
  const trimmedName = name?.trim();
  if (!trimmedName) return null;

  const matches = await api.searchHcps(trimmedName).catch(() => []);
  const exact = matches.find((hcp) => hcp.name.toLowerCase() === trimmedName.toLowerCase());
  if (exact) return exact;

  return api.createHcp({ name: trimmedName, contact_info: {} });
}

async function persistToolAction(localResult, state, repId) {
  const action = findPrimaryTool(localResult);
  if (!action) return localResult;

  const currentDraft = state.interactions.interactionDraft;
  const currentInteractionId = state.interactions.currentInteractionId;
  const patch = normalizeToolPatch(action);
  const nextDraft = mergeDraftPatch(currentDraft, patch);

  try {
    if (action.tool === "log_interaction") {
      const hcp = await ensureHcp(nextDraft.hcp_name);
      if (!hcp) {
        return {
          ...localResult,
          reply: "I filled the form, but I need an HCP name before I can save it.",
          tool_actions: [{ ...action, status: "needs_clarification" }],
        };
      }

      const interaction = await api.createInteraction(repId, draftToInteractionPayload(nextDraft, hcp.id));
      return {
        ...localResult,
        reply: `Created interaction for ${nextDraft.hcp_name} and saved it to the database.`,
        tool_actions: [
          {
            ...action,
            status: "ok",
            data: { ...action.data, hcp, interaction, current_interaction_id: interaction.id },
          },
        ],
      };
    }

    if (action.tool === "edit_interaction") {
      if (!currentInteractionId) {
        return {
          ...localResult,
          reply: "I updated the form draft. Create or read an interaction first, then I can update the database record too.",
          tool_actions: [{ ...action, status: "needs_clarification" }],
        };
      }

      const interaction = await api.updateInteraction(currentInteractionId, {
        ...draftToInteractionPatch(patch),
        changed_by: repId,
      });
      return {
        ...localResult,
        reply: "Updated the saved interaction and kept the rest of the form intact.",
        tool_actions: [
          {
            ...action,
            status: "ok",
            data: { ...action.data, interaction, current_interaction_id: interaction.id },
          },
        ],
      };
    }

    if (action.tool === "lookup_hcp") {
      const name = action.data?.hcp_name || nextDraft.hcp_name;
      const hcp = await ensureHcp(name);
      const interactions = hcp ? await api.listInteractions(hcp.id).catch(() => []) : [];
      const latest = interactions[0];
      return {
        ...localResult,
        reply: latest
          ? `Read latest interaction for ${hcp.name}: ${latest.summary || latest.discussion_notes || "No notes"}.`
          : `${hcp?.name || name} exists, but there are no saved interactions yet.`,
        tool_actions: [
          {
            ...action,
            status: latest ? "ok" : "no_history",
            data: { ...action.data, hcp, interaction: latest, current_interaction_id: latest?.id },
          },
        ],
      };
    }

  } catch (error) {
    return {
      ...localResult,
      reply: `${localResult.reply} Database sync failed: ${error.message}`,
      tool_actions: [{ ...action, status: "error", data: { ...action.data, error: error.message } }],
    };
  }

  return localResult;
}

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async ({ sessionId, repId, text }, { getState }) => {
    const state = getState();
    const { interactionDraft } = state.interactions;
    const localResult = runLocalAgent(text, interactionDraft);
    const primaryTool = findPrimaryTool(localResult);

    if (
      ["log_interaction", "edit_interaction", "lookup_hcp"].includes(primaryTool?.tool)
    ) {
      const persisted = await persistToolAction(localResult, state, repId);
      return {
        session_id: sessionId || "prompt-crud-session",
        ...persisted,
        local: true,
      };
    }

    try {
      const serverResult = await api.sendChatMessage({ session_id: sessionId, rep_id: repId, text });
      const toolActions = serverResult.tool_actions?.length
        ? serverResult.tool_actions.map((action) => {
            const localAction = localResult.tool_actions.find((a) => a.tool === action.tool);
            if (!localAction?.data?.form_patch) return action;

            return {
              ...action,
              status: action.tool === "log_interaction" ? localAction.status : action.status,
              data: { ...(action.data || {}), form_patch: localAction.data.form_patch },
            };
          })
        : localResult.tool_actions;
      const shouldUsePromptDrivenReply = toolActions.some(
        (action) => action.tool === "log_interaction" && action.data?.form_patch
      );

      return {
        ...serverResult,
        tool_actions: toolActions,
        reply: shouldUsePromptDrivenReply ? localResult.reply : serverResult.reply || localResult.reply,
      };
    } catch {
      return {
        session_id: sessionId || "local-demo-session",
        reply: localResult.reply,
        tool_actions: localResult.tool_actions,
        local: true,
      };
    }
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState: {
    sessionId: null,
    messages: [], // {role: 'user'|'agent', content, toolActions?}
    status: "idle",
  },
  reducers: {
    resetSession(state) {
      state.sessionId = null;
      state.messages = [];
      state.status = "idle";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = "loading";
        state.messages.push({ role: "user", content: action.meta.arg.text });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "idle";
        state.sessionId = action.payload.session_id;
        state.messages.push({
          role: "agent",
          content: action.payload.reply,
          toolActions: action.payload.tool_actions || [],
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "error";
        state.messages.push({
          role: "agent",
          content: `Something went wrong: ${action.error.message}`,
          toolActions: [],
        });
      });
  },
});

export const { resetSession } = chatSlice.actions;
export default chatSlice.reducer;
