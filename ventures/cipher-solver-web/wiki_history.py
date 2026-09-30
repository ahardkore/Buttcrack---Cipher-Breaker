"""The history articles: codebreaking, the people who did it, and the ciphers.

Three long-form pages, hand-written. Where a claim is disputed (who invented
the Vigenere cipher, whether the Beale papers are genuine) the page says so
rather than picking the tidy version, and where a puzzle is unsolved it is
described as unsolved rather than as nearly solved.
"""

from __future__ import annotations

TIMELINE = [
    ("9th century", "al-Kindi, Baghdad",
     "The <em>Manuscript on Deciphering Cryptographic Messages</em> describes counting "
     "letter frequencies and matching them against the frequencies of the language. It is "
     "the first written account of cryptanalysis anywhere, and it makes every "
     "monoalphabetic cipher obsolete in the same stroke."),
    ("1467", "Leon Battista Alberti, Florence",
     "The cipher disk: two concentric alphabets that can be turned mid-message. Alberti's "
     "polyalphabetic idea is the first real answer to al-Kindi, and it takes European "
     "cryptography four centuries to use it properly."),
    ("1553", "Giovan Battista Bellaso",
     "Publishes the cipher the world would later call Vigenere's — a repeating keyword "
     "selecting a different alphabet for each letter."),
    ("1586", "Blaise de Vigenere",
     "The <em>Traicté des chiffres</em> describes the autokey cipher, in which the "
     "plaintext extends its own key. It is genuinely stronger than the cipher that took "
     "his name, and it is the one that did not catch on."),
    ("1854", "Charles Babbage",
     "Breaks Vigenere by spotting that repeated ciphertext fragments reveal the key "
     "length. He never publishes, possibly at the request of British intelligence during "
     "the Crimean War, and the credit goes elsewhere."),
    ("1863", "Friedrich Kasiski",
     "Publishes the same attack. The Kasiski examination — measure the gaps between "
     "repeated fragments, take their common factors — is still the first thing this "
     "solver tries on a suspected polyalphabetic cipher."),
    ("1883", "Auguste Kerckhoffs",
     "States the principle that a cipher must stay secure when everything about it except "
     "the key is public. Every honest claim in cryptography since is measured against it."),
    ("1917", "Room 40, London",
     "Nigel de Grey and William Montgomery decrypt the Zimmermann Telegram, in which "
     "Germany offers Mexico an alliance against the United States. Britain then has to "
     "leak it without revealing that it reads German traffic. It is the clearest case in "
     "history of cryptanalysis changing the course of a war."),
    ("1918", "Georges Painvin, France",
     "Breaks ADFGVX — a fractionating cipher over a transposition — during the German "
     "spring offensive, reportedly losing fifteen kilos in the three months it takes. The "
     "decrypt that locates the attack is called the Radiogram of Victory."),
    ("1920s", "William and Elizebeth Friedman",
     "William Friedman's <em>Index of Coincidence and Its Applications in Cryptography</em> "
     "(1922) turns codebreaking into statistics and coins the word cryptanalysis. "
     "Elizebeth Smith Friedman breaks the ciphers of Prohibition smugglers and, later, "
     "Nazi intelligence networks in South America — work credited to J. Edgar Hoover's "
     "FBI for decades."),
    ("1932", "Marian Rejewski, Poland",
     "Using permutation theory and material from French intelligence, Rejewski "
     "reconstructs the internal wiring of the German Enigma — a machine he has never "
     "seen. With Jerzy Rozycki and Henryk Zygalski he builds the cyclometer and the "
     "bomba. In July 1939, weeks before the invasion, Poland hands everything to Britain "
     "and France."),
    ("1939-45", "Bletchley Park",
     "Alan Turing and Gordon Welchman design the bombe, whose diagonal board turns a crib "
     "into a contradiction machine. Turing's Banburismus applies sequential Bayesian "
     "reasoning to naval Enigma years before the statistics literature catches up. Joan "
     "Clarke works in Hut 8; Mavis Batey breaks the Italian naval traffic behind Matapan "
     "and the Abwehr machine that makes the D-Day deception possible."),
    ("1941-45", "Tunny and Colossus",
     "Bill Tutte deduces the structure of the Lorenz SZ40 from a single mis-sent message, "
     "without ever seeing the machine — arguably the greatest single feat of cryptanalysis "
     "on record. Tommy Flowers builds Colossus, 1,600 valves, to do the statistics: the "
     "first electronic digital computer, and classified for thirty years afterwards."),
    ("1940", "Purple, Washington",
     "Frank Rowlett's team reconstructs the Japanese diplomatic machine by pure analysis. "
     "Genevieve Grotjan spots the pattern that opens it. The US is reading Tokyo's "
     "diplomatic traffic before Pearl Harbor — which is not the same as knowing where the "
     "carriers were going."),
    ("1943-80", "Venona",
     "A tiny reuse of one-time pad key material by Soviet cipher clerks is enough. "
     "Meredith Gardner and colleagues read fragments of Soviet intelligence traffic for "
     "decades. A one-time pad is unbreakable only if the pad is used exactly once."),
    ("1976-78", "Public-key cryptography",
     "Diffie and Hellman publish key exchange without a shared secret; Rivest, Shamir and "
     "Adleman publish RSA. (Clifford Cocks at GCHQ had the same idea in 1973; it stayed "
     "classified until 1997.) Cryptography stops being a government monopoly."),
    ("1990-93", "Modern cryptanalysis",
     "Biham and Shamir publish differential cryptanalysis; it emerges later that IBM and "
     "the NSA knew of it in 1974 and quietly hardened DES against it. Matsui publishes "
     "linear cryptanalysis in 1993. Attacks become statistical again, on a new scale."),
    ("2020", "Zodiac Z340",
     "Fifty-one years after it was posted, the Zodiac killer's 340-character cipher falls "
     "to David Oranchak, Sam Blake and Jarl Van Eycke — a transposition wrapped around a "
     "homophonic substitution, found by search where hand analysis had failed."),
]

