"""
French -> Greek-script transliterator.

Rules:
  - c  -> κ (hard: before a/o/u/consonant/end) or σ (soft: before e/i/y)
  - ç  -> σ
  - ch -> χ
  - x  -> χ
  - th -> θ
  - ph -> φ
  - s  -> σ (both positions, no final ς)
  - qu -> κ  (silent u)
  - é  -> έ   (acute kept as Greek tonos)
  - è  -> ὴ   (eta with grave)
  - ê  -> ῆ   (eta with circumflex/perispomeni)
  - ë  -> ε   (diaeresis dropped, vowel stays ε)
  - ô  -> ό   (circumflex rendered as acute on omicron — no perispomeni on ο)
  - â  -> ᾶ   (alpha with circumflex/perispomeni)
  - î  -> ῖ   (iota with circumflex/perispomeni)
  - û  -> ῦ   (upsilon with circumflex/perispomeni)
  - à  -> ὰ   (grave kept)
  - ù  -> ὺ
  - ï, ü, ÿ -> diaeresis dropped (no good Greek equivalent on these)
  - h  -> rough breathing ( ῾ ) on the following vowel; if no vowel follows, dropped
  - y  -> υ
  - w  -> ου
  - v  -> β

Usage:
    python french_to_greek.py "Bonjour mon ami"
    or run interactively.
"""

import sys
import re
import unicodedata


# ---------- 1. Digraphs (must be processed first) ----------
# Order matters: longer / more specific patterns first.
DIGRAPHS = [
    (r"ch", "χ"),
    (r"Ch", "Χ"),
    (r"CH", "Χ"),
    (r"th", "θ"),
    (r"Th", "Θ"),
    (r"TH", "Θ"),
    (r"ph", "φ"),
    (r"Ph", "Φ"),
    (r"PH", "Φ"),
    (r"qu", "κ"),
    (r"Qu", "Κ"),
    (r"QU", "Κ"),
]


# ---------- 2. Context-sensitive C ----------
# Soft c before e, i, y (incl. accented variants) -> σ
# Hard c everywhere else -> κ
SOFT_C_FOLLOWERS = "eiyEIYéèêëÉÈÊË"

