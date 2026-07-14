import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../api/client";
import { sendMessage } from "./chatSlice";
import { DEFAULT_MATERIALS, normalizeToolPatch } from "../utils/localAgent";

export const submitInteraction = createAsyncThunk(
  "interactions/submit",
  async ({ repId, data }) => {
    return api.createInteraction(repId, data);
  }
);

export const fetchHistory = createAsyncThunk("interactions/fetchHistory", async (hcpId) => {
  return api.listInteractions(hcpId);
});

const interactionsSlice = createSlice({
  name: "interactions",
  initialState: {
    history: [],
    interactionDraft: {
      hcp_name: "",
      interaction_date: "",
      type: "",
      discussion_product: "",
      sentiment: "",
      materials_shared: DEFAULT_MATERIALS,
      discussion_notes: "",
      next_steps: "",
    },
    lastToolName: null,
    currentHcpId: null,
    currentInteractionId: null,
    submitStatus: "idle", // idle | loading | succeeded | failed
    submitError: null,
    lastCreated: null,
  },
  reducers: {
    applyInteractionPatch(state, action) {
      const patch = action.payload || {};
      state.interactionDraft = {
        ...state.interactionDraft,
        ...patch,
        materials_shared: {
          ...state.interactionDraft.materials_shared,
          ...(patch.materials_shared || {}),
        },
      };
    },
    resetInteractionDraft(state) {
      state.interactionDraft = {
        hcp_name: "",
        interaction_date: "",
        type: "",
        discussion_product: "",
        sentiment: "",
        materials_shared: DEFAULT_MATERIALS,
        discussion_notes: "",
        next_steps: "",
      };
      state.lastToolName = null;
      state.currentHcpId = null;
      state.currentInteractionId = null;
    },
    resetSubmitStatus(state) {
      state.submitStatus = "idle";
      state.submitError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.submitStatus = "loading";
        state.submitError = null;
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.submitStatus = "succeeded";
        state.lastCreated = action.payload;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.submitStatus = "failed";
        state.submitError = action.error.message;
      })
      .addCase(fetchHistory.fulfilled, (state, action) => {
        state.history = action.payload;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        const formTools = (action.payload.tool_actions || []).filter((toolAction) =>
          ["log_interaction", "edit_interaction", "lookup_hcp"].includes(toolAction.tool)
        );
        formTools.forEach((toolAction) => {
          const patch = normalizeToolPatch(toolAction);
          state.interactionDraft = {
            ...state.interactionDraft,
            ...patch,
            materials_shared: {
              ...state.interactionDraft.materials_shared,
              ...(patch.materials_shared || {}),
            },
          };
          state.lastToolName = toolAction.tool;
          state.currentHcpId = toolAction.data?.hcp?.id || state.currentHcpId;
          state.currentInteractionId =
            toolAction.data?.current_interaction_id || toolAction.data?.interaction?.id || state.currentInteractionId;
        });
      });
  },
});

export const { applyInteractionPatch, resetInteractionDraft, resetSubmitStatus } = interactionsSlice.actions;
export default interactionsSlice.reducer;
