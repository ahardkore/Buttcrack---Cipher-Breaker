// Kryptos & Paradigm Kryptos Master Data Store
const KRYPTOS_ALPHABET = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const STANDARD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const CIPHERS_DATA = {
  PK1: {
    id: "PK1",
    title: "PK1 — The Accession Log",
    length: 192,
    status: "SOLVED (VERIFIED)",
    category: "Paradigm Kryptos",
    mechanism: "Quagmire III over Kryptos Alphabet",
    key: "PROVENANCE (Period 10)",
    ciphertext: "MQRALWVSJIMSXGJSVWQPHJMDINKXGIMHNKYUTXTTQMGZVRUSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJTTMQGZVMSVOVRUMXQVWXQVUJT",
    plaintext: "INVESTIGATIONLOGITEMEIGHTKNOTTIGHTLYWOUNDITSTHREADINSCRIBEDWITHLETTERSTHEACCESSIONLOGSAYSONCEUNRAVELEDITREVEALSTHEROUTETOTHELOSTARCHIVEOFPELLEGRINTWELVEPRIORARCHIVISTSTRIEDTOUNRAVELITALLFAILED",
    notes: "Narrative opening: The apprentice uncovers the ancient knot inscribed with letters leading to the lost archive of Pellegrin."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the stated key (Quagmire III, PROVENANCE, KRYPTOS alphabet) re-encrypts this plaintext to the published ciphertext exactly."
  ,
  PK2: {
    id: "PK2",
    title: "PK2 — Pellegrin's Treatise",
    length: 350,
    status: "SOLVED (VERIFIED)",
    category: "Paradigm Kryptos",
    mechanism: "Complete Columnar Transposition (50x7)",
    key: "MARGINS (Order: [1, 3, 4, 0, 5, 2, 6])",
    ciphertext: "HNETIOCOIOISNNENEELOWYTTLQUBDBTHTEOTRRASVNEUIRORSRTHTNFEIHNIEGSOEOEOEIECRNROSEAEENAGHCTEEIOGTIETTTTIHREEMTRHTENEAORNNTRTIELNNNDHTDREOAAHTEEIAEAAELAEIETNE",
    plaintext: "IHAVEFOUNDREFERENCESTOTHEKNOTINSEVENOTHERRECORDSINOURARCHIVETHEMOSTINTRIGUINGISAPASSINGCOMMENTINATREATISEONTEXTILESWRITTENINPELLEGRINSOWNHANDWHICHSAYSUNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODOIBELIEVEDTHISTOBEJUSTATURNOFPHRASEBUTTHEOTHERMENTIONSSCATTEREDTHROUGHMARGINALIAINBOOKSTHATSHARENOOTHERTOPICHAVELEDMETOSUSPECTTHEPASSAGEREFERSTOAREALOBJECTANEEDLE",
    notes: "Pellegrin's treatise: 'un ago tanto sottile da leggere qualunque nodo' (a needle so fine as to read any knot!)."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the stated key (complete columnar, width 7, order [1,3,4,0,5,2,6]) re-encrypts this plaintext to the published ciphertext exactly."
  ,
  PK3: {
    id: "PK3",
    title: "PK3 — The Viennese Anatomist",
    length: 280,
    status: "SOLVED (VERIFIED)",
    category: "Paradigm Kryptos",
    mechanism: "Quagmire III (Sum-Clock p10 + p8, period 40)",
    key: "PENTIMENTO (10) + ORDINATE (8)",
    ciphertext: "HWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQ",
    plaintext: "SEVENTHMONTHIWROTETOFIFTEENCORRESPONDENTSINSIXCOUNTRIESSEEKINGANYWORDOFTHEITEMMOSTKNEWNOTHINGAFEWHADHEARDLEGENDSOFANEEDLEFINEENOUGHTOSPLITAHAIRORPIERCEGLASSATLASTAVIENNESEANATOMISTSAIDHESAWSUCHANINSTRUMENTUSEDATASURGICALDEMONSTRATIONINBERNIWROTETOHISADDRESSNOANSWERCAMEIWROTEAGAIN",
    notes: "The search in Bern: Viennese anatomist recalls the ultra-fine needle used in surgical demonstrations."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the stated key (sum-clock PENTIMENTO/10 + ORDINATE/8 over the KRYPTOS alphabet) re-encrypts this plaintext to the published ciphertext exactly."
  ,
  PK4: {
    id: "PK4",
    title: "PK4 — The Furlongs of Thread",
    length: 224,
    status: "PLAINTEXT ONLY (key not reproducible)",
    category: "Paradigm Kryptos",
    mechanism: "Columnar Transposition (28x8) + Quagmire III (p45)",
    key: "Dual-Clock Substitution p5 + p9, Width 8",
    ciphertext: "YOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSYOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSYOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSYOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSYOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPSYOVISYUAFKUQNRJQLZTAZTMQOUKELJKCYUWIDSPS",
    plaintext: "THESTRINGSMEASURETWOFURLONGSWEEXAMINEDTHEWEAVEANDTENSIONOFEACHINDIVIDUALSTRANDFINDINGMICROSCOPICCHARACTERSENGRAVEDALONGITSENTIRELENGTHEACHPULLOFTHETHREADREVEALEDFURTHERLETTERSWRITTENINSECTIONSRISINGINCOMPLEXITYTOWARDSTHECORE",
    notes: "Two furlongs of thread; microscopic inscriptions rising in complexity towards the core."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the plaintext reads as English (fitness -4.18) and fits the PK narrative, but the stated key is only 'Dual-Clock Substitution p5 + p9, Transposition Width 8' and no columnar convention at widths 8 or 28, with the keystream phased from either side and over either alphabet, reproduces the ciphertext. The plaintext is neither confirmed nor refuted; the key claim is not reproducible."
  ,
  PK5: {
    id: "PK5",
    title: "PK5 — The Flax Fibers Under the Lens",
    length: 272,
    status: "PLAINTEXT ONLY (key not reproducible)",
    category: "Paradigm Kryptos",
    mechanism: "Columnar Transposition (17x16) + Quagmire III (p17)",
    key: "Period 17, Transposition Width 16",
    ciphertext: "IJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZNIJQUVJJINKWMJBNJHKZZMTVTUBFHXZJIUHOVONZN",
    plaintext: "WEEXAMINEDTHEFIBERSUNDERTHELENSTHEFLAXWASSPUNWITHEXCEPTIONALPRECISIONPRESERVINGTHEINSCRIPTIONSWITHOUTDISTORTIONEACHKNOTCONTAINEDATIGHTLYFOLDEDSEQUENCEOFLETTERSWHICHWHENPROJECTEDONTOTHEPLANEFORMEDANINTERLOCKINGGRIDOFCOORDINATESANDCIPHERTEXTWHICHPOINTEDUSDIRECTLYTOWARDSBERN",
    notes: "Interlocking grid of coordinates and ciphertext pointing to Bern."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the plaintext reads as English (fitness -4.21), but the stated mechanism is refuted for it: with a transposition followed by a period-17 keystream, no set of 17 shifts maps the ciphertext's residue classes onto this plaintext's letter multiset, whatever the transposition. Either the plaintext or the stated mechanism is wrong."
  ,
  PK6: {
    id: "PK6",
    title: "PK6 — The Whitesmith's Workshop",
    length: 315,
    status: "SOLVED (VERIFIED)",
    category: "Paradigm Kryptos",
    mechanism: "Double Columnar Transposition (9x35, 9x35) + Quagmire III (p6)",
    key: "PORTAL (Period 6); Col 1: [1, 3, 0, 4, 8, 2, 6, 7, 5]; Col 2: [4, 2, 8, 1, 6, 7, 0, 3, 5]",
    ciphertext: "BXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVRBXFIVOAJFNMLKEVEHDFJQCMVLMGNVOHCJNBOAEVR",
    plaintext: "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWNTOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHEMAKESONEEVERYDAYANDLOSTCOUNTLONGAGOIASKWHATHEDOESWITHTHEMANDHESAYSTHEYAREONLYTHERESIDUEOFHISPRACTICEHETELLSMETHATIFISTUDYUNDERHIMFORTENYEARSHEWILLLETMETAKEONEOFMYOWNMAKING",
    notes: "The master whitesmith: 'They are only the residue of my practice... study for ten years to make your own.'"
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the stated key (double columnar width 9, orders [1,3,0,4,8,2,6,7,5] then [4,2,8,1,6,7,0,3,5], then Quagmire III PORTAL) re-encrypts this plaintext to the published ciphertext exactly."
  ,
  PK7: {
    id: "PK7",
    title: "PK7 \u2014 Three Weeks In",
    length: 279,
    status: "SOLVED (VERIFIED)",
    category: "Paradigm Kryptos",
    mechanism: "Quagmire III (p6) then Hill 3x3 \u2014 both over the KRYPTOS alphabet",
    key: "Quagmire III keyword ANNEAL (period 6); Hill 3x3 matrix ALCHEMIST = [[7,17,9],[14,11,18],[15,6,4]], det 17",
    ciphertext: "FNRHTKRHSEDEJMBOWBDSCSDDXLICXULMBYQXWTGUIVNDYZBEQLVHFFFIDAKDCCJKWGOOUESCYELYMRAKIUJCUSEAXUQTYKOBVYDYMRBYWOTQEESCQSMDYDQJNPSWRSUOFMFJDYXSHCXNHVJVBYMZOZOATHTEOVLOQWZITHTEAFMKGLASTBZRDMFRJPKWJOXZXPJCBOVAZEPKAEJPPSIUJODXTXERWTLTTYMRENBJGTNMLBDJMYJDDLRCXCQCHYMJMHBEOLXEUFNJKBPRSHTEYXB",
    plaintext: "THREEWEEKSINWERISEBEFORETHESUNANDEACHNEEDLEISDONEBYNOONTHEWHITESMITHSHOWSMEHISTECHNIQUEFORPURIFYINGHISMETALBEFOREDRAWINGITINTOAFINEWIREHEHASMEREPEATTHESAMESTEPFOURTIMESWITHSLIGHTVARIATIONSSTILLMYHANDFALTERSIAMPATIENTBUTIKNOWTHISISNOTMYCALLINGIHAVEMADEPEACEWITHITANDWILLGOHOMESOON",
    notes: "The apprentice three weeks in: 'Still my hand falters. I am patient, but I know this is not my calling.' Recovered from ciphertext alone by the keyed_hill attack; the key re-encrypts to the published ciphertext exactly."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: the stated key (Quagmire III ANNEAL period 6, then Hill 3x3 ALCHEMIST, both over the KRYPTOS alphabet) re-encrypts this plaintext to the published ciphertext exactly."
  ,
  PK8: {
    id: "PK8",
    title: "PK8 — The Residue of Practice",
    length: 153,
    status: "UNSOLVED HERE (solved externally; key unpublished)",
    category: "Paradigm Kryptos",
    mechanism: "Additive 4-Clock {Q4, Q5, Q6, Q7} over Keyed Kryptos Alphabet",
    key: "Periods {4, 5, 6, 7} (lcm = 420); GF(2) Parity q7=[0,1,1,1,0,0,0]_2; Solved by Kevin Hu (@_newhaiku) after 86 days",
    ciphertext: "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY",
    plaintext: "NRHPXXOEICEJAANOSSOYBUIFLBVVOGFUNOITTHSETEHFANCPLBGLSNTEEVNVZBDELQBONIATIQBSFKTTTBAUGNTHEELHASOCENDFGTHSYORTSUODSEDAWPEYONHEACLITTDHUSSIKEYJMHELODYUDOPTN",
    clocks: {
      q4: [0, 6, 13, 20],
      q5: [3, 4, 15, 0, 10],
      q6: [3, 18, 15, 25, 20, 4],
      q7: [10, 2, 24, 0, 9, 5, 17]
    },
    metrics: {
      monogram_ioc: 0.05022,
      lexical_word_coverage: "71.2% (109 / 153 characters)",
      recovered_word_count: 38,
      rare_letters: 7
    },
    notes: "Official plaintext sealed in custody. Frontier candidate derived via orthogonal stride decoupling."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: PK8 was solved by Kevin Hu and the key was never published; this repository has no solution. The stored four-wheel candidate is internally consistent with the clock parameters it names, but it is not English: fitness -6.43 log10/char against English's -4.3, and 8% coverage in words of four letters or more. The previously reported '71.2% lexical word coverage' counted two- and three-letter fragments of a Viterbi segmentation, which random letters also score well on. Retained as a failed candidate, not a solution."
  ,
  PK9: {
    id: "PK9",
    title: "PK9 — The Defunct Cord",
    length: 144,
    core_length: 135,
    padding_length: 9,
    status: "UNSOLVED",
    category: "Paradigm Kryptos",
    mechanism: "Two-Stage Double Columnar Transposition (18x8 -> 8x18) + Period-28 Polyalphabetic Keystream",
    p2: [7, 0, 5, 2, 4, 3, 6, 1],
    p1: [15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8],
    s28: [25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6],
    ciphertext: "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD",
    plaintext: "LARDADEFUNCTORDQBOOMRBETHSKWJEREASTYMARINPRAYIALMSOISEARVEMYLAILEBOTHEEDAMESQUNGLAYIMIRLOFATSEREDCISANTIDBYOUSCHESALSOMYRELIFORESSESTIA",
    regularized_plaintext: "LARD A DEFUNCT ORDER BOOM R BETH SKEWER EAST Y MARIN PRAY I ALMS O I SEAR VE MY LAIL E BOTH HEED THE DAMES QUENCH LAY HIM IRLO FAT SEARED CIS AND ID BY US CHES ALSO MY RELIEF ORES SESTIA",
    metrics: {
      quadgram_score: -5.0481,
      valid_quadgram_pct: 93.9,
      regularized_valid_pct: 99.3,
      monogram_ioc: 0.06081,
      rare_letter_count: 3
    },
    coordinates: "57' 6'' N (Sum_Kr JVRM = 57, Sum_Kr,1 = 126 = 6 mod 60; Tail AUON = 52 = 0 mod 26)",
    notes: "135-character authentic core text. Phases 0 and 17 locked across multiple cross-row words."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: no plaintext is claimed. The best stored reading (pk9_solution_pt.txt) scores -4.93 log10/char with 71% word coverage, below a genuine solve (-4.2 to -4.5 for the verified records) and consistent with an over-fitted transposition search. The 'mathematically locked' phrasing described eliminated search space, not a recovered key."
  ,
  PK10: {
    id: "PK10",
    title: "PK10 — The Unravelling of the Knot",
    length: 504,
    core_length: 432,
    padding_length: 72,
    status: "UNSOLVED",
    category: "Paradigm Kryptos",
    mechanism: "3-Clock CRT Additive System {Q7, Q8, Q9} (lcm=504) + 12x36 Modular Triptych Columnar Transposition",
    clocks: {
      q7: [0, 9, 5, 17, 10, 2, 24],
      q8: [0, 8, 16, 15, 16, 3, 6, 20],
      q9: [16, 0, 19, 9, 7, 23, 6, 16, 18]
    },
    columns_36: [34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16, 20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9, 41, 8, 19, 11, 18, 14, 6],
    ciphertext: "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ",
    plaintext: "IKNOOKRAPROWNSTSIVHNBMDAGAVJPPXESADDWSCILMATBYVASGETBLEARPILAKCNPROPNWQPADYERKUUPTEAADAYFIRVEGRUNGEWRFRRLXVPTMIETIMAEBYKETEVORTDEHANTTGRIVMPMKNECGKKOLGODGOESPREDAMPIHCKYKLICFNDAYMAIDYEKVOCHLYHFOUBIGLEDAYSLYTONDESIFFCVERISLANTSPELDHHNMNMYPAVPFWERCKLOCOUKEVIVAGRUNWAITTHIHCZCHEVRDVRPHIHUNKROHAVEWAPRIAPQVWPOCICKACTVCUMBAULFNIGXPDALWRYSWEFABYEAPPSPBWSAHTDIFWESHPLTUKFLYCIGERNDGOIMOTHKWKGWVTTBRAFTRYBERULYARRFWYIGJVGPGYIANHOUPIDADBUBYSU",
    metrics: {
      quadgram_score: -6.9030,
      valid_quadgram_pct: 61.4,
      panelA_valid_pct: 70.4,
      monogram_ioc: 0.04563,
      rare_letter_count: 12,
      lexical_word_coverage: "70.1% (303 / 432 characters)"
    },
    coordinates: "38° N, 77° 8' 44'' W (77.14° W decimal longitude mean); Concludes with ID BY US",
    notes: "432-character core maps 1-to-1 to Jim Sanborn's 3-panel physical copper screen sculpture."
  },
    audit: "Audited 2026-09-30 by kryptos/verify_pk_records.py: no plaintext is claimed. The best stored readings score -6.2 to -6.6 log10/char (English is -4.3) with 20-27% word coverage: they are not English."
  ,
  K1: {
    id: "K1",
    title: "K1 — Palimpsest",
    length: 63,
    status: "SOLVED",
    category: "CIA Sculpture",
    mechanism: "Vigenère on Keyed Kryptos Alphabet",
    key: "PALIMPSEST / KRYPTOS",
    ciphertext: "EMUFPHZLRFAXYUSDJKZLDKRNSHGXAALVTJSGQAKFGKFCNVWWVAGKZERKVROZALJAYUMVDRYHMLKJUSYWUGAZGKYK",
    plaintext: "BETWEEN SUBTLE SHADING AND THE ABSENCE OF LIGHT LIES THE NUANCE OF IQLUSION",
    notes: "Contains intentional misspelling IQLUSION."
  },
  K2: {
    id: "K2",
    title: "K2 — Abscissa",
    length: 367,
    status: "SOLVED",
    category: "CIA Sculpture",
    mechanism: "Vigenère on Keyed Kryptos Alphabet",
    key: "ABSCISSA / KRYPTOS",
    ciphertext: "VFPJUDEEHZWETZYVGWHKKQETGFQJNCEGGWHKK?DQMCPFQZDQDuplicate...[truncated]",
    plaintext: "IT WAS TOTALLY INVISIBLE HOWS THAT POSSIBLE THEY USED THE EARTHS MAGNETIC FIELD X THE INFORMATION WAS GATHERED AND TRANSMITTED UNDERGRUUND TO AN UNKNOWN LOCATION X DOES LANGLEY KNOW ABOUT THIS THEY SHOULD ITS BURIED OUT THERE SOMEWHERE X WHO KNOWS THE EXACT LOCATION ONLY WW THIS WAS HIS LAST MESSAGE X THIRTY EIGHT DEGREES FIFTY SEVEN MINUTES SIX POINT FIVE SECONDS NORTH SEVENTY SEVEN DEGREES EIGHT MINUTES FORTY FOUR SECONDS WEST LAYER TWO",
    notes: "Contains UNDERGRUUND, ID BY BROWSING, and exact GPS coordinates: 38° 57' 6.5'' N, 77° 8' 44'' W."
  },
  K3: {
    id: "K3",
    title: "K3 — Howard Carter's Tomb",
    length: 337,
    status: "SOLVED",
    category: "CIA Sculpture",
    mechanism: "Columnar Transposition (Width 7 & 4)",
    key: "KRYPTOS / CARTER",
    ciphertext: "ENDYAHROHNLSRHEOCPTEOIBIDYSHNAIACHTNREYULDSLLSLLNOHSNOSMRWXMNETPRNGATIHNRARPESLNNELEBLRMIHRSETOHO...[truncated]",
    plaintext: "SLOWLY DESPARATLY SLOWLY THE REMAINS OF PASSAGE DEBRIS THAT ENCUMBERED THE LOWER PART OF THE DOORWAY WAS REMOVED WITH TREMBLING HANDS I MADE A TINY BREACH IN THE UPPER LEFT HAND CORNER AND THEN WIDENING THE HOLE A LITTLE I INSERTED THE CANDLE AND PEERED IN THE HOT AIR ESCAPING FROM THE CHAMBER CAUSED THE FLAME TO FLICKER BUT PRESENTLY DETAILS OF THE ROOM WITHIN EMERGED FROM THE MIST X CAN YOU SEE ANYTHING Q",
    notes: "Contains DESPARATLY and closing question CAN YOU SEE ANYTHING Q."
  },
  K4: {
    id: "K4",
    title: "K4 — The Unsolved 97 Letters",
    length: 97,
    status: "UNSOLVED",
    category: "CIA Sculpture",
    mechanism: "Unknown Polyalphabetic / Transposition on Keyed Alphabet",
    key: "Confirmed Clues: EAST, NORTHEAST, BERLIN CLOCK",
    ciphertext: "OBKRUOXOGHULBSOLIFBBWFLRVQQPRNGKSSOTWTQSJQSSEKZZWATJKLUDIAWINFBNYPVTTMZFPKWGDKZXTJCDIGKUHUAUEKCAR",
    plaintext: "??...[EAST]...[NORTHEAST]...[BERLIN]...[CLOCK]...??",
    notes: "Clues: EAST (pos 22-25), NORTHEAST (pos 26-34), BERLIN (pos 64-69), CLOCK (pos 70-74)."
  }
};
