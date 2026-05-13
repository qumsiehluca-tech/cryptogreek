"""
Latin -> Greek-script transliterator.

Follows the conventions Hellenistic Greek scribes used when writing Latin
names (Polybius, Plutarch, imperial-era inscriptions). Classical Latin
pronunciation, not Ecclesiastical.

PHONOLOGY
---------
Vowels:
    short a, long ā  -> α
    short e          -> ε
    long ē           -> η
    short i, long ī  -> ι
    short o          -> ο
    long ō           -> ω
    short u, long ū  -> ου
    y                -> υ
Diphthongs:
    ae -> αι       oe -> οι       au -> αυ       eu -> ευ
    ei -> ει       ui -> υι (rare)

Consonants:
    b -> β   c (always /k/) -> κ    d -> δ
    f -> φ   g -> γ                 h -> rough breathing on the next vowel
    j  / consonantal i -> ι          k -> κ                  l -> λ
    m -> μ   n -> ν                 p -> π
    qu -> κυ (kappa-upsilon — period-correct rendering)
    r -> ρ (initial r gets rough breathing: ῥ)
    s -> σ (final ς)
    t -> τ
    v / consonantal u -> β           x -> ξ
    z -> ζ
Digraphs from Greek loanwords:
    ph -> φ    th -> θ    ch -> χ    rh -> ῥ

STRESS / ACCENT
---------------
Classical Latin stress is determined entirely by syllable weight:
    1 syllable        : stress that syllable (rare in practice)
    2 syllables       : stress the penult
    3+ syllables      : if the penult is HEAVY, stress the penult;
                        otherwise stress the antepenult

A syllable is HEAVY if:
    - its vowel is long (ā ē ī ō ū, or a diphthong), OR
    - its short vowel is followed by two or more consonants
      ("position", but watch out for "muta cum liquida" — a stop + l/r
       counts as a single consonant cluster for stress purposes)

Once stress is placed, it becomes a Greek pitch accent. Following the
Greek rules from the rest of this app:
    - long penult, short ultima, stress on penult -> circumflex (trochee §5)
    - otherwise -> acute
    - acute on ultima becomes grave when followed by another word

USAGE
-----
    from latin_to_greek import transliterate_latin
    transliterate_latin("Caesar dixit")        # -> "Καῖσαρ δίξιτ"
    transliterate_latin("philosophia est ars") # -> "φιλοσοφία ἐστ ἄρς"

You can mark long vowels with macrons (ā ē ī ō ū) for accurate stress on
words with light/heavy ambiguity. Without macrons, vowels default to short
and stress is determined by position alone — which is correct for most
words but can be wrong on ones like "amīcus" (heavy penult by length, not
position).
"""
from __future__ import annotations
import re
import unicodedata


# =============================================================================
# Phonology — Latin letters -> Greek letters
# =============================================================================

# Vowels: short and long forms.
# We map them to a Greek vowel and a "length" tag (S=short, L=long).
# Length matters for stress placement, not output (Greek α is the same
# whether it represents short or long Latin a).
VOWELS = {
    "a": ("α", "S"), "ā": ("α", "L"),
    "e": ("ε", "S"), "ē": ("η", "L"),
    "i": ("ι", "S"), "ī": ("ι", "L"),
    "o": ("ο", "S"), "ō": ("ω", "L"),
    "u": ("ου", "S"), "ū": ("ου", "L"),
    "y": ("υ", "S"), "ȳ": ("υ", "L"),
    # Capital forms (we lowercase to look up, but keep originals for capitalization)
}

# Diphthongs — always count as LONG syllables, single Greek output.
DIPHTHONGS = {
    "ae": "αι",
    "oe": "οι",
    "au": "αυ",
    "eu": "ευ",
    "ei": "ει",
    "ui": "υι",
}

# Consonant map.
CONSONANTS = {
    "b": "β",
    "c": "κ",   # classical /k/, always hard
    "d": "δ",
    "f": "φ",
    "g": "γ",
    "j": "ι",   # consonantal i (e.g. "Iulius" / "Julius" -> Ιουλιος)
    "k": "κ",
    "l": "λ",
    "m": "μ",
    "n": "ν",
    "p": "π",
    "r": "ρ",
    "s": "σ",
    "t": "τ",
    "v": "β",   # classical /w/, but Greek scribes wrote it β
    "x": "ξ",
    "z": "ζ",
}

# Greek-loanword digraphs (these come from Greek originals: philosophia, theatrum,
# chorus, rhetor). Maps Latin spelling to a single Greek letter.
DIGRAPHS = [
    ("ph", "φ"),
    ("th", "θ"),
    ("ch", "χ"),
    ("rh", "ρ"),  # rho — initial rh gets rough breathing applied later
    ("qu", "κυ"),
]

# Combining marks
COMB_ACUTE      = "\u0301"
COMB_GRAVE      = "\u0300"
COMB_CIRCUMFLEX = "\u0342"
COMB_SMOOTH     = "\u0313"
COMB_ROUGH      = "\u0314"

CORONIS = "\u1FBD"  # ᾽


# =============================================================================
# Macronization
# =============================================================================
# We add macrons to a word to mark long vowels, then let the stress engine
# place penult-vs-antepenult acute/circumflex accents. Latin vowel length
# comes from several distinct sources, applied in this order:
#
#   STAGE A — Phonological rules (exceptionless):
#     • vowel before another vowel is short          (vocalis ante vocalem)
#     • vowel before gn, nf, ns, nx, nct is long     (Lachmann lengthening)
#     • diphthongs are inherently long               (handled in syllabifier)
#
#   STAGE B — Morphological / derivational suffixes (very reliable):
#     • -tiō / -tiōnis family                       (always long ō)
#     • agent-noun oblique cases -tōris, -tōrēs ... (long ō; -tor nom short)
#     • adjective families -ālis, -ārius, -ōsus,
#       -īnus, -īvus, -ūnus, -ālia, -ārium ...
#     • abstract noun -ūdō / -ūdinis, -tās / -tātis,
#       -tūdō, -tūra, -tūrus (future ptcp)
#     • participles -ātus, -ētus, -ītus  (past ptcp of 1st/2nd/4th conj)
#                   -andus, -endus      (gerundive vowels are short)
#                   -ātor, -ētor, -ītor (-tor of 1st/2nd/4th conj is from long stem)
#     • infinitive endings -āre, -ēre (2nd conj), -īre  (3rd conj -ere is short)
#     • imperfect -ābam/-ēbam/-iēbam, future -ābō/-ēbō
#     • perfect-stem markers -āvī, -ēvī, -īvī before consonant or end
#     • supine -ātum, -ētum, -ītum
#     • generic plural endings -ōrum, -ārum
#     • adverbs -ē (long from 2nd-decl adj), -iter (short)
#
#   STAGE C — Word-final vowel/ending rules (highly reliable):
#     • final -ī, -ō, -ū → long
#     • final -ā after a consonant → ambiguous, but more often long in
#       common forms (1st-decl abl. sg) → leave alone unless we have other info
#     • final -ēs, -ās, -ōs, -ūs → long
#     • final -is, -us, -es, -os, -as, -am, -em, -im, -om, -um → short
#     • final -e after a consonant → short (3rd-decl voc, neut.sg.)
#
#   STAGE D — Exceptions: a deliberately small set of common irregularly-long
#     words that no rule predicts. These are TRUE exceptions: function words
#     whose length is historical (sī, nōn, tū, dē, ē, ā, prō, mē, tē, sē,
#     vōs, nōs), and a handful of nouns with hidden quantity from contraction
#     (rēx, lēx, pāx, vōx, lūx, dux's vowel is short, sōl, etc.).
#
# We apply these as: STAGE D (override) → STAGE A → STAGE B → STAGE C →
# vocalis-ante-vocalem cleanup. Users typing explicit macrons override
# everything.

