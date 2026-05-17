# Planning Phase

## Overview

The Planning Phase transforms our discussion into a structured, actionable plan. This phase generates four interconnected files that track the plan, problems, future considerations, and learnings.

## Key Principle

**No code is written in this phase.** Plans describe _what_ to do and _how_ to approach it, but contain no implementation code.

## Files Generated

For each plan, one file is created in the `plans/` directory with the same number prefix:

### 1. `<number>-plan.md` - The Plan File

**Purpose**: Break down the work into phases and steps.

**Structure**:

```markdown
# Plan <number>: [Title]

## Overview

Brief description of what this plan accomplishes

## Phases

### Phase 1: [Phase Name]

**Goal**: What this phase achieves

**Steps**:

1. [Specific action to take]
2. [Specific action to take]
3. [Specific action to take]

### Phase 2: [Phase Name]

**Goal**: What this phase achieves

**Steps**:

1. [Specific action to take]
2. [Specific action to take]

## Dependencies

- Any prerequisites or required setup

## Expected Outcomes

- What should be accomplished when the plan is complete
```

**Important**:

- No code snippets in the plan
- Only high-level descriptions of what to do
- Focus on the logical flow and order of operations

**Manual Verification**:

- At the end of each plan, include a "Manual Verification Checklist" section
- This lists what the user needs to verify manually after execution
- AI will NOT verify automatically unless specifically asked by the user
- Keep the checklist concise and actionable


**CRITICAL WORKFLOW** (AI must follow):

1. When AI identifies a flag/limitation/vulnerability during execution, AI **MUST**:
   - STOP and report it to you in chat
   - Explain why it should be flagged
   - Wait for your explicit approval


## Numbering Convention

Plans are numbered sequentially with 3-digit zero-padding:

- `001-plan.md`, 
- `002-plan.md`, 
- etc.

## When This Phase Ends

This phase concludes when:

- ✅ The plan file is complete and approved
- ✅ You explicitly ask to move to the Execution Phase

## Output

Four files in the `plans/` directory:

- `<number>-plan.md` (complete)

## Next Phase

Once planning is complete and approved, we move to the [Execution Phase](03-execution-phase.md) where code is written.