PEOPLE = [
    ("al-Kindi", "c. 801-873",
     "Philosopher and polymath in Baghdad's House of Wisdom who wrote the first known text "
     "on breaking ciphers. Frequency analysis — the technique at the bottom of this "
     "solver's scoring — is his."),
    ("Leon Battista Alberti", "1404-1472",
     "Architect, and author of the first polyalphabetic cipher. Called the father of "
     "Western cryptography, largely for realising that one alphabet is never enough."),
    ("Charles Babbage", "1791-1871",
     "Broke the Vigenere cipher around 1854 and published nothing about it. His notebooks "
     "record the method that Kasiski printed nine years later."),
    ("Friedrich Kasiski", "1805-1881",
     "Prussian infantry officer whose 1863 book gave the first published break of "
     "polyalphabetic ciphers. He thought it had been ignored and moved on to archaeology."),
    ("Etienne Bazeries", "1846-1931",
     "French army cryptanalyst who spent three years breaking the Great Cipher of Louis "
     "XIV — a code of 587 numbers that had been unread for two centuries."),
    ("Georges Painvin", "1886-1980",
     "Broke ADFGVX in 1918 under conditions that wrecked his health. A geologist by "
     "training, drafted into codebreaking by circumstance."),
    ("William F. Friedman", "1891-1969",
     "Invented the index of coincidence and the vocabulary of the field. Led the team that "
     "broke Purple. The IC test in this solver is his."),
    ("Elizebeth Smith Friedman", "1892-1980",
     "Broke smuggling rings, then Nazi intelligence networks in South America, testifying "
     "in court about ciphers when no one else could. Her work was credited to others for "
     "most of her life."),
    ("Agnes Meyer Driscoll", "1889-1971",
     "'Miss Aggie' — broke Japanese naval codes across three decades, including the "
     "Red Book and the work underpinning JN-25, and taught most of the US Navy's "
     "cryptanalysts."),
    ("Marian Rejewski", "1905-1980",
     "Reconstructed Enigma's wiring from permutation theory in 1932. With Rozycki and "
     "Zygalski, gave the Allies a running start of seven years."),
    ("Alan Turing", "1912-1954",
     "Designed the bombe with Welchman, invented Banburismus, and formalised computation "
     "along the way. Prosecuted in 1952 for being gay; pardoned in 2013."),
    ("Gordon Welchman", "1906-1985",
     "The diagonal board — his contribution to the bombe — multiplied its power enormously. "
     "He also built the traffic-analysis system that made Bletchley an intelligence "
     "factory rather than a puzzle room."),
    ("Bill Tutte", "1917-2002",
     "Deduced the complete structure of the Lorenz cipher machine from intercepted "
     "ciphertext alone, having never seen one. A graph theorist by trade."),
    ("Tommy Flowers", "1905-1998",
     "Post Office engineer who built Colossus when his superiors doubted valves could be "
     "reliable at that scale. He paid for parts himself and was ordered to destroy the "
     "machines afterwards."),
    ("Joan Clarke", "1917-1996",
     "One of the few women to work as a cryptanalyst rather than an operator at Bletchley, "
     "in Hut 8 on naval Enigma, and repeatedly promoted into grades that had no name for "
     "a woman doing them."),
    ("Mavis Batey", "1921-2013",
     "Broke the Italian naval Enigma traffic before Cape Matapan and the Abwehr machine "
     "whose decrypts confirmed the D-Day deception was believed."),
    ("Genevieve Grotjan Feinstein", "1913-2006",
     "Spotted the correspondence that opened Purple in September 1940, after others had "
     "looked at the same sheets for months."),
    ("Eli Biham and Adi Shamir", "1990",
     "Published differential cryptanalysis, the first general statistical attack on modern "
     "block ciphers — and discovered DES had been designed to resist it sixteen years "
     "earlier."),
    ("Mitsuru Matsui", "1993",
     "Published linear cryptanalysis and used it for the first experimental break of full "
     "DES."),
]