import re

# True exceptions only — words whose vowel length comes from history, not
# from a productive rule. If a word follows the morphological patterns in
# STAGE B/C, it does NOT belong here.
_EXCEPTIONS = {
    # Monosyllabic function words & particles with inherent long vowels.
    # These are individually irregular — no rule predicts their length.
    "a": "ā", "e": "ē",                   # prepositions ā, ē (before consonant)
    "ab": "ab", "ex": "ex",               # alternative forms (short before vowel)
    "de": "dē", "pro": "prō", "pre": "prē",
    "ne": "nē", "se": "sē", "me": "mē", "te": "tē",
    "ni": "nī",
    "si": "sī", "sic": "sīc",
    "non": "nōn", "num": "num", "nunc": "nunc",
    "tu": "tū", "vos": "vōs", "nos": "nōs",
    "is": "is", "id": "id",               # short — listed to suppress final-i rule
    "in": "in", "ad": "ad", "ob": "ob", "per": "per",
    "et": "et", "ac": "ac", "at": "at",
    "ut": "ut", "an": "an",
    # Disyllabic words with historically short final -o (rare; most -o is long):
    "ego": "ego", "modo": "modo", "immo": "immo", "duo": "duo",
    "octo": "octō",                       # octō IS long
    "ergo": "ergō",
    # Disyllabic words with historically short final -i (rare):
    "tibi": "tibi", "mihi": "mihi", "sibi": "sibi",
    "ibi": "ibi", "ubi": "ubi",
    "nisi": "nisi", "quasi": "quasi",
    "cum": "cum", "tum": "tum", "iam": "iam",
    "hic": "hic", "huc": "hūc", "tunc": "tunc",
    "quis": "quis", "quid": "quid", "qui": "quī", "quae": "quae",
    "quo": "quō", "qua": "quā", "quam": "quam", "quem": "quem",
    "quod": "quod", "cur": "cūr",
    "sed": "sed", "vel": "vel", "aut": "aut",
    # Nouns/adjectives with hidden quantity (long vowel "compressed" before
    # consonant cluster, not deducible from spelling without history):
    "rex": "rēx", "lex": "lēx", "pax": "pāx",
    "lux": "lūx", "vox": "vōx", "nix": "nix",
    "nox": "nox", "dux": "dux",            # nox/dux are SHORT
    "sol": "sōl", "mos": "mōs", "ros": "rōs",
    "frons": "frōns", "mons": "mōns", "fons": "fōns",
    "pons": "pōns", "gens": "gēns",
    # A few common verbs whose principal-part vowel-lengths matter and aren't
    # derivable from spelling (would need to know the conjugation class):
    "sum": "sum", "es": "es", "est": "est",
    "sumus": "sumus", "estis": "estis", "sunt": "sunt",
    "eram": "eram", "erat": "erat", "erant": "erant",
    "ero": "erō", "erit": "erit", "erunt": "erunt",
    "fui": "fuī", "fuit": "fuit",
    "habeo": "habeō",   # 2nd conj — but spelled exactly like 3rd: needs exception
    # Greek loanwords commonly used in Latin:
    "philosophia": "philosophia", "musica": "mūsica",
    # Primitive -inus nouns whose i is SHORT (most -inus is long via the
    # derivational adjective suffix; these are inherited words, not derived):
    "dominus": "dominus", "domini": "dominī", "dominus": "dominus",
    "domino": "dominō", "dominorum": "dominōrum", "dominos": "dominōs",
    "geminus": "geminus", "geminis": "geminīs",
    "terminus": "terminus", "termini": "terminī", "terminos": "terminōs",
    # Other primitive -ena/-una/-ina nouns that escape rules:
    "femina": "fēmina",                  # ē is long but i is short!
}


# ----------------------------------------------------------------------------
# Stage A: phonological rules
# ----------------------------------------------------------------------------

# Vowels (plain) -> their macron form
_MACRON_OF = {"a": "ā", "e": "ē", "i": "ī", "o": "ō", "u": "ū", "y": "ȳ",
              "A": "Ā", "E": "Ē", "I": "Ī", "O": "Ō", "U": "Ū", "Y": "Ȳ"}
_PLAIN_OF  = {v: k for k, v in _MACRON_OF.items()}

_PLAIN_VOWELS  = set("aeiouy")
_MACRON_VOWELS = set("āēīōūȳ")
_ALL_VOWELS    = _PLAIN_VOWELS | _MACRON_VOWELS | {c.upper() for c in _PLAIN_VOWELS} | {c.upper() for c in _MACRON_VOWELS}

# Patterns that always lengthen the preceding vowel (Lachmann + before nasal+fricative).
# Compiled into regex for word-internal use.
_LACHMANN_PATTERNS = [
    # vowel + gn → long vowel (māgnus, sīgnum, dīgnus, rēgnum, lūx...)
    (re.compile(r"([aeiou])(gn)", re.IGNORECASE), True),
    # vowel + nf → long (īnferus, cōnferre)
    (re.compile(r"([aeiou])(nf)", re.IGNORECASE), True),
    # vowel + ns → long (mēnsa, cōnsul, īnsula, pēnsum)
    (re.compile(r"([aeiou])(ns)", re.IGNORECASE), True),
    # vowel + nct → long (sānctus, dēfunctus, iūnctus)
    (re.compile(r"([aeiou])(nct)", re.IGNORECASE), True),
    # vowel + nx → long (cōniūnx)
    (re.compile(r"([aeiou])(nx)", re.IGNORECASE), True),
]

