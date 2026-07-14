import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../api/client";

export const searchHcps = createAsyncThunk("hcps/search", async (query) => {
  return api.searchHcps(query);
});

export const createHcp = createAsyncThunk("hcps/create", async (data) => {
  return api.createHcp(data);
});

const hcpsSlice = createSlice({
  name: "hcps",
  initialState: {
    results: [],
    status: "idle",
    selectedHcp: null,
  },
  reducers: {
    selectHcp(state, action) {
      state.selectedHcp = action.payload;
    },
    clearResults(state) {
      state.results = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(searchHcps.pending, (state) => {
        state.status = "loading";
      })
      .addCase(searchHcps.fulfilled, (state, action) => {
        state.status = "idle";
        state.results = action.payload;
      })
      .addCase(searchHcps.rejected, (state) => {
        state.status = "error";
      });
  },
});

export const { selectHcp, clearResults } = hcpsSlice.actions;
export default hcpsSlice.reducer;
