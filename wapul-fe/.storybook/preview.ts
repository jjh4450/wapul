import type { Preview } from '@storybook/sveltekit';
// Same Tailwind entry as +layout.svelte, so shadcn tokens and utilities apply in stories.
import '../src/routes/layout.css';

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i
      }
    },

    a11y: {
      // 'todo' - show a11y violations in the test UI only
      // 'error' - fail CI on a11y violations
      // 'off' - skip a11y checks entirely
      test: 'todo'
    }
  },

  globalTypes: {
    theme: {
      description: 'Color theme',
      toolbar: {
        icon: 'mirror',
        items: [
          { value: 'light', title: 'Light' },
          { value: 'dark', title: 'Dark' }
        ],
        dynamicTitle: true
      }
    }
  },

  initialGlobals: {
    theme: 'light'
  },

  decorators: [
    // layout.css uses `.dark` class-based dark mode (`@custom-variant dark`).
    (story, context) => {
      document.documentElement.classList.toggle('dark', context.globals.theme === 'dark');
      return story();
    }
  ]
};

export default preview;