def _apply_lachmann(word: str) -> str:
    """Apply the lengthening-before-cluster rules (vowel + gn/nf/ns/nx/nct)."""
    out = word
    for pattern, _ in _LACHMANN_PATTERNS:
        out = pattern.sub(lambda m: _MACRON_OF.get(m.group(1), m.group(1)) + m.group(2), out)
    return out


def _vocalis_ante_vocalem(word: str) -> str:
    """Latin: a vowel directly before another vowel is short. Strip any
    macron on a vowel that's followed by another vowel (not in a diphthong)."""
    out = list(word)
    n = len(out)
    DIPHTHONG_STARTS = {("a","e"),("o","e"),("a","u"),("e","u"),("e","i"),("u","i")}
    for i, ch in enumerate(out):
        if ch in _MACRON_VOWELS or ch in {"Ā","Ē","Ī","Ō","Ū","Ȳ"}:
            if i + 1 < n:
                base = _PLAIN_OF.get(ch, ch)
                nxt  = out[i + 1]
                # Protect diphthongs: if (base.lower(), nxt.lower()) is one,
                # don't strip.
                if (base.lower(), nxt.lower()) in DIPHTHONG_STARTS:
                    continue
                if nxt.lower() in _PLAIN_VOWELS:
                    out[i] = base
    return "".join(out)


# ----------------------------------------------------------------------------
# Stage B & C: morphological + final-syllable suffix patterns
# ----------------------------------------------------------------------------

# Each rule is (regex_on_unmacronized_lowercase, replacement_with_macrons).
# Earlier rules win (longest/most-specific first). We anchor with $ for
# word-end matching where applicable.
#
# Replacement uses backreferences \1, \2 etc. to keep stems intact.

