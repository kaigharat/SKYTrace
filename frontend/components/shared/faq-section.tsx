"use client";

import * as React from "react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { Card } from "@/components/ui/card";

interface FAQItem {
  question: string;
  answer: string;
}

const FAQ_ITEMS: FAQItem[] = [
  {
    question: "What is SkyTrace?",
    answer:
      "SkyTrace is an AI-powered repository intelligence platform. It analyzes software repositories by combining source code AST syntax, dependency graphs, git commit history, and machine learning models to identify software defect risks and security vulnerabilities before code reaches production.",
  },
  {
    question: "Who can use SkyTrace?",
    answer:
      "SkyTrace is designed for Developers (to catch risky changes early), Code Reviewers (to assess PR impact), Students & Researchers (to study software analytics and graph neural representations), and Software Engineering Teams (to monitor overall repo health across sprints).",
  },
  {
    question: "What is the main input?",
    answer:
      "The primary input is a public GitHub repository URL (e.g. https://github.com/pallets/flask) or an owner/repo slug (e.g. pallets/flask). You can also analyze specific pull requests or code snippets.",
  },
  {
    question: "What does SkyTrace analyze?",
    answer:
      "SkyTrace analyzes source code AST structure, import and call dependency graphs, historical git churn and commit logs, static security rules (Semgrep integration), and ML feature representations derived from code complexity and past bug fixes.",
  },
  {
    question: "What are the outputs?",
    answer:
      "You receive an overall Repository Health Score (0-100), Component Defect Risk Classifications (LOW / MEDIUM / HIGH / CRITICAL), Security Risk Findings with evidence, Regression Area Blast Radius, Interactive Dependency Graphs, and AI Pull Request Impact Reviews.",
  },
  {
    question: "Does a risk score guarantee that a bug exists?",
    answer:
      "No. Risk scores represent statistical ML defect probabilities and vulnerability likelihood based on complexity, historical bug frequency, and coupling. High-risk components are prime candidates for refactoring, code review, and automated unit testing.",
  },
  {
    question: "Can I analyze another GitHub repository?",
    answer:
      "Yes! Simply click 'Analyze a Repository' or visit the Onboarding page, enter any public GitHub repository URL or owner/repo slug, and SkyTrace will ingest and analyze the repository in real time.",
  },
];

export function FaqSection() {
  const [openIndex, setOpenIndex] = React.useState<number | null>(0);

  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div className="grid gap-3">
      {FAQ_ITEMS.map((item, index) => {
        const isOpen = openIndex === index;
        return (
          <Card
            key={item.question}
            className={`transition-all duration-200 border ${
              isOpen
                ? "border-primary/40 bg-card shadow-md"
                : "border-border/70 hover:border-border hover:bg-muted/30"
            }`}
          >
            <button
              type="button"
              onClick={() => toggle(index)}
              className="flex w-full items-center justify-between gap-4 p-5 text-left font-medium text-foreground transition-colors"
              aria-expanded={isOpen}
            >
              <div className="flex items-center gap-3">
                <HelpCircle className="size-4 shrink-0 text-primary/70" />
                <span className="text-base font-semibold">{item.question}</span>
              </div>
              <ChevronDown
                className={`size-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
                  isOpen ? "rotate-180 text-primary" : ""
                }`}
              />
            </button>
            {isOpen && (
              <div className="border-t border-border/50 px-5 py-4 text-sm leading-relaxed text-muted-foreground">
                {item.answer}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
