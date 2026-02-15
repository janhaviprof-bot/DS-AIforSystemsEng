# EV Charging Slots — UI Redesign (Premium Dashboard)

Design system and implementation guide for a modern, Tesla/Apple-style energy dashboard.

---

## 1. Improved UI Layout Structure

```
+------------------------------------------------------------------+
|  HEADER: App name + EV/charging icon + short tagline             |
+------------------------------------------------------------------+
|  MAIN: Two-column (responsive: stack on mobile)                  |
|  +------------------------------+  +-----------------------------+|
|  | LEFT (2/3)                   |  | RIGHT (1/3)                 ||
|  | • Charging duration          |  | • Vehicle lookup            ||
|  | • Toggle: Greenest vs Cheapest|  | • Confirm vehicle           ||
|  | • [Get recommendations] CTA |  | • EV specs + charging time  ||
|  | • Carbon intensity timeline  |  |                             ||
|  |   (24–48h bar/line chart)    |  |                             ||
|  | • Best Time to Charge card   |  |                             ||
|  |   – Slot cards (scroll)      |  |                             ||
|  |   – [Schedule] [Export]      |  |                             ||
|  +------------------------------+  +-----------------------------+|
+------------------------------------------------------------------+
```

- **Above the fold:** Header + primary CTA (duration + “Get recommendations”) + first slot card or placeholder.
- **Progressive disclosure:** Vehicle panel on right; slots and intensity chart appear after recommendations load.
- **Clear hierarchy:** One primary action per section; secondary actions (Schedule, Export) on the slot card.

---

## 2. Component Breakdown

| Component | Purpose | Key elements |
|-----------|---------|--------------|
| **App header** | Brand + context | Logo/icon, title “Smart Charge” or “EV Charge Optimizer”, one-line tagline |
| **Duration selector** | Input | Numeric stepper or slider (0.5–24 h), label “Charging duration” |
| **Greenest vs Cheapest toggle** | Mode switch | Segmented control or toggle; “Greenest” (default) / “Cheapest” |
| **Primary CTA** | Trigger prediction | “Get recommendations” or “Find best slots”; prominent, rounded |
| **Carbon intensity timeline** | Context | 24–48h bar or area chart; low=green, mid=yellow, high=red; tooltips on hover |
| **Best Time to Charge card** | Main result | Title, short intro, horizontal scroll of slot cards, optional [Schedule] [Export] |
| **Slot card** | One recommendation | Time range, duration, “Low/Medium/High” badge, reason, [Charge now] or [Select] |
| **Vehicle lookup** | Optional input | Text input + “Look up”; confirm step with make/model edit |
| **EV specs card** | Result | Make, model, battery, charge power, charging time (0–100%) |
| **Loading state** | Feedback | Skeleton or spinner on slots area; “Finding best times…” |
| **Empty / error state** | Fallback | Friendly message + retry CTA |

---

## 3. Color Palette (Sustainable + Energy)

### Light mode

| Role | Hex | Usage |
|------|-----|--------|
| **Primary (green/teal)** | `#0d9488` | Main CTAs, links, “greenest” emphasis |
| **Primary hover** | `#0f766e` | Button hover |
| **Secondary (charcoal)** | `#1e293b` | Headings, primary text |
| **Accent (electric)** | `#06b6d4` | Highlights, badges, optional “cheapest” |
| **Background** | `#f8fafc` | Page background |
| **Surface / cards** | `#ffffff` | Card background |
| **Border** | `#e2e8f0` | Dividers, card borders |
| **Muted text** | `#64748b` | Secondary text, captions |

### Slot intensity (WCAG-friendly)

| Level | Background | Text | Use |
|-------|------------|------|-----|
| **Low** | `#22c55e` | `#ffffff` | Best slots |
| **Medium** | `#eab308` | `#1e293b` | OK slots |
| **High** | `#ef4444` | `#ffffff` | Avoid |

### Dark mode

| Role | Hex |
|------|-----|
| Background | `#0f172a` |
| Surface | `#1e293b` |
| Border | `#334155` |
| Text | `#f1f5f9` |
| Muted | `#94a3b8` |
| Primary | `#2dd4bf` |
| Accent | `#22d3ee` |

Use CSS variables and `prefers-color-scheme: dark` (or a toggle) to switch.

---

## 4. Example React + Tailwind Code

### Palette (Tailwind config)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        ev: {
          primary: "#0d9488",
          "primary-hover": "#0f766e",
          secondary: "#1e293b",
          accent: "#06b6d4",
          surface: "#ffffff",
          low: "#22c55e",
          medium: "#eab308",
          high: "#ef4444",
        },
      },
      borderRadius: { "ev": "12px", "ev-lg": "16px" },
      boxShadow: {
        "ev": "0 2px 8px rgba(0,0,0,0.06)",
        "ev-hover": "0 8px 24px rgba(0,0,0,0.1)",
      },
    },
  },
};
```

### Header component

```tsx
export function AppHeader() {
  return (
    <header className="rounded-2xl bg-white dark:bg-slate-800 shadow-ev p-6 mb-6 border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-ev-primary/10 flex items-center justify-center">
          <ChargingIcon className="w-6 h-6 text-ev-primary" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-ev-secondary dark:text-slate-100">
            Smart Charge
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Best EV charging times from carbon intensity
          </p>
        </div>
      </div>
    </header>
  );
}
```

### Slot card component

```tsx
type Intensity = "low" | "medium" | "high";

