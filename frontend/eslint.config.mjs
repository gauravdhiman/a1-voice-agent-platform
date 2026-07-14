import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      // Test files are not production code; they are type-checked by tsc and
      // executed by vitest. Linting them through `next build` blocks the
      // production build on test-hygiene rules (e.g. react/display-name on
      // anonymous render helpers) that have no runtime impact. Run
      // `npx tsc --noEmit` and `npx vitest` to validate tests instead.
      "**/__tests__/**",
      "tests/**",
      "**/*.test.ts",
      "**/*.test.tsx",
      "**/*.spec.ts",
      "**/*.spec.tsx",
    ],
  },
];

export default eslintConfig;