FAMOUS = [
    ("The Great Cipher", "France, 1660s-1890s",
     "The Rossignol family's code of 587 numbers, many standing for syllables and some "
     "for nothing at all. It protected Louis XIV's secrets and then stayed unread for two "
     "hundred years, until Bazeries broke it in the 1890s.", "solved"),
    ("The Zimmermann Telegram", "1917",
     "German code 0075, decrypted by Room 40. Britain's problem was not reading it but "
     "explaining how it came by the text without admitting it read neutral cable traffic.",
     "solved"),
    ("ADFGVX", "Germany, 1918",
     "A Polybius square over six letters chosen to be unmistakable in Morse, followed by "
     "a columnar transposition. Painvin broke it in the field.", "solved"),
    ("Enigma", "Germany, 1920s-45",
     "Rotors, a reflector and a plugboard. Its fatal property was that no letter could "
     "ever encrypt to itself, which turned a guessed crib into a mechanical test — the "
     "principle the bombe ran on.", "solved"),
    ("Lorenz SZ40/42 (Tunny)", "Germany, 1940-45",
     "Hitler's strategic teleprinter cipher, twelve wheels, far stronger than Enigma. "
     "Broken by Tutte's analysis and Colossus's speed.", "solved"),
    ("Purple", "Japan, 1939-45",
     "A stepping-switch machine for diplomatic traffic, reconstructed in Washington "
     "without a physical example ever being seen.", "solved"),
    ("Navajo code talkers", "US, 1942-45",
     "Not a cipher at all: a natural language with no written form, spoken by people the "
     "enemy had no speakers of, with a coined vocabulary for military terms. Never broken.",
     "unbroken"),
    ("The one-time pad", "Vernam, 1917; Shannon, 1949",
     "The only cipher with a proof of perfect secrecy — provided the key is truly random, "
     "as long as the message, and used exactly once. Venona is what happens when the last "
     "condition slips.", "proven"),
    ("The Voynich Manuscript", "c. 1404-1438",
     "Two hundred and forty pages in an unknown script, carbon-dated to the early "
     "fifteenth century. Statistically it behaves somewhat like language and somewhat not. "
     "Hoax, unknown language and unknown cipher all remain live possibilities.", "unsolved"),
    ("The Beale Ciphers", "published 1885",
     "Three number ciphers said to locate buried treasure in Virginia. The second decodes "
     "against the Declaration of Independence; the first and third do not decode against "
     "anything. Many researchers think the whole thing is a nineteenth-century fiction.",
     "disputed"),
    ("The Dorabella Cipher", "Elgar, 1897",
     "Eighty-seven squiggles in three orientations, sent by the composer to a young "
     "friend. Short enough that almost any proposed solution fits, which is precisely the "
     "problem.", "unsolved"),
    ("Zodiac Z408 and Z340", "1969-70",
     "Z408 was a homophonic substitution broken in a week by two schoolteachers, Donald "
     "and Bettye Harden. Z340 held out until 2020, when it turned out to be a "
     "transposition wrapped around a homophonic substitution.", "solved"),
    ("Kryptos", "Jim Sanborn, CIA headquarters, 1990",
     "Four panels. K1 and K2 are Quagmire III over a keyed alphabet, K3 is a transposition, "
     "and K4 — ninety-seven characters — has resisted public solution for over three "
     "decades despite published clues (BERLIN, CLOCK, NORTHEAST, EAST). Treat any claimed "
     "break as needing verification.", "partly unsolved"),
]


def _dash(text: str) -> str:
    """Plain ASCII in the source, real dashes on the page."""
    return text.replace(" -- ", " — ")