const intensityStyles: Record<Intensity, string> = {
  low: "bg-ev-low text-white",
  medium: "bg-ev-medium text-ev-secondary",
  high: "bg-ev-high text-white",
};

export function SlotCard({
  slotNumber,
  start,
  end,
  reason,
  intensity,
}: {
  slotNumber: number;
  start: string;
  end: string;
  reason: string;
  intensity: Intensity;
}) {
  return (
    <div
      className={`
        rounded-ev-lg p-4 min-w-[200px] flex-shrink-0
        transition-all duration-200 hover:scale-[1.02] hover:shadow-ev-hover
        ${intensityStyles[intensity]}
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold">Slot {slotNumber}</span>
        <span className="text-xs uppercase tracking-wide opacity-90">
          {intensity}
        </span>
      </div>
      <p className="text-sm font-medium">{start} – {end}</p>
      <p className="text-sm opacity-90 mt-1">{reason}</p>
      <button className="mt-3 w-full py-2 rounded-lg bg-white/20 hover:bg-white/30 text-sm font-medium transition-colors">
        Charge in this window
      </button>
    </div>
  );
}
```

### Best Time to Charge section

```tsx
export function BestTimeCard({ slots, loading }: { slots: Slot[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="rounded-ev-lg bg-white dark:bg-slate-800 shadow-ev p-6 animate-pulse">
        <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-4" />
        <div className="flex gap-3 overflow-x-auto pb-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 min-w-[200px] bg-slate-100 dark:bg-slate-700 rounded-ev" />
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-ev-lg bg-white dark:bg-slate-800 shadow-ev p-6 border border-slate-200 dark:border-slate-700">
      <h2 className="text-lg font-semibold text-ev-secondary dark:text-slate-100 mb-1">
        Best time to charge
      </h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Recommended windows based on UK carbon intensity
      </p>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        {slots.map((slot, i) => (
          <SlotCard key={i} slotNumber={i + 1} {...slot} />
        ))}
      </div>
      <div className="flex gap-2 mt-4">
        <button className="px-4 py-2 rounded-lg bg-ev-primary text-white hover:bg-ev-primary-hover transition-colors">
          Schedule charging
        </button>
        <button className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 text-ev-secondary dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
          Export
        </button>
      </div>
    </div>
  );
}
```

### Carbon intensity bar (conceptual)

```tsx
export function IntensityBar({ data }: { data: { time: string; index: string; forecast: number }[] }) {
  return (
    <div className="rounded-ev bg-white dark:bg-slate-800 shadow-ev p-4 mb-4">
      <h3 className="text-sm font-medium text-ev-secondary dark:text-slate-300 mb-3">
        Carbon intensity (next 48h)
      </h3>
      <div className="flex gap-0.5 h-8 items-end">
        {data.slice(0, 96).map((d, i) => (
          <div
            key={i}
            title={`${d.time}: ${d.index} (${d.forecast} gCO2/kWh)`}
            className={`
              flex-1 min-w-[2px] rounded-t transition-all hover:opacity-80
              ${d.index === "low" ? "bg-ev-low" : d.index === "moderate" ? "bg-ev-medium" : "bg-ev-high"}
            `}
            style={{ height: `${Math.min(100, (d.forecast / 400) * 100)}%` }}
          />
        ))}
      </div>
    </div>
  );
}
```

---

## 5. Suggestions for Premium, Interactive Feel

- **Motion:** Use `transition` and light `hover:scale` or `hover:-translate-y-0.5` on cards and buttons; keep duration 150–250 ms.
- **Loading:** Always show a skeleton or spinner when fetching slots; avoid blank content.
- **Tooltips:** Add `title` or a tooltip component on intensity bars and slot cards (time, gCO2/kWh, reason).
- **CTAs:** One primary button per section (“Get recommendations”, “Charge in this window”); secondary actions (Schedule, Export) as outline buttons.
- **Spacing:** Use consistent padding (e.g. 1rem / 1.5rem) and gap between cards; avoid dense layouts.
- **Accessibility:** Keep contrast ratios for low/medium/high slots; ensure focus states on buttons and interactive cards.
- **Responsive:** Stack columns on small screens; keep slot cards horizontally scrollable; ensure touch-friendly tap targets (min 44px).
- **Dark mode:** Support via `prefers-color-scheme` and CSS variables so a future toggle can switch themes without duplicating styles.
