# Planning Phase

## Overview

The Planning Phase transforms our discussion into a structured, actionable plan. This phase generates four interconnected files that track the plan, problems, future considerations, and learnings.

## Key Principle

**No code is written in this phase.** Plans describe _what_ to do and _how_ to approach it, but contain no implementation code.

## Files Generated

For each plan, four files are created in the `plans/` directory with the same number prefix:

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

### 2. `<number>-probs.md` - Problems File

**Purpose**: Track problems encountered during execution and their solutions.

**Structure**:

```markdown
# Problems: Plan <number>

## Phase X, Step Y: [Problem Description]

**Problem**: Detailed description of what went wrong

**Attempted Solutions**:

1. What we tried first (and why it didn't work)
2. What we tried second

**Resolution**:

- How we solved it, OR
- "Left for future" with explanation

**Date**: YYYY-MM-DD

---

## Phase X, Step Z: [Problem Description]

...
```

**Important**:

- **Only created/updated when you explicitly ask me to document a problem**
- Starts empty when the plan is first created
- Added to incrementally as issues arise

**CRITICAL WORKFLOW** (AI must follow):

1. When AI encounters a problem during execution, AI **MUST**:
   - STOP and report the problem to you in chat
   - Explain the root cause and proposed solution
   - Wait for your explicit approval
2. Only when you say **"add this to the problems file"** or similar command:
   - Then AI updates the `<number>-probs.md` file
3. AI **MUST NOT** update this file without your approval

### 3. `<number>-flag.md` - Flags File

**Purpose**: Document vulnerabilities, limitations, and items deferred for future work.

**Structure**:

```markdown
# Flags: Plan <number>

## 🚩 Vulnerabilities

### [Vulnerability Name]

**Type**: Security / Performance / Scalability / etc.
**Description**: What the vulnerability is
**Impact**: Potential consequences
**Mitigation**: What we did to minimize it (if anything)
**Status**: Unresolved / Partially Addressed / Accepted Risk

---

## 🔮 Future Considerations

### [Feature/Improvement Name]

**Description**: What should be done in the future
**Reason**: Why it's not being done now
**Priority**: Low / Medium / High

---

## ⚠️ Known Limitations

### [Limitation Name]

**Description**: What the limitation is
**Impact**: How it affects functionality
**Workaround**: Any temporary solutions in place
```

**Important**:

- **Only created/updated when you explicitly ask me to document a flag**
- Starts empty when the plan is first created
- Used to track things we're aware of but not addressing immediately

**CRITICAL WORKFLOW** (AI must follow):

1. When AI identifies a flag/limitation/vulnerability during execution, AI **MUST**:
   - STOP and report it to you in chat
   - Explain why it should be flagged
   - Wait for your explicit approval
2. Only when you say **"add this to the flags file"** or similar command:
   - Then AI updates the `<number>-flag.md` file
3. AI **MUST NOT** update this file without your approval

### 4. `<number>-learning.md` - Learning File

**Purpose**: Document new topics, patterns, and technical knowledge discovered while working with the codebase.

**Structure**:

```markdown
# Learning: Plan <number>

## [Topic/Concept Name]

**Category**: Architecture / Pattern / Library / API / etc.
**Description**: What was learned
**Context**: Where this was found in the codebase
**Resources**: Links or references for further reading (if applicable)
**Date**: YYYY-MM-DD

---

## [Another Topic]

...
```

**Important**:

- **Only created/updated when you explicitly ask me to document learnings**
- Starts empty when the plan is first created
- Used to capture knowledge discovered during code exploration

## Workflow

1. **I create the plan file** (`<number>-plan.md`) with phases and steps
2. **I create empty placeholder files** for `<number>-probs.md`, `<number>-flag.md`, and `<number>-learning.md`
3. **You review the plan** and provide feedback
4. **We iterate** on the plan until you approve it
5. **During execution**, you tell me when to document problems, flags, or learnings

## Numbering Convention

Plans are numbered sequentially with 3-digit zero-padding:

- `001-plan.md`, `001-probs.md`, `001-flag.md`, `001-learning.md`
- `002-plan.md`, `002-probs.md`, `002-flag.md`, `002-learning.md`
- etc.

## When This Phase Ends

This phase concludes when:

- ✅ The plan file is complete and approved
- ✅ Placeholder files are created for probs, flags, and learning
- ✅ You explicitly ask to move to the Execution Phase

## Output

Four files in the `plans/` directory:

- `<number>-plan.md` (complete)
- `<number>-probs.md` (empty initially)
- `<number>-flag.md` (empty initially)
- `<number>-learning.md` (empty initially)

## Next Phase

Once planning is complete and approved, we move to the [Execution Phase](03-execution-phase.md) where code is written.
