# File Structure

Define how the project is organized and where different types of files should be located.

## Project Root Structure

## Naming Conventions

### Files

- **Components**: `PascalCase.tsx` (e.g., `UserProfile.tsx`)
- **Utilities**: `camelCase.ts` (e.g., `formatDate.ts`)
- **Constants**: `UPPER_SNAKE_CASE.ts` (e.g., `API_ENDPOINTS.ts`)
- **Tests**: `*.test.ts` or `*.spec.ts`

### Directories

- **Feature modules**: `kebab-case` (e.g., `user-profile/`)
- **Component directories**: `PascalCase` (e.g., `UserProfile/`)

## File Placement Rules

### When to Create a New File

- Each component should be in its own file
- Utilities should be grouped by functionality
- Services should be separated by domain/resource

### When to Create a New Directory

- When a feature has 3+ related files
- When components have sub-components
- When utilities grow to 5+ functions

## Import Order

Always organize imports in this order:

1. External libraries (React, lodash, etc.)
2. Internal absolute imports (@/components, @/utils)
3. Relative imports (./utils, ../components)
4. Type imports
5. CSS/Style imports

Example:

```typescript
import React from "react";
import { format } from "date-fns";

import { Button } from "@/components/common";
import { useAuth } from "@/hooks";

import { calculateTotal } from "./utils";
import type { Order } from "./types";

import "./styles.css";
```

## Critical Rules

> [!IMPORTANT]
> Add any strict file organization rules here.
