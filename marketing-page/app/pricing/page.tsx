import { PricingSection } from "@/components/blocks/pricing-section";
import { Badge } from "@/components/ui/badge";

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: { monthly: 0, yearly: 0 },
    description: "Try data animation with core templates",
    features: [
      "3 preview renders / day",
      "720p (watermark)",
      "CSV up to 5 MB",
      "Core templates",
      "No API access",
    ],
    cta: "Try free",
  },
  {
    id: "pro",
    name: "Pro",
    price: { monthly: 29, yearly: 24 },
    description: "For creators & analysts",
    features: [
      "200 render minutes / month",
      "1080p no watermark",
      "All templates",
      "API + SSE progress",
      "Email support",
    ],
    cta: "Get Pro",
    popular: true,
  },
  {
    id: "team",
    name: "Team",
    price: { monthly: 99, yearly: 79 },
    description: "For teams shipping content",
    features: [
      "1,000 render minutes / month",
      "Up to 5 seats",
      "Shared brand presets",
      "Priority queue",
      "SSO (Google)",
    ],
    cta: "Start Team",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: { monthly: "Custom", yearly: "Custom" },
    description: "Scale & compliance",
    features: [
      "Unlimited seats",
      "Custom SLAs & support",
      "Managed / on‑prem workers",
      "Security & compliance",
      "Volume pricing",
    ],
    cta: "Contact sales",
    highlighted: true,
  },
];

const PAYMENT_FREQUENCIES = ["monthly", "yearly"];

export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-24">
      {/* Hero */}
      <section className="max-w-3xl mx-auto text-center space-y-6">
        <h1 className="font-mono text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight">
          Simple, transparent pricing
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          Pay for render time, not guesswork. Deterministic templates, fast
          previews, and Manim code export included across paid plans.
        </p>
        <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" className="font-mono">
            No hidden usage multipliers
          </Badge>
          <Badge variant="outline" className="font-mono">
            Cancel anytime
          </Badge>
          <Badge variant="outline" className="font-mono">
            Usage pooled across preview & final
          </Badge>
        </div>
      </section>

      {/* Pricing tiers */}
      <section className="mt-16">
        <PricingSection tiers={TIERS} frequencies={PAYMENT_FREQUENCIES} />
      </section>

      {/* Render minutes explainer */}
      <section className="mt-20 max-w-4xl mx-auto grid gap-10 md:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">
            What are render minutes?
          </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Render minutes measure the total time spent producing your
              animations (preview + final). A 30‑second preview that takes 10
              seconds to compute consumes 10 minutes? No—only actual compute
              duration counts (10 seconds = 0.17 minutes). We aggregate those
              durations across your account.
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex gap-2">
                <span className="text-primary">•</span> Preview and final both
                draw from the same pool.
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span> Unused minutes do not
                roll over.
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span> Overages: soft cap; we
                notify before throttling.
              </li>
            </ul>
        </div>
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">
            Why template‑first pricing?
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Deterministic templates let us give you predictable performance and
            cost. Instead of billing per token or vague “AI operations,” we
            measure actual render compute. If a dataset doesn’t fit a template,
            you can opt into a fallback path explicitly—never silently.
          </p>
          <ul className="space-y-2 text-sm">
            <li className="flex gap-2">
              <span className="text-primary">•</span> Clear guardrails avoid
              runaway generation.
            </li>
            <li className="flex gap-2">
              <span className="text-primary">•</span> Manim code export lets you
              refine offline.
            </li>
            <li className="flex gap-2">
              <span className="text-primary">•</span> Predictable throughput for
              teams and batch jobs.
            </li>
          </ul>
        </div>
      </section>

      {/* Comparison / notes */}
      <section className="mt-24 max-w-5xl mx-auto space-y-8">
        <h2 className="text-2xl font-semibold tracking-tight">
          Choosing a plan
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-none border p-6 space-y-3">
            <h3 className="text-lg font-medium">Free</h3>
            <p className="text-sm text-muted-foreground">
              Quick test runs; explore templates; evaluate quality.
            </p>
          </div>
          <div className="rounded-none border p-6 space-y-3">
            <h3 className="text-lg font-medium">Pro</h3>
            <p className="text-sm text-muted-foreground">
              Regular content creation, dashboards, weekly KPI videos.
            </p>
          </div>
          <div className="rounded-none border p-6 space-y-3">
            <h3 className="text-lg font-medium">Team / Enterprise</h3>
            <p className="text-sm text-muted-foreground">
              Shared brand presets, higher throughput, compliance, scale.
            </p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Need more than 10,000 render minutes / month or custom compliance?
          Reach out for volume pricing and managed infrastructure.
        </p>
      </section>

      {/* Inline FAQ subset (link to full FAQ if needed) */}
      <section className="mt-24 max-w-3xl mx-auto space-y-6">
        <h2 className="text-2xl font-semibold tracking-tight">Pricing FAQ</h2>
        <div className="space-y-4 text-sm">
          <div>
            <p className="font-medium">Do previews count against minutes?</p>
            <p className="text-muted-foreground">
              Yes, but they are usually lightweight. Optimize with shorter
              preview durations before final render.
            </p>
          </div>
          <div>
            <p className="font-medium">What happens if I hit my limit?</p>
            <p className="text-muted-foreground">
              We notify you at 80% and 95%. At 100% we slow queue priority
              (except Enterprise) until you upgrade or the cycle resets.
            </p>
          </div>
          <div>
            <p className="font-medium">Is my data stored?</p>
            <p className="text-muted-foreground">
              Source files and intermediate artifacts are deleted after a short
              retention window unless you pin them (Team+).
            </p>
          </div>
          <div>
            <p className="font-medium">Can I self‑host rendering?</p>
            <p className="text-muted-foreground">
              Enterprise supports managed or on‑prem worker pools for isolation
              and performance.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
