// Keeps every component under src/lib/components paired with a Storybook story.
//
//   node tools/ui-stories.ts                 scaffold stories for components that lack one
//   node tools/ui-stories.ts --check         exit 1 if any component lacks a story
//   node tools/ui-stories.ts --add <name...> shadcn-svelte add, prettier, then scaffold
//
// A component unit is a direct child of src/lib/components/ or src/lib/components/ui/:
// either a folder (shadcn style, needs any *.stories.svelte inside) or a single
// Name.svelte file (needs a sibling Name.stories.svelte).
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');

const componentsDir = path.join(root, 'src/lib/components');

const uiDir = path.join(componentsDir, 'ui');

type Unit = {
  name: string;
  title: string;
  dir: string;
  file: string | null;
};

function pascal(name: string): string {
  return name.replace(/(^|[-_])([a-z0-9])/g, (_, __, c: string) => c.toUpperCase());
}

function listUnits(dir: string, group: string): Unit[] {
  if (!existsSync(dir)) return [];

  const units: Unit[] = [];

  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);

    if (full === uiDir) continue;

    if (statSync(full).isDirectory()) {
      units.push({ name: entry, title: `${group}/${pascal(entry)}`, dir: full, file: null });
    } else if (entry.endsWith('.svelte') && !entry.endsWith('.stories.svelte')) {
      const base = entry.slice(0, -'.svelte'.length);
      units.push({ name: base, title: `${group}/${base}`, dir, file: full });
    }
  }

  return units;
}

function storyPath(unit: Unit): string {
  return path.join(
    unit.dir,
    `${unit.file === null ? unit.name : path.parse(unit.file).name}.stories.svelte`
  );
}

function hasStory(unit: Unit): boolean {
  if (unit.file !== null) return existsSync(storyPath(unit));

  return readdirSync(unit.dir).some((f) => f.endsWith('.stories.svelte'));
}

// Void components (input, separator, ...) never render `children`; passing text to them breaks.
function rendersChildren(source: string): boolean {
  return /\bchildren\b/.test(source);
}

function render(tag: string, label: string, withChildren: boolean): string {
  return withChildren ? `<${tag}>${label}</${tag}>` : `<${tag} />`;
}

function scaffold(unit: Unit): string | null {
  const head = `<script module lang="ts">\n  import { defineMeta } from '@storybook/addon-svelte-csf';\n`;

  if (unit.file !== null) {
    const ident = pascal(unit.name);
    const body = render(ident, unit.name, rendersChildren(readFileSync(unit.file, 'utf8')));

    return `${head}  import ${ident} from './${unit.name}.svelte';

  const { Story } = defineMeta({
    title: '${unit.title}',
    component: ${ident},
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  ${body}
</Story>
`;
  }

  const index = path.join(unit.dir, 'index.ts');
  const main = path.join(unit.dir, `${unit.name}.svelte`);

  // Without the shadcn index.ts + <name>.svelte layout there is no safe entry point to guess.
  if (!existsSync(index) || !existsSync(main)) return null;

  const ns = pascal(unit.name);
  const exportsRoot = /\bRoot\b/.test(readFileSync(index, 'utf8'));

  if (!exportsRoot) return null;

  const body = render(`${ns}.Root`, ns, rendersChildren(readFileSync(main, 'utf8')));

  return `${head}  import * as ${ns} from './index.js';

  const { Story } = defineMeta({
    title: '${unit.title}',
    component: ${ns}.Root,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  ${body}
</Story>
`;
}

function allUnits(): Unit[] {
  return [...listUnits(uiDir, 'UI'), ...listUnits(componentsDir, 'Components')];
}

function generate(): string[] {
  const written: string[] = [];

  for (const unit of allUnits()) {
    if (hasStory(unit)) continue;

    const source = scaffold(unit);

    if (source === null) {
      console.warn(`skip ${path.relative(root, unit.dir)}: write a story by hand`);
      continue;
    }

    const target = storyPath(unit);
    writeFileSync(target, source);
    written.push(target);
    console.log(`story ${path.relative(root, target)}`);
  }

  return written;
}

function check(): void {
  const missing = allUnits().filter((u) => !hasStory(u));

  if (missing.length === 0) return;

  console.error('Components without a Storybook story:');

  for (const unit of missing) {
    console.error(`  ${path.relative(root, unit.file ?? unit.dir)}`);
  }

  console.error('Run `pnpm ui:stories` to scaffold them.');
  process.exit(1);
}

function add(names: string[]): void {
  const run = (cmd: string, args: string[]) =>
    execFileSync(cmd, args, { cwd: root, stdio: 'inherit' });

  run('pnpm', ['exec', 'shadcn-svelte', 'add', ...names]);

  const written = generate();

  const dirs = names.flatMap((n) => {
    const dir = path.join(uiDir, n);

    return existsSync(dir) ? [dir] : [];
  });

  // shadcn output does not follow this repo's prettier config.
  run('pnpm', ['exec', 'prettier', '--write', ...dirs, ...written]);
}

const [flag, ...rest] = process.argv.slice(2);

if (flag === '--check') check();
else if (flag === '--add') add(rest);
else generate();
