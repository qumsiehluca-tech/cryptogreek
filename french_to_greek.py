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


def transliterate(text: str, hellenize: bool = False) -> str:
    # 1. Digraphs (ch, th, ph, qu) before everything.
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
            out.append(ch)
    result = "".join(out)

    # 5. Reorder combining marks (breathing before accents) and compose.
    result = unicodedata.normalize("NFD", result)
    result = _reorder_breathing(result)
    result = unicodedata.normalize("NFC", result)

    # 6. Coronis for elision: ' or ' between letters -> ᾽ (Greek koronis).
    result = _apply_coronis(result)

    # 7. Optional: morphological hellenization (-tion -> -σιον, -e silent, etc.)
    if hellenize:
        result = _hellenize(result)

    # 8. Final-sigma: lowercase σ at end-of-word -> ς. (After hellenize so
    # newly-introduced sigmas at word-end also get the right form.)
    result = _apply_final_sigma(result)

    # 9. Acute -> grave on ultima before another word (Ancient Greek rule).
    result = _apply_grave_rule(result)

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


# ----------------------------------------------------------------------------
# Coronis (᾽) for elisions
# ----------------------------------------------------------------------------
# When an apostrophe sits between two letters (as in j'aime, l'homme,
# qu'est-ce), it marks an elision. Ancient Greek wrote this with a 'koronis',
# U+1FBD, which looks like a high comma but is the proper character. We
# replace any flavour of apostrophe (ASCII ', curly ', curly ') in that
# context. Standalone apostrophes (e.g. as quotation marks) are left alone.

CORONIS = "\u1FBD"   # ᾽
_APOSTROPHES = {"'", "\u2019", "\u2018", "\u02BC"}  # straight + curly + modifier

def _apply_coronis(s: str) -> str:
    out = list(s)
    n = len(out)
    for i, ch in enumerate(out):
        if ch in _APOSTROPHES:
            prev = out[i - 1] if i > 0 else ""
            nxt  = out[i + 1] if i + 1 < n else ""
            if _is_word_char(prev) and _is_word_char(nxt):
                out[i] = CORONIS
    return "".join(out)


# ----------------------------------------------------------------------------
# Ancient-Greek acute-to-grave rule
# ----------------------------------------------------------------------------
# In a connected sentence, an acute accent on the ultima (last syllable)
# becomes a grave when another word follows (and that word isn't an
# enclitic, and isn't sentence-final / before punctuation).
#
# We approximate "another word follows" as: the next non-whitespace char
# after the word is a letter (i.e. another word, not punctuation, not end).

# Mapping of Greek vowels with acute (tonos) -> the same vowel with grave (varia).
_ACUTE_TO_GRAVE = {
    "ά": "ὰ", "Ά": "Ὰ",
    "έ": "ὲ", "Έ": "Ὲ",
    "ή": "ὴ", "Ή": "Ὴ",
    "ί": "ὶ", "Ί": "Ὶ",
    "ό": "ὸ", "Ό": "Ὸ",
    "ύ": "ὺ", "Ύ": "Ὺ",
    "ώ": "ὼ", "Ώ": "Ὼ",
    # acute + smooth/rough breathing combos
    "ἄ": "ἂ", "ἅ": "ἃ", "Ἄ": "Ἂ", "Ἅ": "Ἃ",
    "ἔ": "ἒ", "ἕ": "ἓ", "Ἔ": "Ἒ", "Ἕ": "Ἓ",
    "ἤ": "ἢ", "ἥ": "ἣ", "Ἤ": "Ἢ", "Ἥ": "Ἣ",
    "ἴ": "ἲ", "ἵ": "ἳ", "Ἴ": "Ἲ", "Ἵ": "Ἳ",
    "ὄ": "ὂ", "ὅ": "ὃ", "Ὄ": "Ὂ", "Ὅ": "Ὃ",
    "ὔ": "ὒ", "ὕ": "ὓ",           "Ὕ": "Ὓ",
    "ὤ": "ὢ", "ὥ": "ὣ", "Ὤ": "Ὢ", "Ὥ": "Ὣ",
}

def _apply_grave_rule(s: str) -> str:
    """If a word's last syllable carries an acute and the very next word in
    the text is also a letter (i.e. another word follows in the same breath),
    swap that acute for a grave.

    Approximation of 'last syllable': the rightmost acute-bearing vowel must
    not be followed by any other vowel within the same word. (A vowel after
    it would mean the acute is NOT on the ultima.)
    """
    i = 0
    n = len(s)
    out = list(s)
    while i < n:
        if not _is_word_char(out[i]):
            i += 1
            continue
        # Find end of current word.
        j = i
        while j < n and (_is_word_char(out[j]) or out[j] == CORONIS):
            j += 1
        # Skip whitespace, see if a word follows.
        k = j
        while k < n and out[k].isspace():
            k += 1
        following_is_word = (k < n and _is_word_char(out[k]))

        if following_is_word:
            # Find rightmost acute-bearing vowel.
            for x in range(j - 1, i - 1, -1):
                ch = out[x]
                if ch in _ACUTE_TO_GRAVE:
                    # Check: are there other vowels AFTER position x in the word?
                    has_vowel_after = any(
                        _strip_one_accent(out[y]) in _GREEK_VOWELS_LOW
                        for y in range(x + 1, j)
                    )
                    if not has_vowel_after:
                        out[x] = _ACUTE_TO_GRAVE[ch]
                    break
        i = j
    return "".join(out)


