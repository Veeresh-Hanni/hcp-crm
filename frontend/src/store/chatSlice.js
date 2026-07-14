import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../api/client";

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async ({ sessionId, repId, text }) => {
    return api.sendChatMessage({ session_id: sessionId, rep_id: repId, text });
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState: {
    sessionId: null,
    messages: [],
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
