type Props = {
  title: string;
  phase: string;
  description: string;
};

export function PagePlaceholder({ title, phase, description }: Props) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-medium uppercase tracking-wider text-signal-600 mb-2">
        {phase}
      </p>
      <h1 className="font-display text-2xl text-ink-900 mb-3">{title}</h1>
      <p className="text-ink-500 leading-relaxed">{description}</p>
    </div>
  );
}