def _strip_one_accent(ch: str) -> str:
    """Lowercase + strip combining marks from a single character."""
    d = unicodedata.normalize("NFD", ch.lower())
    return "".join(c for c in d if not unicodedata.combining(c))


# ----------------------------------------------------------------------------
# Hellenize: morphological substitution mode
# ----------------------------------------------------------------------------
# Applies on the already-transliterated Greek-letter text, word by word.
# Substitutions are anchored to word-end and tried longest-first.

# Each rule is (suffix_in_greek_letters, replacement). The suffixes are what
# the French endings become AFTER transliteration. The rules apply to a
# lowercase view of the word; the script preserves the original case.
_HELLENIZE_RULES = [
    # 6-char suffixes
    ("μεντε", "μενος"),    # rare; -mment-e?

    # 5-char
    ("τιον", "σιον"),      # nation -> νατιον -> νασιον (post-c-rule)
    ("σιον", "σιον"),      # already
    ("τριχε", "τρις"),     # actrice -> ακτριχε -> ακτρις
    ("μεντ", "μεν"),       # adverbial -ment: parlment ... actually leave
    ("ισμε", "ισμος"),     # idealisme -> ιδεαλισμε -> ιδεαλισμος
    ("ιστε", "ιστης"),     # artiste -> αρτιστε -> αρτιστης
    ("ικε",  "ικος"),      # politique -> πολιτικε -> πολιτικος
    ("ιτέ",  "οτης"),      # liberté/égalité -> -ιτέ -> -οτης
    ("ιτε",  "οτης"),      # same without accent
    ("ευχ",  "ος"),        # -eux -> -ευχ -> -ος (heureux, dangereux)
    ("ευσε", "ωσα"),       # -euse (fem) -> -ωσα

    # 4-char
    ("ευρ",  "ωρ"),        # docteur -> δοκτευρ -> δοκτωρ
    ("εαυ",  "ος"),        # bateau -> βατεαυ -> βατος
    ("αυτ",  "ος"),        # haut, défaut endings
    ("αυδ",  "ος"),        # similar

    # 3-char  (-ie at end as "ιε" -> "ια"; only on words >=4 chars)
    ("ιε",  "ια"),         # philosophie -> -ιε -> -ια

    # 2-char  silent -e
    # (handled separately below — needs more care)
]

# Set of single vowels (lowercase Greek) for the silent-e check.
_GREEK_VOWELS_LOW = set("αεηιουωάέήίόύώὰὲὴὶὸὺὼᾶῆῖῦῶἀἁἐἑἠἡἰἱὀὁὐὑὠὡἄἅἔἕἤἥἴἵὄὅὔὕὤὥἂἃἒἓἢἣἲἳὂὃὒὓὢὣᾳῃῳ")

def _hellenize(s: str) -> str:
    """Apply morphological substitutions word-by-word."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        if not _is_word_char(s[i]):
            out.append(s[i])
            i += 1
            continue
        # Collect a word
        j = i
        while j < n and (_is_word_char(s[j]) or s[j] == CORONIS):
            j += 1
        word = s[i:j]
        out.append(_hellenize_word(word))
        i = j
    return "".join(out)

def _hellenize_word(word: str) -> str:
    """Apply suffix rewrites to a single word, plus the silent-e + double-consonant rules."""
    if not word:
        return word

    # Skip very short words — they're usually function words that don't
    # benefit from morphological rewriting and break easily.
    if len(word) <= 2:
        return word

    # Reduce double consonants to single (Greek pattern). Do this BEFORE
    # suffix rewriting so e.g. "βελλε" -> "βελε" -> drop final ε.
    word = _collapse_doubles(word)

    # Try suffix replacement rules, longest first (they're already ordered).
    lower = _strip_accents_lower(word)
    for suffix, replacement in _HELLENIZE_RULES:
        if lower.endswith(suffix):
            stem = word[: len(word) - len(suffix)]
            # Preserve initial capitalization if the original word was capitalized.
            new = stem + replacement
            if word[0].isupper():
                new = new[0].upper() + new[1:]
            return new

    # No suffix matched — handle silent final-e (single ε at end after a consonant).
    return _drop_silent_e(word)


def _collapse_doubles(word: str) -> str:
    """λλ -> λ, ττ -> τ, σσ -> σ, etc. — but only consonants."""
    consonants = set("βγδζθκλμνξπρσςτφχψ")
    out = []
    prev = ""
    for ch in word:
        if ch.lower() in consonants and ch.lower() == prev.lower():
            continue   # skip the duplicate
        out.append(ch)
        prev = ch
    return "".join(out)


def _drop_silent_e(word: str) -> str:
    """If the word ends in unstressed ε after a consonant, drop it.
    This mirrors French silent-e at end of word."""
    if len(word) < 3:
        return word
    last = word[-1]
    second_last = word[-2]
    # Only drop a bare ε (unaccented) — never έ, η, ή, etc.
    if last.lower() != "ε":
        return word
    # Don't drop if there's only one consonant cluster — leaves words too short.
    if second_last.lower() in _GREEK_VOWELS_LOW:
        return word
    return word[:-1]


def _strip_accents_lower(s: str) -> str:
    """Lowercase + strip combining marks for comparison purposes."""
    d = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in d if not unicodedata.combining(ch))


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