_SUFFIX_RULES = [
    # ---- DERIVATIONAL ----
    # -tiō / -tiōn- (always long ō): nation, ratio, oratio, etc.
    # Cover the whole declensional paradigm in one regex.
    (re.compile(r"(t|s)ion(es|em|is|ibus|i|e|um)$", re.IGNORECASE),
     lambda m: m.group(1) + "iōn" + m.group(2).replace("e","ē").replace("E","Ē")
        if m.group(2) in {"es","em","ibus","e"}
        else m.group(1) + "iōn" + m.group(2)),
    (re.compile(r"(t|s)io$", re.IGNORECASE),
     lambda m: m.group(1) + "iō"),

    # Agent-noun oblique cases -tōris, -tōrēs, -tōrem etc.
    # Nom -tor stays short.
    (re.compile(r"toribus$", re.IGNORECASE), "tōribus"),
    (re.compile(r"torum$",   re.IGNORECASE), "tōrum"),
    (re.compile(r"tores$",   re.IGNORECASE), "tōrēs"),
    (re.compile(r"torem$",   re.IGNORECASE), "tōrem"),
    (re.compile(r"toris$",   re.IGNORECASE), "tōris"),
    (re.compile(r"tori$",    re.IGNORECASE), "tōrī"),
    (re.compile(r"tore$",    re.IGNORECASE), "tōre"),

    # Abstract noun -tās / -tātis / -tātēs (libertas, civitas, veritas...)
    (re.compile(r"tatibus$", re.IGNORECASE), "tātibus"),
    (re.compile(r"tatum$",   re.IGNORECASE), "tātum"),
    (re.compile(r"tates$",   re.IGNORECASE), "tātēs"),
    (re.compile(r"tatem$",   re.IGNORECASE), "tātem"),
    (re.compile(r"tatis$",   re.IGNORECASE), "tātis"),
    (re.compile(r"tate$",    re.IGNORECASE), "tāte"),
    (re.compile(r"tas$",     re.IGNORECASE), "tās"),
    (re.compile(r"tati$",    re.IGNORECASE), "tātī"),

    # Abstract -ūdō / -ūdin- (multitūdō, magnitūdō, fortitūdō)
    (re.compile(r"udinibus$", re.IGNORECASE), "ūdinibus"),
    (re.compile(r"udinum$",   re.IGNORECASE), "ūdinum"),
    (re.compile(r"udines$",   re.IGNORECASE), "ūdinēs"),
    (re.compile(r"udinem$",   re.IGNORECASE), "ūdinem"),
    (re.compile(r"udinis$",   re.IGNORECASE), "ūdinis"),
    (re.compile(r"udo$",      re.IGNORECASE), "ūdō"),

    # -tūra (natura, cultura, scriptura) — always long ū
    (re.compile(r"turarum$", re.IGNORECASE), "tūrārum"),
    (re.compile(r"turae$",   re.IGNORECASE), "tūrae"),
    (re.compile(r"turas$",   re.IGNORECASE), "tūrās"),
    (re.compile(r"turam$",   re.IGNORECASE), "tūram"),
    (re.compile(r"tura$",    re.IGNORECASE), "tūra"),
    (re.compile(r"turis$",   re.IGNORECASE), "tūrīs"),

    # -tūrus, -tūra, -tūrum (future active participle)
    (re.compile(r"turus$",   re.IGNORECASE), "tūrus"),
    (re.compile(r"turum$",   re.IGNORECASE), "tūrum"),
    (re.compile(r"turi$",    re.IGNORECASE), "tūrī"),
    (re.compile(r"turo$",    re.IGNORECASE), "tūrō"),

    # -ālis adjective family (mortalis, naturalis, animalis)
    (re.compile(r"alibus$", re.IGNORECASE), "ālibus"),
    (re.compile(r"alium$",  re.IGNORECASE), "ālium"),
    (re.compile(r"alia$",   re.IGNORECASE), "ālia"),
    (re.compile(r"ales$",   re.IGNORECASE), "ālēs"),
    (re.compile(r"alem$",   re.IGNORECASE), "ālem"),
    (re.compile(r"alis$",   re.IGNORECASE), "ālis"),
    (re.compile(r"ali$",    re.IGNORECASE), "ālī"),

    # -ārius / -ārium / -āria  (military / occupation nouns)
    (re.compile(r"ariorum$", re.IGNORECASE), "āriōrum"),
    (re.compile(r"ariarum$", re.IGNORECASE), "āriārum"),
    (re.compile(r"arius$",   re.IGNORECASE), "ārius"),
    (re.compile(r"aria$",    re.IGNORECASE), "āria"),
    (re.compile(r"arium$",   re.IGNORECASE), "ārium"),
    (re.compile(r"ariae$",   re.IGNORECASE), "āriae"),
    (re.compile(r"ariis$",   re.IGNORECASE), "āriīs"),

    # -ōsus / -ōsa / -ōsum (gloriosus, famosus, periculosus)
    (re.compile(r"osorum$", re.IGNORECASE), "ōsōrum"),
    (re.compile(r"osarum$", re.IGNORECASE), "ōsārum"),
    (re.compile(r"osus$",   re.IGNORECASE), "ōsus"),
    (re.compile(r"osa$",    re.IGNORECASE), "ōsa"),
    (re.compile(r"osum$",   re.IGNORECASE), "ōsum"),
    (re.compile(r"osi$",    re.IGNORECASE), "ōsī"),
    (re.compile(r"osae$",   re.IGNORECASE), "ōsae"),

    # -ānus / -ēnus / -īnus / -ōnus / -ūnus family (Rōmānus, Latīnus,
    # commūnus, dīvīnus, etc.). The vowel before -n-us is always long.
    # Require a consonant before the vowel so we don't match super-short
    # words like 'unus' (handled as exception if needed).
    (re.compile(r"([bcdfghjklmnpqrstvxz])anus$", re.IGNORECASE), lambda m: m.group(1) + "ānus"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ana$",  re.IGNORECASE), lambda m: m.group(1) + "āna"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anum$", re.IGNORECASE), lambda m: m.group(1) + "ānum"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anae$", re.IGNORECASE), lambda m: m.group(1) + "ānae"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anam$", re.IGNORECASE), lambda m: m.group(1) + "ānam"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ani$",  re.IGNORECASE), lambda m: m.group(1) + "ānī"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anos$", re.IGNORECASE), lambda m: m.group(1) + "ānōs"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anas$", re.IGNORECASE), lambda m: m.group(1) + "ānās"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anorum$", re.IGNORECASE), lambda m: m.group(1) + "ānōrum"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])anarum$", re.IGNORECASE), lambda m: m.group(1) + "ānārum"),

    (re.compile(r"([bcdfghjklmnpqrstvxz])enus$", re.IGNORECASE), lambda m: m.group(1) + "ēnus"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ena$",  re.IGNORECASE), lambda m: m.group(1) + "ēna"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])enum$", re.IGNORECASE), lambda m: m.group(1) + "ēnum"),

    (re.compile(r"([bcdfghjklmnpqrstvxz])inus$", re.IGNORECASE), lambda m: m.group(1) + "īnus"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ina$",  re.IGNORECASE), lambda m: m.group(1) + "īna"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])inum$", re.IGNORECASE), lambda m: m.group(1) + "īnum"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])inae$", re.IGNORECASE), lambda m: m.group(1) + "īnae"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])inam$", re.IGNORECASE), lambda m: m.group(1) + "īnam"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ini$",  re.IGNORECASE), lambda m: m.group(1) + "īnī"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])inos$", re.IGNORECASE), lambda m: m.group(1) + "īnōs"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])inas$", re.IGNORECASE), lambda m: m.group(1) + "īnās"),

    (re.compile(r"([bcdfghjklmnpqrstvxz])onus$", re.IGNORECASE), lambda m: m.group(1) + "ōnus"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])ona$",  re.IGNORECASE), lambda m: m.group(1) + "ōna"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])onum$", re.IGNORECASE), lambda m: m.group(1) + "ōnum"),

    (re.compile(r"([bcdfghjklmnpqrstvxz])unus$", re.IGNORECASE), lambda m: m.group(1) + "ūnus"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])una$",  re.IGNORECASE), lambda m: m.group(1) + "ūna"),
    (re.compile(r"([bcdfghjklmnpqrstvxz])unum$", re.IGNORECASE), lambda m: m.group(1) + "ūnum"),

    # -īvus (captīvus, nātīvus, festīvus)
    (re.compile(r"ivus$", re.IGNORECASE), "īvus"),
    (re.compile(r"iva$",  re.IGNORECASE), "īva"),
    (re.compile(r"ivum$", re.IGNORECASE), "īvum"),

    # ---- VERB STEMS ----
    # 1st conjugation: -āre infinitive, -āv- perfect stem, -āt- supine/ptcp
    (re.compile(r"averunt$", re.IGNORECASE), "āvērunt"),
    (re.compile(r"avere$",   re.IGNORECASE), "āvēre"),
    (re.compile(r"avisti$",  re.IGNORECASE), "āvistī"),
    (re.compile(r"avistis$", re.IGNORECASE), "āvistis"),
    (re.compile(r"avimus$",  re.IGNORECASE), "āvimus"),
    (re.compile(r"averit$",  re.IGNORECASE), "āverit"),
    (re.compile(r"avero$",   re.IGNORECASE), "āverō"),
    (re.compile(r"avissem$", re.IGNORECASE), "āvissem"),
    (re.compile(r"avi$",     re.IGNORECASE), "āvī"),
    (re.compile(r"avit$",    re.IGNORECASE), "āvit"),
    (re.compile(r"are$",     re.IGNORECASE), "āre"),
    (re.compile(r"abat$",    re.IGNORECASE), "ābat"),
    (re.compile(r"abant$",   re.IGNORECASE), "ābant"),
    (re.compile(r"abam$",    re.IGNORECASE), "ābam"),
    (re.compile(r"abas$",    re.IGNORECASE), "ābās"),
    (re.compile(r"abamus$",  re.IGNORECASE), "ābāmus"),
    (re.compile(r"abatis$",  re.IGNORECASE), "ābātis"),
    (re.compile(r"abo$",     re.IGNORECASE), "ābō"),
    (re.compile(r"abis$",    re.IGNORECASE), "ābis"),
    (re.compile(r"abit$",    re.IGNORECASE), "ābit"),
    (re.compile(r"abimus$",  re.IGNORECASE), "ābimus"),
    (re.compile(r"abitis$",  re.IGNORECASE), "ābitis"),
    (re.compile(r"abunt$",   re.IGNORECASE), "ābunt"),
    (re.compile(r"atum$",    re.IGNORECASE), "ātum"),
    (re.compile(r"atus$",    re.IGNORECASE), "ātus"),
    (re.compile(r"ata$",     re.IGNORECASE), "āta"),
    (re.compile(r"ati$",     re.IGNORECASE), "ātī"),
    (re.compile(r"atae$",    re.IGNORECASE), "ātae"),
    # 1st conj 1sg/2sg/etc present — but only when stem is recognizably
    # multi-syllable (avoid matching -as on amās vs other -as endings)
    # We rely on the final-VC rule below for -ās generic.

    # 4th conjugation: -īre, -īvī, -ītum
    (re.compile(r"iverunt$", re.IGNORECASE), "īvērunt"),
    (re.compile(r"ivimus$",  re.IGNORECASE), "īvimus"),
    (re.compile(r"ivisti$",  re.IGNORECASE), "īvistī"),
    (re.compile(r"ivit$",    re.IGNORECASE), "īvit"),
    (re.compile(r"ivi$",     re.IGNORECASE), "īvī"),
    (re.compile(r"ire$",     re.IGNORECASE), "īre"),
    (re.compile(r"itum$",    re.IGNORECASE), "ītum"),
    (re.compile(r"itus$",    re.IGNORECASE), "ītus"),
    (re.compile(r"ita$",     re.IGNORECASE), "īta"),
    (re.compile(r"iebat$",   re.IGNORECASE), "iēbat"),
    (re.compile(r"iebam$",   re.IGNORECASE), "iēbam"),

    # 2nd conjugation: -ēre, -uī, -itum (the only macron is on the -ēre inf)
    # Hard to disambiguate from 3rd conj -ere (short e). Skip the inf
    # unless explicitly typed.

    # ---- PLURAL ENDINGS ----
    # gen.pl long: -ōrum, -ārum
    (re.compile(r"orum$", re.IGNORECASE), "ōrum"),
    (re.compile(r"arum$", re.IGNORECASE), "ārum"),
    # dat/abl.pl long: -īs (only after consonants to avoid breaking -uis etc.)
    # Just handle common case -iīs / -ibus differently from -is.
    (re.compile(r"abus$", re.IGNORECASE), "ābus"),

    # ---- WORD-FINAL SINGLE-VOWEL+CONSONANT ----
    # Reliable long endings (these come from 1st/3rd-decl plurals & verbs)
    (re.compile(r"([bcdfgklmnprstvxz])as$", re.IGNORECASE),
     lambda m: m.group(1) + "ās"),
    (re.compile(r"([bcdfgklmnprstvxz])os$", re.IGNORECASE),
     lambda m: m.group(1) + "ōs"),
    (re.compile(r"([bcdfgklmnprstvxz])es$", re.IGNORECASE),
     lambda m: m.group(1) + "ēs"),

    # ---- WORD-FINAL BARE VOWELS ----
    # Word-final -ō (1sg present, dat/abl.sg, adverbs) → long.
    # Allow after vowel too (audi-ō, gaud-e-ō) — vocalis ante vocalem applies
    # to the preceding vowel but the final -ō itself stays long.
    (re.compile(r"o$", re.IGNORECASE), "ō"),
    # Word-final -ī (nom.pl, gen.sg, perfect 1sg, dat.sg) → long
    (re.compile(r"i$", re.IGNORECASE), "ī"),
    # Word-final -ū (4th decl) → long
    (re.compile(r"u$", re.IGNORECASE), "ū"),
]


