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
  - w  -> ω    (omega — rare in French; mostly affects English loanwords)
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
    "w": "ω", "W": "Ω",
    "x": "χ", "X": "Χ",
    "y": "υ", "Y": "Υ",
    "ÿ": "υ", "Ÿ": "Υ",
    "z": "ζ", "Z": "Ζ",
    "œ": "ε", "Œ": "Ε",
    "æ": "ε", "Æ": "Ε",
}


def transliterate(text: str, hellenize: bool = False,
                  accents: bool = False) -> str:
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

    # 8. Final-sigma: lowercase σ at end-of-word -> ς.
    result = _apply_final_sigma(result)

    # 9. Optional: add proper Ancient Greek accent + breathing marks on words
    # that don't already have them.
    if accents:
        result = _add_greek_accents(result)

    # 10. Acute -> grave on ultima before another word (Ancient Greek rule).
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
# Each rule is (suffix_in_greek_letters, replacement, min_word_length).
# Suffixes are what the French endings become AFTER transliteration. Rules
# apply to a lowercase view of the word; the script preserves the original
# case. Longer suffixes go first so they win over shorter ones.
_HELLENIZE_RULES = [
    # 5-char
    ("τιον", "σιον",   5),    # nation -> νατιον -> νασιον (post-c)
    ("σιον", "σιον",   5),    # already σιον
    ("τριχε","τρις",   6),    # actrice -> ακτριχε -> ακτρις
    ("ισμε", "ισμος",  5),    # optimisme -> οπτιμισμε -> οπτιμισμος
    ("ιστε", "ιστης",  5),    # artiste -> αρτιστε -> αρτιστης
    ("ικε",  "ικος",   5),    # politique -> πολιτικε -> πολιτικος
    ("ιτέ",  "οτης",   5),    # liberté/égalité
    ("ιτε",  "οτης",   5),    # same without accent
    ("ευχ",  "ος",     5),    # heureux -> ἑυρευχ -> ἑυρος
    ("ευσε", "ωσα",    5),    # amoureuse -> αμουρευσε -> αμουρωσα

    # ---- verb-ish endings ----
    # French infinitive -er (aimer, parler, donner) -> -εω (Greek contract verb)
    ("ερ",   "εω",     4),
    # French infinitive -ir (finir, partir) -> -ειν (Greek active infinitive)
    ("ιρ",   "ειν",    4),
    # 3rd person plural -ent (parlent, aiment) -> -ουσι
    ("εντ",  "ουσι",   5),
    # 1st person plural -ons (parlons) -> -ομεν  (sigma medial; rules run pre-final-sigma)
    ("ονσ",  "ομεν",   5),
    # 2nd person plural -ez (parlez) -> -ετε
    ("εζ",   "ετε",    4),

    # 4-char
    ("ευρ",  "ωρ",     4),    # docteur, professeur
    ("εαυ",  "ος",     5),    # bateau -> βατεαυ -> βατος
    ("αυτ",  "ος",     5),    # haut, défaut endings
    ("αυδ",  "ος",     5),    # similar

    # 3-char
    ("ιε",   "ια",     4),    # philosophie -> -ιε -> -ια

    # 2-char silent -e (handled separately below)
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
    for suffix, replacement, min_len in _HELLENIZE_RULES:
        if len(word) < min_len:
            continue
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


# ============================================================================
# Greek accent engine
# ============================================================================
# Adds smooth/rough breathing on vowel-initial words and places acute or
# circumflex accents following the rules in your guide:
#   - acute on any of the last three syllables;
#   - circumflex only on penult or ultima, and only on a long syllable;
#   - the "trochee rule": if a word ends long-short and the accent falls on
#     the penult, that penult accent must be a circumflex;
#   - rule 4: if the ultima is long, the acute can't be antepenult.
# We default to recessive (verb-like) accentuation: as far back as the rules
# allow, since we have no grammatical info to do otherwise.

# Unaccented base vowels (the bare letters before any marks).
_BASE_VOWELS = set("αεηιουω")

# Long vowels (the inherently long ones).
_LONG_BASES   = set("ηω")
_SHORT_BASES  = set("εο")
# α ι υ are ambiguous; treated as short by default (we have no length info).

# Greek diphthongs (always counted as a single long syllable).
_DIPHTHONGS = {
    "αι","ει","οι","υι","αυ","ευ","ου","ηυ","ωυ",
}
# Iota subscripts (ᾳ ῃ ῳ etc.) count as long as well, but we don't generate them.

# Combining marks
COMB_ACUTE       = "\u0301"   # ´  (tonos)
COMB_GRAVE       = "\u0300"   # `  (varia)
COMB_CIRCUMFLEX  = "\u0342"   # ͂  (perispomeni)
COMB_SMOOTH      = "\u0313"   # ᾿  (psili)
COMB_ROUGH       = "\u0314"   # ̔  (dasia)

_ACCENT_COMB = {COMB_ACUTE, COMB_GRAVE, COMB_CIRCUMFLEX}
_BREATHING_COMB = {COMB_SMOOTH, COMB_ROUGH}


def _word_has_accent(word: str) -> bool:
    """True if any character in the word carries an acute, grave, or circumflex."""
    d = unicodedata.normalize("NFD", word)
    return any(c in _ACCENT_COMB for c in d)


def _word_has_breathing(word: str) -> bool:
    """True if any character carries a smooth or rough breathing."""
    d = unicodedata.normalize("NFD", word)
    return any(c in _BREATHING_COMB for c in d)


def _syllabify(word: str) -> list[tuple[int, int]]:
    """Split a word into syllables. Returns a list of (start, end) character
    ranges over the *decomposed* form. Each syllable contains exactly one
    vowel nucleus (a vowel or a diphthong).

    Standard Greek syllabification: consonants between vowels go with the
    FOLLOWING syllable (a single intervocalic consonant always; two or more
    consonants are split mostly at the first one — but for our purposes the
    coarse rule is fine since we only care about which syllable holds the
    nucleus, not the precise consonant boundary).
    """
    d = unicodedata.normalize("NFD", word.lower())
    # Track positions of bare vowels and diphthongs.
    nuclei = []   # list of (start_idx_in_d, length_in_chars_excluding_marks)
    i = 0
    n = len(d)
    while i < n:
        ch = d[i]
        if ch in _BASE_VOWELS:
            # Look ahead for a diphthong. Skip combining marks between.
            j = i + 1
            while j < n and unicodedata.combining(d[j]):
                j += 1
            if j < n and d[j] in _BASE_VOWELS and (ch + d[j]) in _DIPHTHONGS:
                # Make sure the second vowel doesn't itself carry an accent
                # or diaeresis that would split the diphthong.
                k = j + 1
                second_has_accent = False
                while k < n and unicodedata.combining(d[k]):
                    if d[k] in _ACCENT_COMB or d[k] == "\u0308":  # diaeresis
                        second_has_accent = True
                    k += 1
                if not second_has_accent:
                    nuclei.append((i, k))
                    i = k
                    continue
            # Single vowel nucleus; consume any combining marks on it.
            j = i + 1
            while j < n and unicodedata.combining(d[j]):
                j += 1
            nuclei.append((i, j))
            i = j
        else:
            i += 1
    # Build syllable spans by carving the consonants:
    # syllable k owns [prev_end .. nuclei[k].end), except the first owns
    # [0 .. nuclei[0].end).
    syllables = []
    prev_end = 0
    for idx, (n_start, n_end) in enumerate(nuclei):
        if idx == 0:
            syllables.append((0, n_end))
        else:
            # Consonants between previous nucleus and this one: send the
            # last consonant to the current syllable, earlier ones stay
            # with the previous. (Approximation.)
            prev_nuc_end = nuclei[idx - 1][1]
            cluster = list(range(prev_nuc_end, n_start))
            if len(cluster) <= 1:
                # 0 or 1 consonant — goes to current syllable.
                curr_start = prev_nuc_end
            else:
                # 2+ consonants — split: leave one on the previous syllable,
                # the rest go to current. (Real rules are subtler — stop+liquid
                # stays together — but this works for accent purposes.)
                curr_start = prev_nuc_end + 1
            # Adjust the previous syllable's end if we kept some consonants.
            ps, pe = syllables[-1]
            syllables[-1] = (ps, curr_start)
            syllables.append((curr_start, n_end))
    # Stretch the last syllable to absorb trailing consonants.
    if syllables:
        s, e = syllables[-1]
        syllables[-1] = (s, n)
    return syllables


def _syllable_is_long(word_d: str, span: tuple[int, int]) -> bool:
    """A syllable is long if its nucleus is η, ω, or a diphthong.
    α, ι, υ default to short (we have no length info from a transliteration)."""
    s, e = span
    text = word_d[s:e]
    # Find the vowel nucleus
    bases = [c for c in text if c in _BASE_VOWELS]
    if not bases:
        return False
    if len(bases) >= 2:
        # Diphthong
        dipht = bases[0] + bases[1]
        if dipht in _DIPHTHONGS:
            return True
    return bases[0] in _LONG_BASES


def _add_greek_accents(text: str) -> str:
    """Walk through the text word-by-word and add breathings + accents
    on any word that doesn't already have them."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if not _is_word_char(text[i]):
            out.append(text[i])
            i += 1
            continue
        # Collect the word.
        j = i
        while j < n and (_is_word_char(text[j]) or text[j] == CORONIS):
            j += 1
        word = text[i:j]
        out.append(_accent_word(word))
        i = j
    return "".join(out)


def _accent_word(word: str) -> str:
    """Add breathing + accent to a single word, if it doesn't have them already."""
    if len(word) <= 1:
        return word
    d = unicodedata.normalize("NFD", word)

    if _word_has_accent(d):
        return word

    has_breathing = _word_has_breathing(d)

    syllables = _syllabify(word)
    if not syllables:
        return word
    d_lower = d.lower()

    # Plan both insertions BEFORE applying any, so the indices we compute
    # against the original decomposed string stay valid.
    breathing_idx = None
    if not has_breathing:
        first_letter = _first_letter_idx(d)
        if first_letter < len(d_lower) and d_lower[first_letter] in _BASE_VOWELS:
            # Initial diphthong: breathing on the 2nd vowel.
            second_idx = first_letter + 1
            while second_idx < len(d_lower) and unicodedata.combining(d_lower[second_idx]):
                second_idx += 1
            if (second_idx < len(d_lower)
                    and d_lower[second_idx] in _BASE_VOWELS
                    and (d_lower[first_letter] + d_lower[second_idx]) in _DIPHTHONGS):
                breathing_idx = second_idx
            else:
                breathing_idx = first_letter

    accent_idx, accent_mark = _choose_accent(d_lower, syllables)

    # Apply insertions right-to-left so earlier indices remain valid.
    insertions = []
    if breathing_idx is not None:
        insertions.append((breathing_idx, COMB_SMOOTH))
    if accent_idx is not None and accent_mark is not None:
        insertions.append((accent_idx, accent_mark))
    insertions.sort(key=lambda t: t[0], reverse=True)
    for idx, mark in insertions:
        d = _insert_combining(d, idx, mark)

    # Reorder so breathings come before accents on the same base, then NFC.
    d = _reorder_marks(d)
    return unicodedata.normalize("NFC", d)


def _reorder_marks(s: str) -> str:
    """Within each cluster of combining marks on a base, put breathings
    first, then accents. This is the order Unicode's precomposed Greek
    polytonic glyphs expect (e.g. ο + ̔ + ́ -> ὅ)."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        out.append(s[i])
        j = i + 1
        marks = []
        while j < n and unicodedata.combining(s[j]):
            marks.append(s[j])
            j += 1
        if marks:
            breathings = [m for m in marks if m in _BREATHING_COMB]
            accents    = [m for m in marks if m in _ACCENT_COMB]
            others     = [m for m in marks
                          if m not in _BREATHING_COMB and m not in _ACCENT_COMB]
            out.extend(others + breathings + accents)
        i = j
    return "".join(out)


def _first_letter_idx(d: str) -> int:
    """Index of the first actual letter (not a combining mark) in a decomposed string."""
    for idx, ch in enumerate(d):
        if not unicodedata.combining(ch):
            return idx
    return 0


def _insert_combining(d: str, base_idx: int, mark: str) -> str:
    """Insert a combining mark immediately after the base char at base_idx,
    in front of any existing combining marks on that base. (NFC re-ordering
    will sort them properly later.)"""
    return d[: base_idx + 1] + mark + d[base_idx + 1:]


def _choose_accent(d_lower: str, syllables) -> tuple[int | None, str | None]:
    """Apply rules 3-5 from the guide:
       - The default is recessive: as far back as the rules allow.
       - Acute on antepenult only if ultima is short.
       - Penult accent: if the penult is long AND the ultima is short, use
         circumflex (the trochee rule, §5); otherwise acute.
       - For monosyllables: circumflex if the syllable is long, acute otherwise.

       Returns (base_char_index_in_d_lower, combining_mark) or (None, None).
    """
    nsyll = len(syllables)
    if nsyll == 0:
        return None, None

    # Find the index of the FIRST vowel char in each syllable (where the
    # accent mark will attach — for diphthongs, the second vowel by convention).
    def accent_target(span):
        s, e = span
        # Collect indices of base vowels within the syllable.
        vowel_idxs = [k for k in range(s, e) if d_lower[k] in _BASE_VOWELS]
        if not vowel_idxs:
            return None
        if len(vowel_idxs) >= 2:
            # diphthong — accent goes on the SECOND element by Greek convention
            return vowel_idxs[1]
        return vowel_idxs[0]

    if nsyll == 1:
        # Monosyllable: circumflex on long syllables, acute on short.
        target = accent_target(syllables[0])
        if target is None:
            return None, None
        if _syllable_is_long(d_lower, syllables[0]):
            return target, COMB_CIRCUMFLEX
        return target, COMB_ACUTE

    ultima = syllables[-1]
    penult = syllables[-2]
    ultima_long = _syllable_is_long(d_lower, ultima)
    penult_long = _syllable_is_long(d_lower, penult)

    if nsyll >= 3 and not ultima_long:
        # Try antepenult acute (rule 4: only allowed if ultima is short).
        antepenult = syllables[-3]
        target = accent_target(antepenult)
        if target is not None:
            return target, COMB_ACUTE

    # Penult accent. Trochee rule (§5): if penult is long and ultima is short,
    # the penult accent MUST be circumflex.
    target = accent_target(penult)
    if target is not None:
        if penult_long and not ultima_long:
            return target, COMB_CIRCUMFLEX
        return target, COMB_ACUTE

    # Fallback to ultima.
    target = accent_target(ultima)
    if target is None:
        return None, None
    if ultima_long:
        return target, COMB_CIRCUMFLEX
    return target, COMB_ACUTE


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
