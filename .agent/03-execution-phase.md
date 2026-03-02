# Execution Phase

## Overview

The Execution Phase is where the plan becomes reality. This is when code is written, files are modified, and the steps outlined in the plan are systematically executed.

## Key Principle

**Follow the plan.** Execution should align with the approved `<number>-plan.md` file, proceeding through phases and steps in order.

## Workflow

### 1. Reference the Plan

- Work from the active `<number>-plan.md` file
- Execute steps in the order specified
- Check off phases and steps as they're completed

### 2. Execute Systematically

For each phase:

1. Read the phase goal and all steps
2. Execute each step in order
3. Verify the step worked as expected
4. Move to the next step

### 3. Phase Gate

1. **Execute only one phase** at a time
2. **Notify the user** when a phase is complete
3. **Wait for explicit confirmation** before moving to the next phase

### 4. Handle Problems **CRITICAL WORKFLOW**

When issues arise during execution:

**AI MUST follow this exact workflow:**

1. **STOP execution** immediately when AI encounters a problem
2. **Report to you in chat**:
   - Problem description
   - Phase and Step where it occurred
   - Root cause (if known)
   - Proposed solution
3. **WAIT for your explicit approval**
4. **ONLY when you say** "add this to the problems file" or similar command:
   - Then AI updates `<number>-probs.md`

**AI MUST NOT update the problems file without your explicit command.**

### 5. Handle Flags **CRITICAL WORKFLOW**

If vulnerabilities or limitations are discovered during execution:

**AI MUST follow this exact workflow:**

1. **STOP and report to you in chat**:
   - What the flag/limitation/vulnerability is
   - Why it should be flagged
   - Impact and potential solutions
2. **WAIT for your explicit approval**
3. **ONLY when you say** "add this to the flags file" or similar command:
   - Then AI updates `<number>-flag.md`

**AI MUST NOT update the flags file without your explicit command.**

### 6. Adapt When Needed

If the plan needs adjustment during execution:

1. **Stop execution**
2. **Discuss the issue** (like Discussion Phase)
3. **Update the plan** if you approve changes
4. **Resume execution** with the updated plan

## Communication During Execution

### Progress Updates

I'll periodically update you on:

- Which phase we're currently in
- Which step is being executed
- Any notable observations

### Asking for Input

I'll ask for your input when:

- A problem is encountered
- A flag/vulnerability is discovered
- The plan needs modification
- Clarification is needed on a step

## Code Standards

All code written follows:

- Your critical coding standards (from user rules)
- Existing codebase patterns and conventions
- Best practices for the language/framework

## Testing & Verification

After executing steps that involve code changes:

- Run relevant tests (if applicable)
- Verify the change works as intended
- Check for any breaking changes

## When This Phase Ends

This phase concludes when:

- ✅ All phases and steps in the plan are completed
- ✅ All code changes have been made
- ✅ Testing confirms everything works
- ✅ Problems and flags are documented (if requested)

## Output

- Modified/new code files as specified in the plan
- Updated `<number>-probs.md` (if problems were documented)
- Updated `<number>-flag.md` (if flags were documented)

## After Execution

Once execution is complete:

- We can review what was accomplished
- You can test the changes manually
- We can start a new Discussion Phase for the next task