def _timeline_html() -> str:
    rows = "".join(
        f"    <li><strong>{when}</strong> — <em>{who}</em><br>{_dash(what)}</li>\n"
        for when, who, what in TIMELINE
    )
    return f'    <ol class="timeline">\n{rows}    </ol>'


def _people_html() -> str:
    rows = "".join(
        f"    <li><strong>{name}</strong> <span class=\"dates\">{dates}</span><br>{_dash(note)}</li>\n"
        for name, dates, note in PEOPLE
    )
    return f'    <ul class="people">\n{rows}    </ul>'


def _famous_html() -> str:
    rows = "".join(
        f"    <li><strong>{name}</strong> <span class=\"dates\">{when}</span> "
        f'<span class="status status-{status.split()[0]}">{status}</span><br>{_dash(note)}</li>\n'
        for name, when, note, status in FAMOUS
    )
    return f'    <ul class="famous">\n{rows}    </ul>'


HISTORY_PAGES = [
    {
        "slug": "history-of-codebreaking.html",
        "title": "A History of Codebreaking — From al-Kindi to Colossus and After",
        "desc": "How cryptanalysis developed: frequency analysis in ninth-century Baghdad, "
                "the Kasiski examination, the index of coincidence, Enigma and Lorenz, and "
                "the statistical attacks that define the modern field.",
        "h1": "A History of Codebreaking",
        "tagline": "Every technique in this solver has an inventor and a date. Here they are.",
        "preset": "vigenere",
        "faqs": [
            ("Who invented cryptanalysis?",
             "al-Kindi, in ninth-century Baghdad. His manuscript on deciphering messages is "
             "the first known description of frequency analysis, and it made every "
             "monoalphabetic cipher breakable."),
            ("Who really broke the Vigenere cipher?",
             "Charles Babbage, around 1854, but he never published. Friedrich Kasiski "
             "published the same attack independently in 1863, and the method carries his "
             "name."),
            ("Was Enigma broken by Britain or by Poland?",
             "Poland first. Marian Rejewski reconstructed the machine's wiring in 1932 and "
             "Polish cryptologists handed their results to Britain and France in July 1939. "
             "Bletchley Park then scaled the attack to the wartime traffic."),
            ("Is any cipher unbreakable?",
             "The one-time pad, and only under strict conditions: the key must be truly "
             "random, as long as the message, and never reused. The Venona decrypts exist "
             "because Soviet clerks reused pad material."),
        ],
        "body": f"""    <p>Cryptanalysis is younger than cryptography by a few thousand years and has been
    winning for about eleven hundred of them. What follows is the line of descent for the
    techniques this solver actually uses — frequency analysis, the Kasiski examination, the
    index of coincidence, hill climbing on n-gram statistics — with the people who found
    them.</p>

    <h2>The timeline</h2>
{_timeline_html()}

    <h2>What the pattern shows</h2>
    <p>Three things recur. First, ciphers are broken by <em>structure</em>, not by
    guessing: al-Kindi counted letters, Kasiski measured gaps, Friedman computed
    coincidences, Tutte inferred a machine from its output. Second, the break usually
    arrives through operator habit rather than mathematics — repeated message keys, stock
    openings, a reused pad. Third, the people who did the work were frequently not
    credited: Babbage published nothing, Elizebeth Friedman's cases were attributed to the
    FBI, Flowers was ordered to destroy his own computers, and Bletchley's staff said
    nothing for thirty years.</p>

    <h2>Where this tool sits</h2>
    <p>Nothing here is novel. This solver is al-Kindi's frequency analysis and Friedman's
    index of coincidence, run a few million times a second, with quadgram statistics
    standing in for a human's sense of whether a line reads as English. What has changed
    since 1945 is the cost of trying: a hill climb over 25! alphabets is not a cleverer
    idea than anagramming by hand, only a faster one.</p>

    <p>Read on: <a href="famous-cryptanalysts.html">the cryptanalysts themselves</a>, or
    <a href="famous-ciphers.html">the ciphers that made history</a> — and the ones still
    unread.</p>""",
    },
    {
        "slug": "famous-cryptanalysts.html",
        "title": "Famous Cryptanalysts — The People Who Broke the Codes",
        "desc": "Profiles of the codebreakers: al-Kindi, Babbage, Kasiski, William and "
                "Elizebeth Friedman, Rejewski, Turing, Tutte, Flowers, Batey, Grotjan, "
                "Biham, Shamir and Matsui.",
        "h1": "The Codebreakers",
        "tagline": "Who broke what, when, and what it cost them.",
        "preset": "substitution",
        "faqs": [
            ("Who was the first cryptanalyst?",
             "al-Kindi, around the ninth century, whose manuscript describes frequency "
             "analysis — the first systematic method for reading a cipher without the key."),
            ("Who broke Enigma?",
             "Marian Rejewski reconstructed the machine in 1932; Rozycki and Zygalski built "
             "the Polish attacks; Turing and Welchman designed the bombe that scaled them. "
             "It was a relay, not a single sprint."),
            ("Who was Elizebeth Friedman?",
             "A cryptanalyst who broke smuggling ciphers during Prohibition and later Nazi "
             "intelligence networks in South America. Much of her work was publicly credited "
             "to the FBI during her lifetime."),
            ("What did Bill Tutte do?",
             "He reconstructed the entire logical structure of the Lorenz SZ40 cipher "
             "machine from intercepted ciphertext, without ever seeing the device — the "
             "work that led to Colossus."),
        ],
        "body": f"""    <p>Codebreaking has no single inventor and very few heroes who worked alone. These are
    the people whose methods are still in use — including several whose names were withheld
    for decades by the secrecy of the work.</p>

    <h2>Profiles</h2>
{_people_html()}

    <h2>A note on credit</h2>
    <p>The history of this field is unusually bad at attribution, and not by accident.
    Secrecy delayed recognition by decades (Bletchley), classification erased it entirely
    for a time (Cocks and public-key cryptography), and institutional habit reassigned it
    (Elizebeth Friedman's cases). Where the record is contested, the pages on this site say
    so rather than picking whichever version is tidier.</p>

    <p>Next: <a href="history-of-codebreaking.html">the timeline</a> or
    <a href="famous-ciphers.html">the ciphers themselves</a>.</p>""",
    },
    {
        "slug": "famous-ciphers.html",
        "title": "Famous and Historical Ciphers — Solved, Unsolved and Disputed",
        "desc": "The ciphers that mattered: the Great Cipher, the Zimmermann Telegram, "
                "ADFGVX, Enigma, Lorenz, Purple and the one-time pad — plus Voynich, Beale, "
                "Dorabella, Zodiac and Kryptos.",
        "h1": "Famous Ciphers",
        "tagline": "The ones that changed history, and the handful nobody has read yet.",
        "preset": "layered",
        "faqs": [
            ("What is the most famous unsolved cipher?",
             "The Voynich Manuscript is the best known. Kryptos K4, the Beale ciphers and "
             "Elgar's Dorabella cipher are the other long-standing open cases."),
            ("Has the Zodiac cipher been solved?",
             "Z408 was solved within a week in 1969 by Donald and Bettye Harden. Z340 held "
             "out until December 2020, when David Oranchak, Sam Blake and Jarl Van Eycke "
             "showed it was a transposition over a homophonic substitution."),
            ("What is Kryptos?",
             "A sculpture by Jim Sanborn at CIA headquarters carrying four encrypted panels. "
             "Three are solved; the fourth, ninety-seven characters long, has resisted "
             "public solution since 1990 despite several clues released by the artist."),
            ("Was any cipher never broken?",
             "The Navajo code talkers' system was never broken during the war — though it "
             "was a language plus a code vocabulary rather than a cipher. A correctly used "
             "one-time pad is provably unbreakable."),
        ],
        "body": f"""    <p>A cipher earns its place in history either by protecting something that mattered or
    by failing to. Both kinds are here, along with the small set of messages that nobody has
    yet read.</p>

    <h2>The ciphers</h2>
{_famous_html()}

    <h2>Why unsolved ciphers stay unsolved</h2>
    <p>Rarely because the cipher is strong. Usually the message is too <em>short</em>: with
    eighty-seven symbols, as in the Dorabella cipher, many different keys produce something
    that reads plausibly, and nothing distinguishes the right one. That is a problem of
    evidence rather than of computing power, and it does not go away with a faster machine
    — which is why this solver caps its own confidence when a key is large relative to the
    text it was recovered from.</p>

    <p>The other common reason is a wrong assumption held collectively for years. Z340
    resisted for half a century partly because analysts assumed the transposition ran one
    way when it ran another.</p>

    <p>More: <a href="history-of-codebreaking.html">the timeline of codebreaking</a> and
    <a href="famous-cryptanalysts.html">the people who did it</a>. To try the classical
    ciphers yourself, start at the <a href="cipher-wiki.html">cipher wiki</a>.</p>""",
    },
]