def _has_macron(s: str) -> bool:
    return any(ch in "āēīōūȳĀĒĪŌŪȲ" for ch in s)


def _macronize(word: str) -> str:
    """Add macrons to a Latin word using exception list + morphological
    rules + phonological rules. User-typed macrons override everything."""
    if not word:
        return word
    if _has_macron(word):
        return word

    was_capital = word[:1].isupper()
    lower = word.lower()

    # STAGE D: exceptions (only true irregulars)
    if lower in _EXCEPTIONS:
        result = _EXCEPTIONS[lower]
    else:
        # STAGE B/C: try each suffix rule; first match wins.
        result = lower
        for pattern, replacement in _SUFFIX_RULES:
            new_result, n = pattern.subn(replacement, result, count=1)
            if n:
                result = new_result
                break

    # STAGE A: phonological rules apply to whatever we have.
    result = _apply_lachmann(result)
    result = _vocalis_ante_vocalem(result)

    if was_capital:
        result = result[:1].upper() + result[1:]
    return result




# =============================================================================
# Syllabification (adapted from your script, simplified for stress purposes)
# =============================================================================

_VOWEL_CHARS = set("aeiouyāēīōūȳAEIOUYĀĒĪŌŪȲ")
_BASE_VOWEL_LOWER = set("aeiouy")  # for looking up in VOWELS

def _lower_word(word: str) -> str:
    return word.lower()


