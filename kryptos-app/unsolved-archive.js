// Curated reading list for famous unresolved cipher and script problems.
// Each entry links to a primary, institutional, scholarly, or specialist source.
const UNSOLVED_CIPHER_ARCHIVE = [
  {
    id: "dagapeyeff",
    title: "D’Agapeyeff Cipher",
    date: "1939",
    kind: "Challenge ciphertext",
    summary: "Alexander D’Agapeyeff published this 395-digit exercise in the first edition of Codes and Ciphers. No plaintext or method has been verified; a construction or transcription error remains a live possibility.",
    boundary: "An English-looking fragment is not a solution without an exact, reproducible construction for the published digits.",
    sourceLabel: "Read the MysteryTwister challenge transcript",
    sourceUrl: "https://mysterytwister.org/media/challenges/pdf/mtc3-schmeh-02-agapeyeff-en.pdf"
  },
  {
    id: "zodiac-z13",
    title: "Zodiac Z13",
    date: "1970",
    kind: "13-symbol cryptogram",
    summary: "The short cipher follows the phrase “My name is—” in a Zodiac letter. Its length leaves too little information to distinguish a proposed name from other fitting candidates, and no definitive solution is accepted.",
    boundary: "Treat proposed names as hypotheses, not identifications, unless a method supplies unique and independently checkable validation.",
    sourceLabel: "Read the cipher overview",
    sourceUrl: "https://www.history.com/articles/the-zodiac-ciphers-what-we-know"
  },
  {
    id: "zodiac-z32",
    title: "Zodiac Z32",
    date: "1970",
    kind: "32-symbol map cipher",
    summary: "This 32-symbol message accompanied a San Francisco Bay Area map and was said to concern a bomb location. It has not been definitively decoded; the map context does not turn a candidate reading into proof.",
    boundary: "A credible solution must account for the full symbol sequence and produce a falsifiable connection to the accompanying map.",
    sourceLabel: "Read the cipher overview",
    sourceUrl: "https://www.history.com/articles/the-zodiac-ciphers-what-we-know"
  },
  {
    id: "dorabella",
    title: "Dorabella Cipher",
    date: "1897",
    kind: "87-glyph personal cryptogram",
    summary: "Composer Edward Elgar’s note to Dora Penny uses a small set of curved glyphs. Textual and musical interpretations have been proposed, but no reading has gained consensus as the intended message.",
    boundary: "The short text admits many plausible readings; historical fit and an exact, consistently applied key are required before calling one a solution.",
    sourceLabel: "Read about Elgar’s cipher",
    sourceUrl: "https://nautil.us/the-artist-of-the-unbreakable-code-234588"
  },
  {
    id: "beale",
    title: "Beale Ciphers 1 & 3",
    date: "Published 1885",
    kind: "Number-cipher / treasure legend",
    summary: "Of three number ciphers in the Beale Papers, only cipher 2 has a demonstrated Declaration of Independence key. The location and heir messages, ciphers 1 and 3, remain open—and the underlying treasure story itself is unverified.",
    boundary: "The archive separates the unsolved texts from the historical claim: a decryption would not by itself authenticate the treasure narrative.",
    sourceLabel: "Read the Cipher Museum’s provenance note",
    sourceUrl: "https://ciphermuseum.com/ciphers/beale.html"
  },
  {
    id: "voynich",
    title: "Voynich Manuscript",
    date: "15th–16th century",
    kind: "Undeciphered manuscript / script",
    summary: "Beinecke MS 408 is written in an unidentified script by an unknown author. It is not established that the writing is a cipher at all; cryptographic approaches have not produced an accepted decipherment.",
    boundary: "This belongs in an undeciphered-script archive, not in a list of solved cipher systems. Yale provides high-resolution research images.",
    sourceLabel: "View Yale’s Beinecke record and scans",
    sourceUrl: "https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript"
  },
  {
    id: "phaistos",
    title: "Phaistos Disc",
    date: "Bronze Age Crete",
    kind: "Undeciphered inscribed object",
    summary: "The unique spiral object bears more than 240 stamped signs. Its script, language, purpose, and even whether it should be treated as ordinary text remain unresolved because there is no comparable corpus or bilingual key.",
    boundary: "Proposed readings are not established decipherments. The archive labels it an undeciphered object rather than assuming a specific cipher mechanism.",
    sourceLabel: "Read the archaeological context",
    sourceUrl: "https://anetoday.org/phaistos-disk/"
  }
];
