# Claude Documentation for Mirra MVP

**Project**: Mirra - Full virtual try-on platform with measurement-based digital twins and 3D clothing assets.

## What is Mirra?

Mirra enables customers to see how clothes actually look and fit on their own body. We do this by: (1) creating a personalized 3D digital twin from body measurements, (2) converting 2D product images into 3D reusable garment patterns, and (3) combining both to generate physics-simulated virtual try-ons. The result is a trustworthy, personalized clothing fit experience.

## Quick Checklist - What to Read Based on Your Task

**Working on Step 1 (Avatar Generation)?**
- Read: `CLAUDE.md` (this file)
- Read: `.claude/current-roadmap.md` (3 min)
- Read: `.claude/architecture/architecture.md` (5 min)
- Read: `.claude/architecture/step_1_avatar.md` (10 min) 
- ⭐ SKIP step_2 and step_3 files
- Read: `.claude/commands/start-work.md` → Step 1 section
- Reference: `.claude/quick-reference.md` → Step 1 section
- Lookup: `.claude/faq.md` → Step 1 section
- Debug: `.claude/troubleshooting.md` → Step 1 section

**Working on Step 2 (Product Ingestion)?**
- Read: `CLAUDE.md` (this file)
- Read: `.claude/current-roadmap.md` (3 min)
- Read: `.claude/architecture/architecture.md` (5 min)
- Read: `.claude/architecture/step_2_ingestion.md` (10 min) 
- ⭐ SKIP step_1 and step_3 files
- Read: `.claude/commands/start-work.md` → Step 2 section
- Reference: `.claude/quick-reference.md` → Step 2 section
- Lookup: `.claude/faq.md` → Step 2 section
- Debug: `.claude/troubleshooting.md` → Step 2 section

**Working on Step 3 (Virtual Try-On)?**
- Read: `CLAUDE.md` (this file)
- Read: `.claude/current-roadmap.md` (3 min)
- Read: `.claude/architecture/architecture.md` (5 min)
- Read: `.claude/architecture/step_3_vto.md` (10 min) 
- ⭐ SKIP step_1 and step_2 files
- Read: `.claude/commands/start-work.md` → Step 3 section
- Reference: `.claude/quick-reference.md` → Step 3 section
- Lookup: `.claude/faq.md` → Step 3 section
- Debug: `.claude/troubleshooting.md` → Step 3 section

**Need Project Context?**
- Read: `.claude/project-context.md` (business vision, goals, constraints)
- Read: `.claude/repo-rules.md` (how to code here)

---

## Critical Commands (Copy-Paste)

**Step 1: Avatar Generation**
```bash
python clo_avatar_generation/run_avatar.py
```

**Step 2: Product Ingestion**
```bash
python product_ingestion/run_product_ingestion.py
```

**Step 3: Virtual Try-On**
```bash
python clo_avatar_generation/run_clo_vto.py
```

---

## Critical Things to Remember

1. **Command Format**: Use repo-root relative paths. NOT `python -m`. 
   - ✅ Correct: `python clo_avatar_generation/run_avatar.py`
   - ❌ Wrong: `python -m clo_avatar_generation.run_avatar`

2. **Each Step is Sequential**:
   - Step 1 and Step 2 are **independent** (can run in parallel)
   - Step 3 **requires** both Step 1 and Step 2 outputs

3. **Output Artifacts**: 
   - Step 1 output: `output/<user_id>-<run_number>/`
   - Step 2 output: `output/<cloth_id>-<size_id>-<run_number>/`
   - Step 3 output: `output/native_vto_report.json`
   - Always check `.json` files in output/ for step results

4. **Step-Specific Architecture**:
   - Read ONLY the architecture file for your step to save context
   - High-level architecture is in `.claude/architecture/architecture.md`
   - Detailed pipeline info is in `.claude/architecture/step_N_*.md`

5. **Half-Girth Convention** (Step 2 → Step 3):
   - All width/girth measurements in Step 2 are **flat seam-to-seam** (half of circumference)
   - This is critical for Step 3 seam creation
   - See `.claude/quick-reference.md` Step 2 section for details

---

## Where to Find Everything

| Need | Location |
|------|----------|
| Project vision & goals | `.claude/project-context.md` |
| How to code here | `.claude/repo-rules.md` |
| High-level architecture | `.claude/architecture/architecture.md` |
| Step 1 deep-dive | `.claude/architecture/step_1_avatar.md` |
| Step 2 deep-dive | `.claude/architecture/step_2_ingestion.md` |
| Step 3 deep-dive | `.claude/architecture/step_3_vto.md` |
| Quick checklists & lookups | `.claude/quick-reference.md` |
| Common questions | `.claude/faq.md` |
| Known issues & solutions | `.claude/troubleshooting.md` |
| How to start work | `.claude/commands/start-work.md` |
| Project status & priorities | `.claude/current-roadmap.md` |
| Business requirements | `.claude/context/` |
| Technical standards | `.claude/coding-rules/` |
| Planning phase docs | `.claude/planning/` |

---

## How to Ask Questions

1. **Quick answer?** → Check `.claude/faq.md` (your step section)
2. **Known issue?** → Check `.claude/troubleshooting.md` (your step section)
3. **Stuck on architecture?** → Check `.claude/architecture/step_N_*.md`
4. **Need conventions?** → Check `.claude/repo-rules.md`
5. **Still lost?** → Ask in context (I'll help guide you)

---

## How Claude Works on Files

When making changes to a file, Claude will:

1. **Read the file once** to understand its full structure
2. **Plan all changes** needed for that file
3. **Ask for permission once** with a complete list of changes, OR
4. **Make all changes in a single request** rather than multiple sequential edits

**Why?** This approach is more efficient, cleaner, and respects your time by bundling related changes instead of making many small edits.

**If you disagree** with a proposed change list, just say so and Claude will adjust. **If you want to make changes yourself**, just tell Claude to wait or skip that file.

---

## Project Navigation

```
Mirra MVP
├── Step 1: Avatar Generation (measurement → 3D body)
├── Step 2: Product Ingestion (2D image → 3D patterns)
└── Step 3: Virtual Try-On (avatar + patterns → VTO)
```

**Start here**: Pick a step above, then read its architecture file + relevant sections.

---

*Last updated: 2026-05-16*