def _split_latin_syllables(word: str) -> list[dict]:
    """Split a Latin word into syllables. Returns a list of dicts:
        {
          'text':   the syllable's letters (lowercase),
          'nucleus': the vowel/diphthong of the syllable,
          'long_by_nature':   True if its nucleus is long (long vowel or diphthong),
          'long_by_position': True if a short vowel is followed by 2+ consonants
                              (cluster spans into the next syllable),
        }

    The standard rule for Latin syllabification, used here:
      - A single consonant between vowels goes with the FOLLOWING vowel.
      - Two consonants split between syllables, EXCEPT a stop + liquid
        cluster (muta cum liquida: pl, pr, bl, br, tl, tr, dl, dr, cl, cr,
        gl, gr, fl, fr) which both go with the following syllable in
        classical Latin pronunciation.
      - Three+ consonants: first stays with the previous syllable, the rest
        go with the next (approximation).
      - qu, ph, th, ch, rh are single consonants for syllable purposes.

    Length:
      - long_by_nature: macron-marked vowel OR diphthong
      - long_by_position: short-vowel syllable whose nucleus is followed by
        2+ consonants (counted across the syllable boundary). Stop+liquid
        does NOT make position.

    """
    w = _lower_word(word)

    # Step 1: tokenize into a sequence of "phonemes" — vowel/diphthong nuclei
    # and consonant clusters. Each token is (text, kind, length_tag).
    # kind = 'V' (vowel/diphthong) or 'C' (consonant or cluster element).
    tokens = []
    i = 0
    n = len(w)
    while i < n:
        ch = w[i]
        # Check 2-char digraphs that count as single consonants for syllable
        # purposes: ph, th, ch, rh, qu.
        two = w[i:i+2]
        if two in {"ph", "th", "ch", "rh", "qu"}:
            tokens.append((two, "C"))
            i += 2
            continue
        # Diphthong?
        if two in DIPHTHONGS:
            tokens.append((two, "V"))
            i += 2
            continue
        if ch in _BASE_VOWEL_LOWER or ch in {"ā","ē","ī","ō","ū","ȳ"}:
            tokens.append((ch, "V"))
            i += 1
            continue
        # Consonant.
        tokens.append((ch, "C"))
        i += 1

    if not tokens:
        return []

    # Step 2: walk through, building syllables. Each syllable contains
    # exactly one V token (its nucleus) plus surrounding consonants.
    # We'll first find all the V positions, then divvy up the C tokens.
    v_positions = [idx for idx, (_, k) in enumerate(tokens) if k == "V"]
    if not v_positions:
        return []   # no vowels -> not a syllabifiable word

    syllables = []
    # For each vowel, decide where the cluster between it and the previous
    # vowel splits.
    for vi, v_idx in enumerate(v_positions):
        if vi == 0:
            syl_start = 0
        else:
            prev_v = v_positions[vi - 1]
            cluster = tokens[prev_v + 1 : v_idx]   # list of (text, 'C')
            nc = len(cluster)
            if nc == 0:
                syl_start = prev_v + 1
            elif nc == 1:
                syl_start = prev_v + 1
            elif nc == 2:
                c1 = cluster[0][0]
                c2 = cluster[1][0]
                if _is_muta_cum_liquida(c1, c2):
                    # Both go with the following syllable.
                    syl_start = prev_v + 1
                else:
                    # Split: first stays with previous, second goes with current.
                    syl_start = prev_v + 2
            else:
                # 3+ consonants: first stays with previous, rest with current.
                # Refinement: if the LAST two form muta cum liquida, only
                # those two go with the next syllable; everything before
                # stays with the previous. This handles e.g. -mpl-, -str-.
                if nc >= 2 and _is_muta_cum_liquida(cluster[-2][0], cluster[-1][0]):
                    syl_start = prev_v + 1 + (nc - 2)
                else:
                    syl_start = prev_v + 1 + (nc - 1)

        # End: up to and including v_idx; the syllable absorbs all trailing
        # consonants only on the last syllable.
        if vi == len(v_positions) - 1:
            syl_end = len(tokens)
        else:
            # End where the next syllable starts — figured out next iteration.
            # Tentatively end at v_idx + 1; we'll patch after.
            syl_end = v_idx + 1

        syllables.append({"start": syl_start, "end": syl_end, "v_idx": v_idx})

    # Step 3: patch syllable ends so each ends right where the next begins.
    for i in range(len(syllables) - 1):
        syllables[i]["end"] = syllables[i + 1]["start"]

    # Step 4: build the syllable records.
    result = []
    for syl in syllables:
        syl_tokens = tokens[syl["start"] : syl["end"]]
        text = "".join(t[0] for t in syl_tokens)
        v_token = tokens[syl["v_idx"]][0]
        # Determine long-by-nature: macron-marked vowel or diphthong.
        if v_token in DIPHTHONGS:
            long_by_nature = True
        elif v_token in {"ā","ē","ī","ō","ū","ȳ"}:
            long_by_nature = True
        else:
            long_by_nature = False
        # Determine long-by-position: count consonants between this syllable's
        # vowel and the NEXT syllable's vowel. (For the last syllable, there's
        # no following vowel, so position doesn't apply — final syllable
        # weight matters only for the trochee rule, where we care about
        # nature.)
        result.append({
            "text": text,
            "nucleus": v_token,
            "long_by_nature": long_by_nature,
            "long_by_position": False,   # filled in below
        })

    # Now compute long_by_position by looking at consonant counts.
    for i in range(len(syllables) - 1):
        # Count consonant tokens between this V and next V.
        v_here = syllables[i]["v_idx"]
        v_next = syllables[i + 1]["v_idx"]
        cluster = tokens[v_here + 1 : v_next]
        # Stop + liquid does NOT make position (count it as 1 effectively).
        if len(cluster) == 2 and _is_muta_cum_liquida(cluster[0][0], cluster[1][0]):
            n_effective = 1
        else:
            n_effective = len(cluster)
        # Also: x (=ks) and z (=dz) count as double consonants by themselves.
        for tok in cluster:
            if tok[0] in {"x", "z"}:
                n_effective += 1
        if n_effective >= 2:
            result[i]["long_by_position"] = True

    return result


_MUTA = set("pbtdcgkqf")
_LIQUIDA = set("lr")

def _is_muta_cum_liquida(c1: str, c2: str) -> bool:
    """True for stop + l/r combinations that don't make position.
    Handles single-char muta only (qu, ph etc. don't combine with l/r as
    a single cluster here — they're already 2 chars."""
    return c1 in _MUTA and c2 in _LIQUIDA


# =============================================================================
# Latin -> Greek letter-by-letter mapping
# =============================================================================

def _strip_macrons(s: str) -> str:
    """Convert macron-marked vowels to plain ones (for matching in maps)."""
    return (s.replace("ā", "a").replace("ē", "e").replace("ī", "i")
             .replace("ō", "o").replace("ū", "u").replace("ȳ", "y")
             .replace("Ā", "A").replace("Ē", "E").replace("Ī", "I")
             .replace("Ō", "O").replace("Ū", "U").replace("Ȳ", "Y"))


def _greek_for_vowel(v: str, capital: bool) -> str:
    """Greek letter(s) for a Latin vowel/diphthong, respecting capitalization."""
    lower = v.lower()
    if lower in DIPHTHONGS:
        g = DIPHTHONGS[lower]
    elif lower in VOWELS:
        g, _ = VOWELS[lower]
    else:
        return v  # passthrough
    if capital:
        return g[0].upper() + g[1:]
    return g


def _greek_for_consonant(c: str, capital: bool) -> str:
    lower = c.lower()
    if len(lower) == 2 and lower in {"ph", "th", "ch", "rh", "qu"}:
        for pat, rep in DIGRAPHS:
            if pat == lower:
                if capital:
                    return rep[0].upper() + rep[1:]
                return rep
    if lower in CONSONANTS:
        g = CONSONANTS[lower]
        if capital:
            return g.upper()
        return g
    return c


