/* PK records come from the shared generated catalog, not hand-maintained copies.
 * CIA entries are separately labelled; incomplete legacy excerpts cannot earn
 * an exact PK corpus match or a reproduced-decryption badge. */
const KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const STANDARD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const CIPHERS_DATA = Object.fromEntries(PARADIGM_KRYPTOS.map(record => [record.id, {
  ...record, category: "Paradigm Kryptos", status: "DOCUMENTED REFERENCE",
  length: record.ciphertext_length, method: record.verification,
  challengeUrl: `https://paradigm.xyz/kryptos-ctf/${record.id.toLowerCase()}`,
  notes: "Exact normalized reference from the shared PK catalog. Lookup alone does not reproduce a proposed decryption; use Research Mode to execute the method.",
}]));
Object.assign(CIPHERS_DATA, {
  "K1": {
    "id": "K1",
    "title": "K1 — Palimpsest",
    "length": 63,
    "status": "REFERENCE",
    "category": "CIA Sculpture",
    "mechanism": "Vigenère on Keyed Kryptos Alphabet",
    "key": "PALIMPSEST / KRYPTOS",
    "ciphertext": "EMUFPHZLRFAXYUSDJKZLDKRNSHGNFIVJYQTQUXQBQVYUVLLTREVJYQTMKYRDMFD",
    "plaintext": "BETWEENSUBTLESHADINGANDTHEABSENCEOFLIGHTLIESTHENUANCEOFIQLUSION",
    "notes": "Local K1 transcription from kryptos/kryptos_solve.py. Reproduction can be tested with PALIMPSEST in the KRYPTOS alphabet; not part of the PK corpus matcher."
  },
  "K2": {
    "id": "K2",
    "title": "K2 — Abscissa",
    "length": 367,
    "status": "INCOMPLETE REFERENCE",
    "category": "CIA Sculpture",
    "mechanism": "Vigenère on Keyed Kryptos Alphabet",
    "key": "ABSCISSA / KRYPTOS",
    "ciphertext": "VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKK?DQMCPFQZDQDuplicate...[truncated]",
    "plaintext": "IT WAS TOTALLY INVISIBLE HOWS THAT POSSIBLE THEY USED THE EARTHS MAGNETIC FIELD X THE INFORMATION WAS GATHERED AND TRANSMITTED UNDERGRUUND TO AN UNKNOWN LOCATION X DOES LANGLEY KNOW ABOUT THIS THEY SHOULD ITS BURIED OUT THERE SOMEWHERE X WHO KNOWS THE EXACT LOCATION ONLY WW THIS WAS HIS LAST MESSAGE X THIRTY EIGHT DEGREES FIFTY SEVEN MINUTES SIX POINT FIVE SECONDS NORTH SEVENTY SEVEN DEGREES EIGHT MINUTES FORTY FOUR SECONDS WEST LAYER TWO",
    "notes": "Legacy incomplete excerpt, not a complete published transcription. Do not use it to verify a proposed solution. Paste an authoritative complete transcription into Research Mode as custom input.",
    "reference_complete": false
  },
  "K3": {
    "id": "K3",
    "title": "K3 — Howard Carter's Tomb",
    "length": 337,
    "status": "INCOMPLETE REFERENCE",
    "category": "CIA Sculpture",
    "mechanism": "Columnar Transposition (Width 7 & 4)",
    "key": "KRYPTOS / CARTER",
    "ciphertext": "ENDYAHROHNLSRHEOCPTEOIBIDYSHNAIACHTNREYULDSLLSLLNOHSNOSMRWXMNETPRNGATIHNRARPESLNNELEBLRMIHRSETOHO...[truncated]",
    "plaintext": "SLOWLY DESPARATLY SLOWLY THE REMAINS OF PASSAGE DEBRIS THAT ENCUMBERED THE LOWER PART OF THE DOORWAY WAS REMOVED WITH TREMBLING HANDS I MADE A TINY BREACH IN THE UPPER LEFT HAND CORNER AND THEN WIDENING THE HOLE A LITTLE I INSERTED THE CANDLE AND PEERED IN THE HOT AIR ESCAPING FROM THE CHAMBER CAUSED THE FLAME TO FLICKER BUT PRESENTLY DETAILS OF THE ROOM WITHIN EMERGED FROM THE MIST X CAN YOU SEE ANYTHING Q",
    "notes": "Legacy incomplete excerpt, not a complete published transcription. Do not use it to verify a proposed solution. Paste an authoritative complete transcription into Research Mode as custom input.",
    "reference_complete": false
  },
  "K4": {
    "id": "K4",
    "title": "K4 — 97-letter research ciphertext",
    "length": 97,
    "status": "RESEARCH",
    "category": "CIA Sculpture",
    "mechanism": "Unknown; competing methods are research hypotheses",
    "key": "Confirmed Anchors: EAST, NORTHEAST, BERLIN, CLOCK",
    "ciphertext": "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR",
    "plaintext": "",
    "notes": "Clue placements recorded in this repository (one-based): EAST 22–25, NORTHEAST 26–34, BERLIN 64–69, CLOCK 70–74. Clues are constraints, not a full recovered plaintext or a cipher-family proof. No claim about current private recovery, custody or disclosure is made here."
  }
});