def handle_c(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "cC":
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt in SOFT_C_FOLLOWERS:
                out.append("σ" if ch == "c" else "Σ")
            else:
                out.append("κ" if ch == "c" else "Κ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# ---------- 3. h -> rough breathing on next vowel ----------
# We mark the vowel that follows h with U+0314 (combining reversed comma above =
# rough breathing). After per-character transliteration we normalize to NFC so
# precomposed forms (ἁ, ἑ, etc.) appear where they exist.

# French vowels (incl. accented) that can carry the breathing.
H_FOLLOWING_VOWELS = set("aàâeéèêëiîïoôuùûüyÿAÀÂEÉÈÊËIÎÏOÔUÙÛÜYŸ")

ROUGH_BREATHING = "\u0314"

def handle_h(text: str) -> str:
    """Replace h with a rough-breathing mark on the following vowel."""
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "hH":
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt in H_FOLLOWING_VOWELS:
                # Drop the h; mark the next vowel.
                out.append(nxt + ROUGH_BREATHING)
                i += 2
                continue
            # No vowel after — h is just silent.
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# ---------- 4. Single-letter map (accent-preserving) ----------
SINGLE_MAP = {
    "a": "α", "A": "Α",
    "à": "ὰ", "À": "Ὰ",
    "â": "ᾶ", "Â": "Α͂",
    "b": "β", "B": "Β",
    "ç": "σ", "Ç": "Σ",
    "d": "δ", "D": "Δ",
    "e": "ε", "E": "Ε",
    "é": "έ", "É": "Έ",
    "è": "ὴ", "È": "Ὴ",
    "ê": "ῆ", "Ê": "Η͂",
    "ë": "ε", "Ë": "Ε",         # diaeresis dropped
    "f": "φ", "F": "Φ",
    "g": "γ", "G": "Γ",
    "i": "ι", "I": "Ι",
    "î": "ῖ", "Î": "Ῐ",          # capital perispomeni-iota doesn't exist precomposed
    "ï": "ι", "Ï": "Ι",
    "j": "ζ", "J": "Ζ",
    "k": "κ", "K": "Κ",
    "l": "λ", "L": "Λ",
    "m": "μ", "M": "Μ",
    "n": "ν", "N": "Ν",
    "o": "ο", "O": "Ο",
    "ô": "ό", "Ô": "Ό",         # no precomposed omicron+perispomeni; use tonos
    "p": "π", "P": "Π",
    "q": "κ", "Q": "Κ",
    "r": "ρ", "R": "Ρ",
    "s": "σ", "S": "Σ",
    "t": "τ", "T": "Τ",
    "u": "υ", "U": "Υ",
    "ù": "ὺ", "Ù": "Ὺ",
    "û": "ῦ", "Û": "Ῠ",
    "ü": "υ", "Ü": "Υ",
    "v": "β", "V": "Β",
    "w": "ου", "W": "Ου",
    "x": "χ", "X": "Χ",
    "y": "υ", "Y": "Υ",
    "ÿ": "υ", "Ÿ": "Υ",
    "z": "ζ", "Z": "Ζ",
    "œ": "ε", "Œ": "Ε",
    "æ": "ε", "Æ": "Ε",
}


def transliterate(text: str) -> str:
    # 1. Mark rough breathing for h (before digraphs, so 'ch'/'ph'/'th' are untouched —
    #    actually we need digraphs FIRST so 'ch' isn't seen as c+h).
    # Re-order: digraphs first, then h, then c, then single map.

    # 1. Digraphs.
    for pat, rep in DIGRAPHS:
        text = re.sub(pat, rep, text)

    # 2. h -> rough breathing on following vowel.
    text = handle_h(text)

    # 3. Context-sensitive c.
    text = handle_c(text)

    # 4. Per-character map.
    out = []
    for ch in text:
        if ch in SINGLE_MAP:
            out.append(SINGLE_MAP[ch])
        else:
            # Combining marks, punctuation, digits, already-Greek chars -> keep.
            out.append(ch)
    result = "".join(out)

    # 5. Normalize: decompose, then reorder so the rough breathing (̔) comes
    # before any accent marks on the same base — that's the order Unicode's
    # precomposed Greek polytonic glyphs expect — then recompose.
    result = unicodedata.normalize("NFD", result)
    result = _reorder_breathing(result)
    result = unicodedata.normalize("NFC", result)

    # 6. Final-sigma: lowercase σ at the end of a word becomes ς.
    # "End of word" = followed by anything that isn't a Greek/Latin letter,
    # or the end of the string. Apostrophes count as word boundaries
    # (so j'aime -> ζ'αιμε with no sigma anyway, but la maisons -> λα μαισονς).
    result = _apply_final_sigma(result)
    return result


def _apply_final_sigma(s: str) -> str:
    """Replace lowercase σ with ς when it's the last letter of a word."""
    out = list(s)
    n = len(out)
    for i, ch in enumerate(out):
        if ch != "σ":
            continue
        # Look at the next character.
        nxt = out[i + 1] if i + 1 < n else ""
        if not nxt or not _is_word_char(nxt):
            out[i] = "ς"
    return "".join(out)


def _is_word_char(ch: str) -> bool:
    """True if ch can be part of a word (a letter, basically). Spaces,
    punctuation, apostrophes, etc. are NOT word chars."""
    if not ch:
        return False
    # Unicode category: L* = letters, M* = combining marks (accents).
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat.startswith("M")


# Combining marks that can sit on a Greek vowel.
_ACCENT_MARKS = {
    "\u0300",  # combining grave
    "\u0301",  # combining acute (= Greek tonos after NFD)
    "\u0342",  # combining perispomeni (Greek circumflex)
    "\u0308",  # combining diaeresis
}

def _reorder_breathing(s: str) -> str:
    """Ensure rough breathing (̔, U+0314) precedes any accent mark in a
    cluster, so NFC can compose to e.g. ὅ instead of ό̔."""
    out = []
    i = 0
    while i < len(s):
        out.append(s[i])
        # Look ahead at combining marks attached to this base.
        j = i + 1
        marks = []
        while j < len(s) and unicodedata.combining(s[j]):
            marks.append(s[j])
            j += 1
        if marks:
            # Pull rough breathing to the front of the mark cluster.
            breathing = [m for m in marks if m == "\u0314"]
            rest = [m for m in marks if m != "\u0314"]
            out.extend(breathing + rest)
        i = j
    return "".join(out)


# ---------- CLI ----------
def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        print(transliterate(text))
        return

    print("French -> Greek-script transliterator")
    print("Type some French (or 'quit' to exit):\n")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in {"quit", "exit", "q"}:
            break
        print(transliterate(line))


if __name__ == "__main__":
    main()
