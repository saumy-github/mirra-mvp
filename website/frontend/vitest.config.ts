import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

/**
 * Unit tests for the dashboard's data layer.
 *
 * These deliberately test the modules that encode the product's safety
 * properties — lifecycle transitions, requirement validation, authorization,
 * revision invalidation, inventory policy, reporting windows, and the
 * dashboard-to-storefront publication contract — rather than rendering.
 * Those are the rules a regression would break silently.
 */
export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
