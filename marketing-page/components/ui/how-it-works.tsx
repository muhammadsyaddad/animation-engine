"use client";

import * as React from "react";

import {
  ArrowRight,
  MousePointerClick,
  FileSpreadsheet,
  PlayCircle,
  Code2,
} from "lucide-react";

type Step = {
  id: number;
  title: string;
  description: string;
  Visual: React.FC;
};

const Step1Visual: React.FC = () => {
  return (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl border bg-muted/30">
      {/* Window chrome */}
      <div className="flex items-center gap-1 border-b bg-background/60 px-3 py-2">
        <div className="h-2 w-2 rounded-full bg-red-400" />
        <div className="h-2 w-2 rounded-full bg-yellow-400" />
        <div className="h-2 w-2 rounded-full bg-green-400" />
        <div className="ml-3 h-4 w-24 rounded bg-muted" />
      </div>

      {/* Content blocks */}
      <div className="relative h-full p-5">
        <div className="mb-3 h-4 w-48 rounded bg-muted" />
        <div className="mb-6 h-4 w-32 rounded bg-muted/80" />

        <div className="grid grid-cols-3 gap-3">
          <div className="h-24 rounded-lg border bg-background" />
          <div className="h-24 rounded-lg border bg-background" />
          <div className="h-24 rounded-lg border bg-background" />
        </div>

        {/* Upload CTA */}
        <div className="absolute bottom-5 left-5 flex items-center gap-2 rounded-full border bg-background/80 px-3 py-1.5 text-sm shadow-sm backdrop-blur">
          <FileSpreadsheet className="h-4 w-4" />
          <span>Upload CSV</span>
        </div>

        {/* Pointer */}
        <MousePointerClick className="absolute -bottom-1 right-6 h-8 w-8 rotate-12 opacity-70" />
      </div>
    </div>
  );
};

const Step2Visual: React.FC = () => {
  return (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl border bg-muted/30">
      {/* Window chrome */}
      <div className="flex items-center gap-1 border-b bg-background/60 px-3 py-2">
        <div className="h-2 w-2 rounded-full bg-red-400" />
        <div className="h-2 w-2 rounded-full bg-yellow-400" />
        <div className="h-2 w-2 rounded-full bg-green-400" />
        <div className="ml-3 h-4 w-28 rounded bg-muted" />
      </div>

      {/* Toolbar */}
      <div className="absolute left-1/2 top-1/2 z-10 w-[85%] -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-background/80 px-3 py-2 shadow backdrop-blur">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="h-6 w-20 rounded bg-muted" />
            <div className="h-6 w-24 rounded bg-muted" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-md border" />
            <div className="h-8 w-8 rounded-md border" />
            <div className="h-8 w-8 rounded-md border" />
          </div>
        </div>
      </div>

      {/* Template chips */}
      <div className="absolute bottom-5 left-1/2 z-10 -translate-x-1/2">
        <div className="flex items-center gap-2">
          <div className="rounded-full border bg-background/80 px-3 py-1 text-xs backdrop-blur">
            Bar Chart Race
          </div>
          <div className="rounded-full border bg-background/80 px-3 py-1 text-xs backdrop-blur">
            Bubble
          </div>
          <div className="rounded-full border bg-background/80 px-3 py-1 text-xs backdrop-blur">
            Distribution
          </div>
        </div>
      </div>

      {/* Background blocks */}
      <div className="absolute inset-0 p-5">
        <div className="mb-3 h-4 w-40 rounded bg-muted" />
        <div className="grid grid-cols-4 gap-3">
          <div className="h-28 rounded-lg border bg-background" />
          <div className="h-28 rounded-lg border bg-background" />
          <div className="h-28 rounded-lg border bg-background" />
          <div className="h-28 rounded-lg border bg-background" />
        </div>
      </div>
    </div>
  );
};

const Step3Visual: React.FC = () => {
  return (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl border bg-muted/30">
      {/* Document frame */}
      <div className="absolute left-1/2 top-1/2 h-[82%] w-[74%] -translate-x-1/2 -translate-y-1/2 rounded-2xl border bg-background p-4 shadow-sm">
        <div className="mb-3 h-4 w-48 rounded bg-muted" />
        <div className="mb-2 h-3 w-40 rounded bg-muted/80" />
        <div className="space-y-2">
          <div className="h-2.5 w-full rounded bg-muted" />
          <div className="h-2.5 w-11/12 rounded bg-muted" />
          <div className="h-2.5 w-10/12 rounded bg-muted" />
          <div className="h-2.5 w-9/12 rounded bg-muted" />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="h-20 rounded border bg-background" />
          <div className="h-20 rounded border bg-background" />
        </div>
      </div>

      {/* Actions */}
      <div className="absolute bottom-5 left-1/2 flex -translate-x-1/2 items-center gap-2">
        <div className="flex items-center gap-2 rounded-full border bg-background/80 px-3 py-1.5 text-sm shadow-sm backdrop-blur">
          <PlayCircle className="h-4 w-4" />
          <span>Render preview</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border bg-background/80 px-3 py-1.5 text-sm shadow-sm backdrop-blur">
          <Code2 className="h-4 w-4" />
          <span>Download code</span>
        </div>
      </div>
    </div>
  );
};

const steps: Step[] = [
  {
    id: 1,
    title: "Upload your data",
    description:
      "Drop in a CSV or send it via API. Long‑form and wide‑form supported. Danim X/Y/R files are unified automatically.",
    Visual: Step1Visual,
  },
  {
    id: 2,
    title: "Pick template or auto‑detect",
    description:
      "Choose a deterministic template or let us auto‑detect. We validate required columns with clear, actionable errors.",
    Visual: Step2Visual,
  },
  {
    id: 3,
    title: "Preview and render",
    description:
      "Get a fast preview, then export the final video. Stream progress over SSE and download the exact Manim CE code.",
    Visual: Step3Visual,
  },
];

function ConnectorArrow() {
  return (
    <div className="hidden items-center justify-center md:flex">
      <ArrowRight className="h-8 w-8 opacity-70" />
    </div>
  );
}

function StepBlock({ step }: { step: Step }) {
  const { id, title, description, Visual } = step;
  return (
    <div className="flex flex-col items-start">
      <Visual />
      <div className="mt-6">
        <div className="mb-1 text-sm text-muted-foreground">{id}</div>
        <h3 className="text-2xl font-semibold leading-tight">{title}</h3>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {description}
        </p>
      </div>
    </div>
  );
}

export function HowItWorksSection() {
  return (
    <section className="" id="how-it-works">
      {/* Horizontal 3-step composition with arrows */}
      <div className="mt-10 grid grid-cols-1 items-start gap-8 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <StepBlock step={steps[0]} />
        <ConnectorArrow />
        <StepBlock step={steps[1]} />
        <ConnectorArrow />
        <StepBlock step={steps[2]} />
      </div>

      {/* Stacked layout hint for small screens */}
      <div className="mt-4 text-center text-xs text-muted-foreground md:hidden">
        Steps connect left to right on larger screens.
      </div>
    </section>
  );
}

export default HowItWorksSection;
