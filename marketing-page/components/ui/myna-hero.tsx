"use client";

import * as React from "react";
import { ArrowRight } from "lucide-react";
import CombinedFeaturedSection from "@/components/ui/combined-featured-section";
import { motion, useAnimation, useInView } from "framer-motion";
import { Button } from "@/components/ui/button";
import VideoPlayer from "@/components/ui/video-player";
import { PricingSection } from "@/components/blocks/pricing-section";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Footerdemo } from "./footer-section";
import { HowItWorksSection } from "@/components/ui/how-it-works";
export function MynaHero() {
  const controls = useAnimation();
  const ref = React.useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.1 });

  React.useEffect(() => {
    if (isInView) {
      controls.start("visible");
    }
  }, [controls, isInView]);

  const titleWords = [
    "Turn",
    "CSVs",
    "into",
    "cinematic",
    "data",
    "animations",
    "—",
    "instantly",
  ];
  const TIERS = [
    {
      id: "free",
      name: "Free",
      price: {
        monthly: 0,
        yearly: 0,
      },
      description: "Try data animation with core templates",
      features: [
        "3 preview renders / day",
        "720p with watermark",
        "CSV up to 5 MB",
        "Core templates",
        "No API access",
      ],
      cta: "Try free",
    },
    {
      id: "pro",
      name: "Pro",
      price: {
        monthly: 29,
        yearly: 24,
      },
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
      price: {
        monthly: 99,
        yearly: 79,
      },
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
      price: {
        monthly: "Custom",
        yearly: "Custom",
      },
      description: "Scale & compliance",
      features: [
        "Unlimited seats",
        "Custom SLAs & support",
        "Managed/on‑prem workers",
        "Security & compliance",
        "Volume pricing",
      ],
      cta: "Contact sales",
      highlighted: true,
    },
  ];
  const faqItems = [
    {
      id: "item-1",
      question: "What data formats do you support?",
      answer:
        "CSV (long-form or wide-form) and Danim X/Y/R files (auto unified).",
    },
    {
      id: "item-2",
      question: "Do I get the Manim code?",
      answer:
        "Yes. Every render includes downloadable Manim CE source used to generate the video.",
    },
    {
      id: "item-3",
      question: "How fast are renders?",
      answer:
        "Preview seconds, final depends on length and complexity. Most <60s videos finish in under a minute.",
    },
    {
      id: "item-4",
      question: "Will my data fall back to LLM generation silently?",
      answer:
        "No. We validate template inputs and emit clear errors; LLM fallback only runs when explicitly triggered.",
    },
    {
      id: "item-5",
      question: "Is there a watermark?",
      answer:
        "Only on Free plan previews. Paid plans render no watermark videos.",
    },
    {
      id: "item-6",
      question: "How is usage measured?",
      answer:
        "By render minutes (preview + final). Unused minutes do not roll over.",
    },
    {
      id: "item-7",
      question: "Can I self-host rendering?",
      answer: "Enterprise tier supports managed or on‑prem render workers.",
    },
  ];
  const PAYMENT_FREQUENCIES = ["monthly", "yearly"];
  return (
    <div className="container mx-auto px-4 min-h-screen bg-background">
      <main>
        <section className="container py-24">
          <div className="flex flex-col items-center text-center">
            <motion.h1
              initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative font-mono text-4xl font-bold sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl mx-auto leading-tight"
            >
              {titleWords.map((text, index) => (
                <motion.span
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    delay: index * 0.15,
                    duration: 0.6,
                  }}
                  className="inline-block mx-2 md:mx-4"
                >
                  {text}
                </motion.span>
              ))}
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2, duration: 0.6 }}
              className="mx-auto mt-2 max-w-2xl text-xl text-foreground font-mono"
            >
              Upload a dataset or hit the API to render studio-quality Manim
              videos. Deterministic templates. Fast previews. Clear pricing.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 2.4,
                duration: 0.6,
                type: "spring",
                stiffness: 100,
                damping: 10,
              }}
              className="mx-auto mt-5 max-w-2xl "
            >
              <Button
                size="lg"
                className="cursor-pointer rounded-none  bg-[#FF6B2C] hover:bg-[#FF6B2C]/90 font-mono"
              >
                Try the demo <ArrowRight className="ml-1 w-4 h-4" />
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 2.4,
                duration: 0.6,
                type: "spring",
                stiffness: 100,
                damping: 10,
              }}
              className="mt-12"
            >
              <VideoPlayer src="https://videos.pexels.com/video-files/30333849/13003128_2560_1440_25fps.mp4" />
            </motion.div>
          </div>
        </section>
        <section className="container py-24" ref={ref}>
          <div className="flex flex-col items-center">
            <motion.h1
              initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative font-mono text-4xl font-bold sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl text-left"
            >
              <motion.span
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.15,
                  duration: 0.6,
                }}
                className="inline-block mx-2 md:mx-4"
              >
                HOW IT WORKS
              </motion.span>
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 3.2, duration: 0.6 }}
            >
              <HowItWorksSection />
            </motion.div>
          </div>
        </section>
        <section className="container py-24" ref={ref}>
          <div className="flex flex-col items-center">
            <motion.h1
              initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative font-mono text-4xl font-bold sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl text-left"
            >
              <motion.span
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.15,
                  duration: 0.6,
                }}
                className="inline-block mx-2 md:mx-4"
              >
                WHAT YOU GET
              </motion.span>
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 3.2, duration: 0.6 }}
            >
              <CombinedFeaturedSection />
            </motion.div>
          </div>
        </section>
        <section className="container py-24" ref={ref}>
          <div className="flex flex-col items-center ">
            <motion.h1
              initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative font-mono text-4xl font-bold sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl text-left"
            >
              <motion.span
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.15,
                  duration: 0.6,
                }}
                className="inline-block mx-2 md:mx-4"
              >
                PRICING
              </motion.span>
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 3.2, duration: 0.6 }}
            >
              <PricingSection frequencies={PAYMENT_FREQUENCIES} tiers={TIERS} />
            </motion.div>
          </div>
        </section>
        <section className="container py-24" ref={ref}>
          <div className="flex flex-col items-center mx-auto max-w-2xl px-6 space-y-12">
            <motion.h1
              initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
              animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative font-mono text-4xl font-bold sm:text-5xl md:text-6xl lg:text-7xl max-w-4xl text-left"
            >
              <motion.span
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.15,
                  duration: 0.6,
                }}
                className="inline-block mx-2 md:mx-4"
              >
                QUESTION
              </motion.span>
            </motion.h1>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 3.2, duration: 0.6 }}
            >
              <Accordion type="single" collapsible className="-mx-2 sm:mx-0">
                {faqItems.map((item) => (
                  <div className="group" key={item.id}>
                    <AccordionItem
                      value={item.id}
                      className="data-[state=open]:bg-muted peer rounded-xl border-none px-5 py-1 data-[state=open]:border-none md:px-7"
                    >
                      <AccordionTrigger className="cursor-pointer text-base hover:no-underline">
                        {item.question}
                      </AccordionTrigger>
                      <AccordionContent>
                        <p className="text-base">{item.answer}</p>
                      </AccordionContent>
                    </AccordionItem>
                    <hr className="mx-5 -mb-px group-last:hidden peer-data-[state=open]:opacity-0 md:mx-7" />
                  </div>
                ))}
              </Accordion>
            </motion.div>
          </div>
        </section>
        <section className="container py-24 block" ref={ref}>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 3.2, duration: 0.6 }}
          >
            <Footerdemo />
          </motion.div>
        </section>
      </main>
    </div>
  );
}
