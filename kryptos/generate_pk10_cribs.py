import itertools

openers = [
    # Needle in hand / using the needle
    "WITHTHENEEDLEINHAND",
    "WITHTHENEEDLEINMYHAND",
    "WITHTHESILVERNEEDLE",
    "WITHTHEEXQUISITENEEDLE",
    "HOLDINGTHENEEDLEIN",
    "ITOKETHENEEDLEAND",
    "ITOOKTHENEEDLEAND",
    "HETOKETHENEEDLEAND",
    "HETOOKTHENEEDLEAND",
    "NOWWITHTHENEEDLE",
    "NOWWITHTHISNEEDLE",
    "WITHTHISINSTRUMENT",
    "WITHTHISNEEDLEINHAND",
    
    # Unravelling the knot
    "IUNRAVELEDTHEKNOT",
    "WEUNRAVELEDTHEKNOT",
    "HEUNRAVELEDTHEKNOT",
    "THEKNOTWASUNRAVELED",
    "THEKNOTWASATLAST",
    "ATLASTTHEKNOTWAS",
    "THEKNOTBEGANTOUNRAVEL",
    "IINSERTEDTHENEEDLE",
    "HEINSERTEDTHENEEDLE",
    "SLIPPINGTHENEEDLEINTO",
    "INSERTINGTHENEEDLE",
    "THEFINEPOINTPIERCED",
    "THENEEDLESLIPPEDINTO",
    "THENEEDLEENTEREDTHE",
    "EACHTHREADUNRAVELED",
    "THREADBYTHREADTHEKNOT",
    "THREADBYTHREADITUN",
    "ASITUNRAVELEDTHE",
    "ASTHEKNOTUNRAVELED",
    "ONCEUNRAVELEDITREVEALS",
    "ONCEUNRAVELEDTHEROUTE",
    "THEROUTETOTHELOST",
    "THEROUTETOTHEARCHIVE",
    "THEROUTEWASREVEALED",
    
    # Archive of Pellegrin
    "THELOSTARCHIVEOFPELLE",
    "THELOSTARCHIVEOFOUR",
    "THEARCHIVEOFPELLEGRIN",
    "THEARCHIVESOFPELLEGRIN",
    "THEARCHIVEWASFOUND",
    "THEARCHIVEWASOPENED",
    "WEFOUNDTHELOSTARCHIVE",
    "IFOUNDTHELOSTARCHIVE",
    "ATLASTTHELOSTARCHIVE",
    "INTHESECRETARCHIVE",
    "INTHESECRETROOMAT",
    "INSIDETHELOSTARCHIVE",
    "INSIDETHEARCHIVEOF",
    
    # Investigation log / final report
    "INVESTIGATIONLOGITEM",
    "FINALREPORTITEMEIGHT",
    "ACCESSIONLOGITEMEIGHT",
    "CONCLUDINGREPORTON",
    "TWELVEPRIORARCHIVISTS",
    "FORTHEFIRSTTIMEIN",
    "AFTERTENYEARSOFSTUDY",
    "AFTERTENYEARSINTHE",
    "HAVINGCOMPLETEDMYTEN",
    "HAVINGMADEANEEDLEOF",
    "MYOWNMAKINGREVEALED",
    "ONEOFMYOWNMAKINGWAS",
]

continuations = [
    "AND", "THE", "IN", "TO", "OF", "AT", "ON", "WITH", "BY", "FOR",
    "IT", "HE", "WE", "IS", "AS", "THAT", "THIS", "WAS", "WERE", "HAD",
    "BEGAN", "FOUND", "COULD", "WOULD", "REVEALED", "OPENED", "SHOWED"
]

subjects = [
    "THESECRET", "THEROUTE", "THEARCHIVE", "THEKNOT", "THETHREAD",
    "THELETTERS", "THEWORDS", "THEMESSAGE", "THECHAMBER", "THELIBRARY",
    "THEVAULT", "THECHEST", "THEVOLUME", "THETREATISE", "THEMANUSCRIPT"
]

all_cribs = set()

# Extend or truncate to exactly 22 chars
for op in openers:
    if len(op) == 22:
        all_cribs.add(op)
    elif len(op) < 22:
        rem = 22 - len(op)
        for c in continuations:
            if len(c) == rem:
                all_cribs.add(op + c)
            elif len(c) < rem:
                rem2 = rem - len(c)
                for s in subjects:
                    if len(s) >= rem2:
                        all_cribs.add((op + c + s)[:22])
        for s in subjects:
            if len(s) >= rem:
                all_cribs.add((op + s)[:22])
    else:
        all_cribs.add(op[:22])

print(f"Generated {len(all_cribs)} unique 22-char cribs.")
with open("pk10_narrative_cribs.txt", "w") as f:
    for c in sorted(all_cribs):
        f.write(c + "\n")
