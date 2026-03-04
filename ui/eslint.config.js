import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting';
import globals from 'globals';

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{js,mjs,jsx,vue}'],
  },

  {
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/node_modules/**', '**/venv/**'],
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  {
    name: 'app/custom-rules',
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      // Disable for Vue 3 - v-model with arguments is the correct syntax in Vue 3
      // This allows using v-model:propName="value" patterns
      'vue/no-v-model-argument': 'off',
    },
  },

  skipFormatting,
];
