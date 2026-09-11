"""The material vocabulary shared by pricing and the listing builder.

canonical (glossary-corrected) spoken word -> data/reference/material_rates.csv key.
Deliberately independent of craft_glossary.csv's file structure (that file mixes
techniques/objects/materials under comments, not a machine-readable type column).

Its own dependency-free module so pipelines.voice.describe can reuse it for the
category guess without importing attributes.py's OpenCV/Whisper stack.
"""
from __future__ import annotations

MATERIAL_TERMS: dict[str, str] = {
    "clay": "clay", "terracotta clay": "terracotta", "terracotta": "terracotta",
    "brass": "brass", "copper": "copper", "silver": "silver",
    "cotton": "cotton", "silk": "silk", "wool": "wool", "jute": "jute",
    "bamboo": "bamboo", "sandalwood": "sandalwood", "wood": "wood",
    "leather": "leather",
    "मिट्टी": "clay", "पीतल": "brass", "तांबा": "copper", "चांदी": "silver",
    "सूती": "cotton", "रेशम": "silk", "बांस": "bamboo", "लकड़ी": "wood",
    # Oblique/adjective forms and plain-Hindi words that were missing (Day 7,
    # same class of gap as leather on 7 Sep): "तांबे का बर्तन" ("a vessel OF
    # copper") never matched "तांबा", and wool/jute/sandalwood/terracotta/raw
    # cotton only had English entries.
    "तांबे": "copper", "रेशमी": "silk", "ऊन": "wool", "ऊनी": "wool",
    "जूट": "jute", "चंदन": "sandalwood", "टेराकोटा": "terracotta", "कपास": "cotton",
    # "चमड़ा"/"चमड़े" (the plain Hindi word, inflected form "of leather") and
    # "लेदर" (the common English-loanword transliteration) — found missing
    # live 7 Sep: a real leather-sandal voice note said "लेदर" clearly, but
    # nothing in this dict recognised it, so material silently came back
    # empty. Leather goods (chappals, bags, belts) are a major Indian craft
    # category this vocabulary had no entry for at all.
    "चमड़ा": "leather", "चमड़े": "leather", "लेदर": "leather",
    # The English word "clay" as Whisper writes it in Devanagari — found by
    # scripts/offline_check.py on the demo note clay-bartan.m4a ("ये एक कले का
    # बर्तन है"), where material came back empty.
    "क्ले": "clay", "कले": "clay",
}
