import { useState, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { searchHcps, selectHcp, clearResults } from "../store/hcpsSlice";
import "./HcpSearchInput.css";

export default function HcpSearchInput({ onSelect }) {
  const dispatch = useDispatch();
  const { results, selectedHcp } = useSelector((s) => s.hcps);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query || (selectedHcp && selectedHcp.name === query)) {
      dispatch(clearResults());
      return;
    }
    debounceRef.current = setTimeout(() => {
      dispatch(searchHcps(query));
      setOpen(true);
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [query, dispatch, selectedHcp]);

  const handlePick = (hcp) => {
    dispatch(selectHcp(hcp));
    setQuery(hcp.name);
    setOpen(false);
    onSelect?.(hcp);
  };

  return (
    <div className="hcp-search">
      <label className="field-label" htmlFor="hcp-search-input">
        HCP
      </label>
      <input
        id="hcp-search-input"
        className="field-input"
        placeholder="Search by name…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        autoComplete="off"
      />
      {open && results.length > 0 && (
        <ul className="hcp-search__results" role="listbox">
          {results.map((hcp) => (
            <li key={hcp.id} role="option">
              <button type="button" className="hcp-search__option" onClick={() => handlePick(hcp)}>
                <span className="hcp-search__name">{hcp.name}</span>
                <span className="hcp-search__meta">
                  {hcp.specialty || "—"} · {hcp.interaction_count} logged
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
