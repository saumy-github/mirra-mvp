# Agent Planning Directory

This directory contains planning documents and workflows for AI-assisted development tasks.

## Purpose

The `.agent` folder serves as a centralized location for:

- **Task Planning**: Breaking down complex requests into actionable steps
- **Implementation Plans**: Detailed technical plans before executing changes
- **Workflows**: Reusable procedures for common development tasks
- **Progress Tracking**: Documenting what has been accomplished

## Workflow Phases

All development work follows a structured 3-phase approach:

### 1. **Discussion Phase**

Collaborative exploration and requirement gathering. We discuss what needs to be done, ask questions, explore better options, and identify potential vulnerabilities.

- **Output**: None (no files or code generated)
- **Details**: See [01-discussion-phase.md](01-discussion-phase.md)

### 2. **Planning Phase**

Create a detailed plan with tracking for problems and future considerations. For each plan, four files are generated:

- `<number>-plan.md` - Phases and steps breakdown
- `<number>-probs.md` - Problems encountered and solutions
- `<number>-flag.md` - Vulnerabilities and items left for future
- `<number>-learning.md` - New topics and learnings discovered in the code
- **No code is written in this phase**
- **Details**: See [02-planning-phase.md](02-planning-phase.md)

### 3. **Execution Phase**

Execute the plan systematically, following the steps outlined in the plan.md file.

- **Output**: Code changes as per plan
- **Details**: See [03-execution-phase.md](03-execution-phase.md)

## Structure

```plain
.agent/
├── README.md                  # Overview of the 3-phase workflow
├── 01-discussion-phase.md     # Detailed guide for Discussion Phase
├── 02-planning-phase.md       # Detailed guide for Planning Phase
├── 03-execution-phase.md      # Detailed guide for Execution Phase
├── context/                   # Project context and requirements
│   ├── README.md
│   └── [context documents]
├── coding-rules/              # Technical standards and conventions
│   ├── README.md
│   ├── tech-stack.md
│   ├── file-structure.md
│   ├── coding-style.md
│   └── [other rules]
├── plans/                     # All plan files organized by number
│   ├── 001-plan.md
│   ├── 001-probs.md
│   ├── 001-flag.md
│   ├── 001-learning.md
│   ├── 002-plan.md
│   └── ...
└── workflows/                 # Reusable workflow procedures (if needed)
```

## Benefits

- **Transparency**: You can see exactly what I plan to do before I do it
- **Collaboration**: Easier to provide feedback on the approach
- **Documentation**: Clear record of what was done and why
- **Efficiency**: Workflows can be reused for repetitive tasks
