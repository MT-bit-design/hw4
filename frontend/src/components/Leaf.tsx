import type { CSSProperties, ReactNode } from "react";

/** A simple fall leaf (inline SVG, no image request). Decorative: hidden from screen readers. */
export function Leaf({
  color = "var(--orange)",
  size = 18,
  className = "",
  style,
}: {
  color?: string;
  size?: number;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      className={`leaf ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      style={style}
    >
      <path
        d="M12 1.5C6.6 5.6 4 10.2 5 14.7c.8 3.5 3.6 5.7 7 6.3 3.4-.6 6.2-2.8 7-6.3 1-4.5-1.6-9.1-7-13.2z"
        fill={color}
      />
      <path
        d="M12 4.5V23M12 10l-3.2-2.6M12 10l3.2-2.6M12 14.5l-4-3M12 14.5l4-3M12 18.5l-3-2.2M12 18.5l3-2.2"
        stroke="rgba(255,255,255,0.55)"
        strokeWidth="0.9"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/** A thin rule with a small leaf in the middle, used between sections. */
export function LeafDivider({ color = "var(--orange)" }: { color?: string }) {
  return (
    <div className="leaf-divider" role="presentation">
      <span />
      <Leaf color={color} size={16} />
      <span />
    </div>
  );
}

/** Empty / error state with a leaf, so "nothing here" still feels on-brand. */
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty-state">
      <Leaf color="var(--gold)" size={36} />
      <h2>{title}</h2>
      {children}
    </div>
  );
}

const DRIFT: { x: number; delay: number; dur: number; size: number; color: string }[] = [
  { x: 6, delay: 0, dur: 19, size: 22, color: "var(--orange)" },
  { x: 18, delay: 7, dur: 23, size: 16, color: "var(--gold)" },
  { x: 33, delay: 3, dur: 21, size: 20, color: "var(--red)" },
  { x: 52, delay: 11, dur: 25, size: 14, color: "var(--orange)" },
  { x: 68, delay: 5, dur: 20, size: 24, color: "var(--gold)" },
  { x: 81, delay: 14, dur: 24, size: 18, color: "var(--red)" },
  { x: 92, delay: 9, dur: 22, size: 15, color: "var(--orange)" },
];

/** Leaves drifting slowly down the Home hero. Pure CSS animation; hidden when reduced motion is on. */
export function DriftingLeaves() {
  return (
    <div className="drift" aria-hidden="true">
      {DRIFT.map((l, i) => (
        <span
          key={i}
          className="drift-leaf"
          style={
            {
              left: `${l.x}%`,
              animationDelay: `-${l.delay}s`,
              animationDuration: `${l.dur}s`,
            } as CSSProperties
          }
        >
          <Leaf color={l.color} size={l.size} />
        </span>
      ))}
    </div>
  );
}