def _transliterate_word(word: str) -> tuple[str, list[dict]]:
    """Transliterate a single Latin word to Greek letters and return
    BOTH the Greek text and the syllable analysis (so the caller can place
    the stress accent).

    Returns (greek_text, syllables) where syllables is the list from
    _split_latin_syllables (still in Latin form, but we map syllable->Greek
    via character indexing of the produced Greek text).
    """
    syllables = _split_latin_syllables(word)
    if not syllables:
        return _passthrough(word), []

    w = _lower_word(word)

    # Tokenize again, identical to syllabifier, so we can produce Greek
    # for each token in order.
    tokens = []
    i = 0
    n = len(w)
    while i < n:
        two = w[i:i+2]
        if two in {"ph", "th", "ch", "rh", "qu"}:
            tokens.append((two, "C", i))
            i += 2
            continue
        if two in DIPHTHONGS:
            tokens.append((two, "V", i))
            i += 2
            continue
        ch = w[i]
        if ch in _BASE_VOWEL_LOWER or ch in {"ā","ē","ī","ō","ū","ȳ"}:
            tokens.append((ch, "V", i))
            i += 1
            continue
        tokens.append((ch, "C", i))
        i += 1

    # Special handling: drop 'h', let it become rough breathing on the
    # following vowel instead. We do that by skipping the h token and
    # marking the next V token as carrying rough breathing.
    out = []
    rough_pending = False     # set True after we see h
    # Track per-Greek-char syllable association so we can map stress later.
    greek_chars = []
    char_syllable = []        # syllable index for each char in `greek_chars`
    char_is_vowel = []        # True if that char is a vowel
    char_breathing = []       # smooth / rough / None pending (combining)

    # Find each token's syllable index by walking syllable start positions
    # in Latin-token terms.
    # syllables came from _split_latin_syllables but it uses local indices;
    # we need to recompute syllable assignment by token index.
    syl_for_token = _assign_token_to_syllable(tokens, syllables)

    # The first character of the word — for capitalization.
    capital_word = word[:1].isupper()

    # Initial rho gets rough breathing (Greek convention).
    initial_consonant_rho = (tokens and tokens[0][0] in {"r", "rh"})

    for ti, (tok, kind, _src) in enumerate(tokens):
        is_word_initial_char = (len(greek_chars) == 0)
        # Should this character be uppercase? Only the first emitted char,
        # if the source word was capitalized.
        capital = capital_word and is_word_initial_char

        if kind == "C":
            if tok == "h":
                # h is dropped; mark rough breathing for the next vowel.
                rough_pending = True
                continue
            g = _greek_for_consonant(tok, capital)
            # Initial rh → ῥ (rough breathing on rho).
            if is_word_initial_char and tok == "rh":
                # g currently is "ρ" — we need to add rough breathing.
                for ch in g:
                    greek_chars.append(ch)
                    char_syllable.append(syl_for_token[ti])
                    char_is_vowel.append(False)
                    char_breathing.append(COMB_ROUGH)
                continue
            # Initial r → ῥ
            if is_word_initial_char and tok == "r":
                greek_chars.append(g)
                char_syllable.append(syl_for_token[ti])
                char_is_vowel.append(False)
                char_breathing.append(COMB_ROUGH)
                continue
            # qu → κυ: the upsilon is the syllable nucleus visually, BUT
            # in our syllable model qu is part of the consonant cluster.
            # We want the next actual vowel to carry the stress mark.
            for ch in g:
                greek_chars.append(ch)
                char_syllable.append(syl_for_token[ti])
                # Mark the upsilon of κυ as a non-nucleus vowel.
                char_is_vowel.append(False)
                char_breathing.append(None)
            continue

        # Vowel token.
        g = _greek_for_vowel(tok, capital)
        # If word starts with a vowel and we haven't already marked
        # rough breathing from an h, add a smooth breathing on the
        # first emitted vowel.
        breathing = None
        if rough_pending:
            breathing = COMB_ROUGH
            rough_pending = False
        elif is_word_initial_char:
            breathing = COMB_SMOOTH

        if len(g) == 1:
            greek_chars.append(g)
            char_syllable.append(syl_for_token[ti])
            char_is_vowel.append(True)
            char_breathing.append(breathing)
        else:
            # Diphthong (2 chars). Breathing goes on the second vowel per
            # Greek convention.
            for ci, ch in enumerate(g):
                greek_chars.append(ch)
                char_syllable.append(syl_for_token[ti])
                char_is_vowel.append(True)
                if ci == len(g) - 1:   # last char of diphthong
                    char_breathing.append(breathing)
                else:
                    char_breathing.append(None)

    # Compute stress position (which syllable carries the accent).
    stress_idx = _latin_stress_syllable(syllables)

    # Choose the accent character (acute or circumflex).
    accent_mark = _latin_accent_mark(syllables, stress_idx)

    # Find which Greek character to put the accent on:
    # - the syllable's NUCLEUS vowel (the last vowel-tagged char in that syllable)
    accent_target_char_idx = None
    if stress_idx is not None and accent_mark is not None:
        for ci in range(len(greek_chars) - 1, -1, -1):
            if char_syllable[ci] == stress_idx and char_is_vowel[ci]:
                accent_target_char_idx = ci
                break

    # Now assemble the final string with breathings and accent in NFD form.
    parts = []
    for i, ch in enumerate(greek_chars):
        parts.append(ch)
        # Combining marks: any per-char breathing, then accent if this is the
        # stressed char. Order: breathing(s) FIRST, then accent — so
        # precomposed Unicode glyphs (ἄ, ὅ, etc.) compose under NFC.
        marks = []
        if char_breathing[i] is not None:
            marks.append(char_breathing[i])
        if i == accent_target_char_idx and accent_mark is not None:
            marks.append(accent_mark)
        parts.extend(marks)

    result = "".join(parts)
    # NFC compose into precomposed polytonic glyphs.
    result = unicodedata.normalize("NFC", result)

    # Final sigma at end of word.
    result = _final_sigma(result)

    return result, syllables


def _assign_token_to_syllable(tokens, syllables) -> list[int]:
    """For each token index, which syllable does it belong to?"""
    out = [0] * len(tokens)
    # syllables don't carry token indices in their result form; reconstruct
    # by replaying the split logic — easiest is to rebuild from the syllable
    # *text* by walking tokens.
    syl_strs = [syl["text"] for syl in syllables]
    # Try to match each consecutive run of tokens to syllable boundaries by
    # length of concatenated texts.
    ti = 0
    for si, target in enumerate(syl_strs):
        # Accumulate tokens until we've consumed `len(target)` letters.
        consumed = 0
        while ti < len(tokens) and consumed < len(target):
            consumed += len(tokens[ti][0])
            out[ti] = si
            ti += 1
    # Any leftover tokens (shouldn't happen) go to last syllable.
    while ti < len(tokens):
        out[ti] = len(syl_strs) - 1
        ti += 1
    return out


def _latin_stress_syllable(syllables) -> int | None:
    """Return the index (0-based) of the syllable that carries the stress,
    following classical Latin stress rules."""
    n = len(syllables)
    if n == 0:
        return None
    if n == 1:
        return 0
    if n == 2:
        return 0    # penult on a 2-syllable word = the first syllable
    # n >= 3: look at penult (index n-2).
    penult = syllables[-2]
    if penult["long_by_nature"] or penult["long_by_position"]:
        return n - 2
    return n - 3


