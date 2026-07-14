import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../api/client";
import { runLocalAgent } from "../utils/localAgent";

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async ({ sessionId, repId, text }, { getState }) => {
    const { interactionDraft } = getState().interactions;
    const localResult = runLocalAgent(text, interactionDraft);

    try {
      const serverResult = await api.sendChatMessage({ session_id: sessionId, rep_id: repId, text });
      const toolActions = serverResult.tool_actions?.length
        ? serverResult.tool_actions.map((action) => {
            const localAction = localResult.tool_actions.find((a) => a.tool === action.tool);
            return localAction?.data?.form_patch
              ? { ...action, data: { ...(action.data || {}), form_patch: localAction.data.form_patch } }
              : action;
          })
        : localResult.tool_actions;

      return {
        ...serverResult,
        tool_actions: toolActions,
        reply: serverResult.reply || localResult.reply,
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
