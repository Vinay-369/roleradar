type Props = {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  label?: string;
};

function colorFor(value: number): string {
  if (value >= 85) return "#0e7c66"; // signal-600
  if (value >= 70) return "#d68f1a"; // amber-500
  return "#b33a3a"; // alert-600
}

export function ScoreRing({ value, size = 72, strokeWidth = 6, label }: Props) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference;
  const color = colorFor(value);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e7ecee"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="rr-ring-progress"
            style={{ ["--rr-ring-circumference" as string]: circumference }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-display text-lg font-bold" style={{ color }}>{Math.round(value)}</span>
        </div>
      </div>
      {label && <p className="text-xs text-ink-500 mt-1.5 text-center">{label}</p>}
    </div>
  );
}
