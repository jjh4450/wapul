"""Code normalization shared by the training corpus and inference: input code must match it.

Standard library only, so the dataset build can import it without the model's dependencies.
"""

import re
import unicodedata

# CP949 bytes saved upstream as Latin-1 text ("¼ö¸¦ ´ãÀ»" = "수를 담을"); recoverable
LATIN1_MOJIBAKE = re.compile(r"(?:[\u00c0-\u00ff][\u0080-\u00ff].*){3}")


def clean_char(ch: str) -> str:
    """Unicode spaces (NBSP, hair space...) -> " "; zero-width, control, private-use and
    U+FFFD (text already lost upstream) -> dropped."""
    if ch in "\t\n" or ch.isascii() and ch.isprintable():
        return ch
    if ch == "�":
        return ""
    cat = unicodedata.category(ch)
    if cat == "Zs":
        return " "
    if cat in ("Cc", "Cf", "Co", "Cn"):
        return ""
    return ch


def clean_text(text: str) -> str:
    return "".join(map(clean_char, text))


def normalize(code: str) -> str:
    """LF line endings, Latin-1 mojibake repaired, no invisible chars, no trailing whitespace, no leading/trailing blank lines."""
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    if LATIN1_MOJIBAKE.search(code):
        code = re.sub(r"[\u0080-ÿ]+", lambda m: m.group().encode("latin-1").decode("cp949", "replace"), code)
    code = clean_text(code)
    lines = [line.rstrip() for line in code.split("\n")]
    return "\n".join(lines).strip("\n") + "\n"
