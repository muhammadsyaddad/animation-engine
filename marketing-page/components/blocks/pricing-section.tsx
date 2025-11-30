"use client";

import * as React from "react";
import { PricingCard, type PricingTier } from "@/components/ui/pricing-card";
import { Tab } from "@/components/ui/pricing-tab";

interface PricingSectionProps {
  tiers: PricingTier[];
  frequencies: string[];
}

export function PricingSection({ tiers, frequencies }: PricingSectionProps) {
  const [selectedFrequency, setSelectedFrequency] = React.useState(
    frequencies[0],
  );

  return (
    <section className="flex flex-col items-center gap-10 py-2">
      <div className="space-y-7 text-center">
        <div className="space-y-4"></div>
        <div className="mx-auto flex w-fit rounded-full bg-muted p-1">
          {frequencies.map((freq) => (
            <Tab
              key={freq}
              text={freq}
              selected={selectedFrequency === freq}
              setSelected={setSelectedFrequency}
              discount={freq === "yearly"}
            />
          ))}
        </div>
      </div>

      <div className="grid w-full max-w-6xl gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {tiers.map((tier) => (
          <PricingCard
            key={tier.name}
            tier={tier}
            paymentFrequency={selectedFrequency}
          />
        ))}
      </div>
    </section>
  );
}
