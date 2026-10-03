import parser from "@typescript-eslint/parser";

export default [
  { ignores: ["dist/**", "src/contracts.ts", "src-tauri/**", "node_modules/**"] },
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: { parser, parserOptions: { ecmaFeatures: { jsx: true } } },
    rules: {
      "no-async-promise-executor": "error",
      "no-unsafe-finally": "error",
      "no-constant-binary-expression": "error",
    },
  },
];
