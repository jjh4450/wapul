// Code normalization: a copy of wapul-ml's wapul_ml/normalize.py, the original. The model's
// input must go through this exactly as the training corpus did (docs/ml/index.ko.md).

// CP949 bytes saved upstream as Latin-1 text ("\u00bc\u00f6\u00b8\u00a6 \u00b4\u00e3\u00c0\u00bb" = "\uc218\ub97c \ub2f4\uc744"); recoverable.
// `[^\n]` where Python has `.`: Python's dot skips only "\n".
const LATIN1_MOJIBAKE = /(?:[\u00c0-\u00ff][\u0080-\u00ff][^\n]*){3}/;

// WHATWG "euc-kr" is the whole of CP949, as Python's cp949 codec is.
const cp949 = new TextDecoder('euc-kr');

function repairMojibake(code: string): string {
  return code.replace(/[\u0080-\u00ff]+/g, (run) =>
    cp949.decode(Uint8Array.from(run, (ch) => ch.charCodeAt(0)))
  );
}

// Unicode spaces (NBSP, hair space...) -> " "; zero-width, control, private-use and U+FFFD
// (text already lost upstream) -> dropped. ASCII printable, tab and newline stay.
// Unassigned (Cn) depends on the engine's Unicode version, as Python's does on its own.
function cleanChar(ch: string): string {
  if (ch === '\t' || ch === '\n' || /^[\x20-\x7e]$/.test(ch)) {
    return ch;
  }

  if (ch === '\ufffd') {
    return '';
  }

  if (/^\p{Zs}$/u.test(ch)) {
    return ' ';
  }

  if (/^[\p{Cc}\p{Cf}\p{Co}\p{Cn}]$/u.test(ch)) {
    return '';
  }

  return ch;
}

export function cleanText(text: string): string {
  let out = '';

  for (const ch of text) {
    out += cleanChar(ch);
  }

  return out;
}

// What Python's str.rstrip() can still find after cleanText: Zs became " ", Cc and Cf are gone.
const TRAILING = /[ \t\u2028\u2029]+$/;

/** LF line endings, Latin-1 mojibake repaired, no invisible chars, no trailing whitespace, no
 * leading/trailing blank lines. */
export function normalize(code: string): string {
  code = code.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  if (LATIN1_MOJIBAKE.test(code)) {
    code = repairMojibake(code);
  }

  code = cleanText(code);
  const lines = code.split('\n').map((line) => line.replace(TRAILING, ''));

  return lines.join('\n').replace(/^\n+/, '').replace(/\n+$/, '') + '\n';
}
