import argostranslate.translate
from french_to_greek import transliterate

english = "I love philosophy"
french = argostranslate.translate.translate(english, "en", "fr")
greek_script = transliterate(french)

print("English:    ", english)
print("French:     ", french)
print("Greek script:", greek_script)