def _latin_accent_mark(syllables, stress_idx) -> str | None:
    """Choose acute vs circumflex for the stressed syllable, following the
    Greek rules used elsewhere in the app.
      - circumflex needs a long-by-nature syllable
      - trochee rule (§5): if stress on penult, penult is long (by nature),
        and ultima is short, then circumflex
      - otherwise acute
    """
    if stress_idx is None:
        return None
    n = len(syllables)
    s = syllables[stress_idx]

    # Monosyllable: circumflex if long-by-nature; acute otherwise.
    if n == 1:
        return COMB_CIRCUMFLEX if s["long_by_nature"] else COMB_ACUTE

    # If stress is on the penult (n-2), check the trochee rule.
    if stress_idx == n - 2:
        ultima = syllables[-1]
        ultima_long_nature = ultima["long_by_nature"]
        if s["long_by_nature"] and not ultima_long_nature:
            return COMB_CIRCUMFLEX
        return COMB_ACUTE

    # Stress on ultima or antepenult → always acute (graves only on ultima
    # and only when followed by another word; that pass runs later).
    return COMB_ACUTE


# =============================================================================
# Coronis, final-sigma, grave-rule passes (mirroring the French side)
# =============================================================================

_APOSTROPHES = {"'", "\u2019", "\u2018", "\u02BC"}

def _is_word_char(ch: str) -> bool:
    if not ch:
        return False
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat.startswith("M")


def _final_sigma(word: str) -> str:
    """σ at the absolute end of a word -> ς."""
    if not word:
        return word
    # Only the very last char, since we operate on one word at a time.
    if word.endswith("σ"):
        return word[:-1] + "ς"
    return word


_ACUTE_TO_GRAVE = {
    "ά":"ὰ","Ά":"Ὰ","έ":"ὲ","Έ":"Ὲ","ή":"ὴ","Ή":"Ὴ","ί":"ὶ","Ί":"Ὶ",
    "ό":"ὸ","Ό":"Ὸ","ύ":"ὺ","Ύ":"Ὺ","ώ":"ὼ","Ώ":"Ὼ",
    "ἄ":"ἂ","ἅ":"ἃ","Ἄ":"Ἂ","Ἅ":"Ἃ",
    "ἔ":"ἒ","ἕ":"ἓ","Ἔ":"Ἒ","Ἕ":"Ἓ",
    "ἤ":"ἢ","ἥ":"ἣ","Ἤ":"Ἢ","Ἥ":"Ἣ",
    "ἴ":"ἲ","ἵ":"ἳ","Ἴ":"Ἲ","Ἵ":"Ἳ",
    "ὄ":"ὂ","ὅ":"ὃ","Ὄ":"Ὂ","Ὅ":"Ὃ",
    "ὔ":"ὒ","ὕ":"ὓ","Ὕ":"Ὓ",
    "ὤ":"ὢ","ὥ":"ὣ","Ὤ":"Ὢ","Ὥ":"Ὣ",
}

_BASE_VOWEL_GREEK = set("αεηιουω")


def _apply_grave_to_ultima(text: str) -> str:
    """Acute on ultima -> grave when another word follows in the same breath."""
    n = len(text)
    out = list(text)
    i = 0
    while i < n:
        if not _is_word_char(out[i]):
            i += 1
            continue
        j = i
        while j < n and (_is_word_char(out[j]) or out[j] == CORONIS):
            j += 1
        k = j
        while k < n and out[k].isspace():
            k += 1
        following_is_word = (k < n and _is_word_char(out[k]))

        if following_is_word:
            for x in range(j - 1, i - 1, -1):
                ch = out[x]
                if ch in _ACUTE_TO_GRAVE:
                    # Verify the acute is on the ultima (no vowel after it
                    # within the same word).
                    has_vowel_after = False
                    for y in range(x + 1, j):
                        d = unicodedata.normalize("NFD", out[y].lower())
                        base = "".join(c for c in d if not unicodedata.combining(c))
                        if base in _BASE_VOWEL_GREEK:
                            has_vowel_after = True
                            break
                    if not has_vowel_after:
                        out[x] = _ACUTE_TO_GRAVE[ch]
                    break
        i = j
    return "".join(out)


def _passthrough(s: str) -> str:
    """A trivial mapping for words that have no Latin vowels (rare)."""
    return s


# =============================================================================
# Public API
# =============================================================================

_NON_WORD_RE = re.compile(r"(\W+)", flags=re.UNICODE)

def transliterate_latin(text: str) -> str:
    """Transliterate Latin text to Greek letters with stress-based accents.

    Each word is processed independently; punctuation and whitespace are
    preserved. Apostrophes between letters become Greek koronis (᾽).
    """
    if not text:
        return text

    parts = _NON_WORD_RE.split(text)
    out = []
    for p in parts:
        if not p:
            continue
        if _NON_WORD_RE.fullmatch(p):
            out.append(p)
        else:
            # Macronize the word first (adds long-vowel marks via lexicon +
            # heuristics), then transliterate.
            macronized = _macronize(p)
            greek, _ = _transliterate_word(macronized)
            out.append(greek)

    joined = "".join(out)

    # Replace apostrophes between two letters with coronis.
    chars = list(joined)
    for i, ch in enumerate(chars):
        if ch in _APOSTROPHES:
            prev_c = chars[i - 1] if i > 0 else ""
            next_c = chars[i + 1] if i + 1 < len(chars) else ""
            if _is_word_char(prev_c) and _is_word_char(next_c):
                chars[i] = CORONIS
    joined = "".join(chars)

    # Apply the acute→grave rule.
    joined = _apply_grave_to_ultima(joined)

    return joined


# =============================================================================
# CLI for quick testing
# =============================================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(transliterate_latin(" ".join(sys.argv[1:])))
    else:
        samples = [
            "Caesar",
            "Augustus",
            "Cicero",
            "philosophia",
            "amīcus",        # heavy penult by nature -> stress on penult
            "amicus",        # without macron: short by default, stress on antepenult
            "Roma",
            "Rōma",
            "imperium",      # 4 syllables: im-pe-ri-um. penult 'ri' light -> antepenult
            "Vergilius",
            "Quintus",
            "philosophia est ars",
            "veni vidi vici",
            "Vivamus mea Lesbia atque amemus",
            "Catullus",
            "rhetor dixit",
            "habeo, habēbam, habēbō",
        ]
        for s in samples:
            print(f"{s:38s} -> {transliterate_latin(s)}")