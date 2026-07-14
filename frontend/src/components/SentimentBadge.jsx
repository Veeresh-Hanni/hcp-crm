const STYLES = {
  positive: { bg: "var(--status-positive-tint)", fg: "var(--status-positive)" },
  neutral: { bg: "var(--status-neutral-tint)", fg: "var(--status-neutral)" },
  negative: { bg: "var(--status-negative-tint)", fg: "var(--status-negative)" },
};

export default function SentimentBadge({ sentiment }) {
  if (!sentiment) return null;
  const style = STYLES[sentiment] || STYLES.neutral;
  return (
    <span
      style={{
        background: style.bg,
        color: style.fg,
        fontFamily: "var(--font-mono)",
        fontSize: "11.5px",
        fontWeight: 500,
        padding: "2px 7px",
        borderRadius: "999px",
        textTransform: "uppercase",
        letterSpacing: "0.03em",
      }}
    >
      {sentiment}
    </span>
  );
}
