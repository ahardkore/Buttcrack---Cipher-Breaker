"""Generate a print-ready cryptogram puzzle book.

Produces a single self-contained HTML file with a cover, instructions, graded
puzzle pages and a solutions section. Open it in a browser and "Print to PDF"
to get a file you can sell on Gumroad, itch.io or Amazon KDP, or give away as a
lead magnet.

    python3 ventures/puzzle-packs/generate.py --puzzles 60 --seed 7

Quotations are short fragments attributed to historical figures who died before
1956 — short enough and old enough to sell without licensing concerns. The puzzles
are generated deterministically from the seed, so the same seed always yields
the same book — change the seed to produce a genuinely different volume.
"""
from __future__ import annotations

import argparse
import html
import random
import string
from datetime import date
from pathlib import Path

ALPHABET = string.ascii_uppercase

# Short quotations attributed to historical figures, all of whom died before
# 1956 and most of whom died centuries ago. Fragments this short are not
# protected as literary works in any case, but the list is kept conservative
# deliberately: this book is meant to be sellable without a lawyer.
QUOTES: list[tuple[str, str]] = [
    ("The only thing we have to fear is fear itself", "Franklin D. Roosevelt"),
    ("I think therefore I am", "Rene Descartes"),
    ("Knowledge is power", "Francis Bacon"),
    ("To be or not to be that is the question", "William Shakespeare"),
    ("All the world is a stage and all the men and women merely players", "William Shakespeare"),
    ("The unexamined life is not worth living", "Socrates"),
    ("I came I saw I conquered", "Julius Caesar"),
    ("Give me liberty or give me death", "Patrick Henry"),
    ("A journey of a thousand miles begins with a single step", "Lao Tzu"),
    ("Better to remain silent and be thought a fool than to speak and remove all doubt", "Abraham Lincoln"),
    ("The pen is mightier than the sword", "Edward Bulwer Lytton"),
    ("Genius is one percent inspiration and ninety nine percent perspiration", "Thomas Edison"),
    ("In the middle of difficulty lies opportunity", "Albert Einstein"),
    ("Imagination is more important than knowledge", "Albert Einstein"),
    ("That which does not kill us makes us stronger", "Friedrich Nietzsche"),
    ("The mass of men lead lives of quiet desperation", "Henry David Thoreau"),
    ("Beware the barrenness of a busy life", "Socrates"),
    ("It is not death that a man should fear but never beginning to live", "Marcus Aurelius"),
    ("You have power over your mind not outside events", "Marcus Aurelius"),
    ("We suffer more often in imagination than in reality", "Seneca"),
    ("Luck is what happens when preparation meets opportunity", "Seneca"),
    ("How much longer will you wait before you demand the best of yourself", "Epictetus"),
    ("Nothing in life is to be feared it is only to be understood", "Marie Curie"),
    ("The important thing is not to stop questioning", "Albert Einstein"),
    ("There is nothing permanent except change", "Heraclitus"),
    ("No man ever steps in the same river twice", "Heraclitus"),
    ("Happiness depends upon ourselves", "Aristotle"),
    ("We are what we repeatedly do excellence then is a habit", "Aristotle"),
    ("The whole is greater than the sum of its parts", "Aristotle"),
    ("Man is by nature a political animal", "Aristotle"),
    ("The greatest wealth is to live content with little", "Plato"),
    ("Wise men speak because they have something to say", "Plato"),
    ("Necessity is the mother of invention", "Plato"),
    ("Do not go where the path may lead go instead where there is no path", "Ralph Waldo Emerson"),
    ("To be yourself in a world that is constantly trying to make you something else", "Ralph Waldo Emerson"),
    ("Every artist was first an amateur", "Ralph Waldo Emerson"),
    ("Life is really simple but we insist on making it complicated", "Confucius"),
    ("It does not matter how slowly you go so long as you do not stop", "Confucius"),
    ("Our greatest glory is not in never falling but in rising every time we fall", "Confucius"),
    ("Everything has beauty but not everyone sees it", "Confucius"),
    ("The superior man is modest in his speech but exceeds in his actions", "Confucius"),
    ("Hope is the thing with feathers that perches in the soul", "Emily Dickinson"),
    ("I dwell in possibility", "Emily Dickinson"),
    ("Tell all the truth but tell it slant", "Emily Dickinson"),
    ("I am large I contain multitudes", "Walt Whitman"),
    ("Keep your face always toward the sunshine and shadows will fall behind you", "Walt Whitman"),
    ("Water water everywhere nor any drop to drink", "Samuel Taylor Coleridge"),
    ("A thing of beauty is a joy forever", "John Keats"),
    ("Beauty is truth truth beauty that is all ye know on earth", "John Keats"),
    ("If winter comes can spring be far behind", "Percy Bysshe Shelley"),
    ("Look on my works ye mighty and despair", "Percy Bysshe Shelley"),
    ("She walks in beauty like the night of cloudless climes and starry skies", "Lord Byron"),
    ("It is a truth universally acknowledged that a single man in possession of a good fortune must be in want of a wife", "Jane Austen"),
    ("There is no charm equal to tenderness of heart", "Jane Austen"),
    ("It was the best of times it was the worst of times", "Charles Dickens"),
    ("No one is useless in this world who lightens the burden of another", "Charles Dickens"),
    ("The world is a book and those who do not travel read only one page", "Saint Augustine"),
    ("Patience is bitter but its fruit is sweet", "Aristotle"),
    ("Call me Ishmael", "Herman Melville"),
    ("Whatever you are be a good one", "Abraham Lincoln"),
    ("I have not failed I have just found ten thousand ways that will not work", "Thomas Edison"),
    ("A room without books is like a body without a soul", "Marcus Tullius Cicero"),
    ("Any fool can know the point is to understand", "Albert Einstein"),
    ("Science is organised knowledge wisdom is organised life", "Immanuel Kant"),
    ("Act only according to that maxim whereby you can will that it become a universal law", "Immanuel Kant"),
    ("He who has a why to live can bear almost any how", "Friedrich Nietzsche"),
    ("Without music life would be a mistake", "Friedrich Nietzsche"),
    ("There is no greatness where there is no simplicity", "Leo Tolstoy"),
    ("Everyone thinks of changing the world but no one thinks of changing himself", "Leo Tolstoy"),
    ("If you want to tell people the truth make them laugh", "Oscar Wilde"),
    ("We are all in the gutter but some of us are looking at the stars", "Oscar Wilde"),
    ("Be yourself everyone else is already taken", "Oscar Wilde"),
    ("Experience is simply the name we give our mistakes", "Oscar Wilde"),
    ("The truth is rarely pure and never simple", "Oscar Wilde"),
    ("It is a capital mistake to theorise before one has data", "Arthur Conan Doyle"),
    ("When you have eliminated the impossible whatever remains must be the truth", "Arthur Conan Doyle"),
    ("You see but you do not observe", "Arthur Conan Doyle"),
    ("The game is afoot", "Arthur Conan Doyle"),
    ("Twenty years from now you will be more disappointed by the things you did not do", "Mark Twain"),
    ("The secret of getting ahead is getting started", "Mark Twain"),
    ("Whenever you find yourself on the side of the majority it is time to pause and reflect", "Mark Twain"),
    ("Kindness is the language which the deaf can hear and the blind can see", "Mark Twain"),
    ("Courage is resistance to fear mastery of fear not absence of fear", "Mark Twain"),
    ("Do the right thing it will gratify some people and astonish the rest", "Mark Twain"),
    ("All generalisations are false including this one", "Mark Twain"),
    ("Never put off till tomorrow what may be done day after tomorrow just as well", "Mark Twain"),
    ("Education is what remains after one has forgotten what one has learned in school", "Albert Einstein"),
    ("Try not to become a man of success but rather try to become a man of value", "Albert Einstein"),
    ("Logic will get you from A to B imagination will take you everywhere", "Albert Einstein"),
    ("Insanity is doing the same thing over and over and expecting different results", "Albert Einstein"),
    ("Strive not to be a success but rather to be of value", "Albert Einstein"),
]


def random_key(rng: random.Random) -> dict[str, str]:
    """A substitution alphabet where no letter maps to itself."""
    while True:
        shuffled = list(ALPHABET)
        rng.shuffle(shuffled)
        if all(a != b for a, b in zip(ALPHABET, shuffled)):
            return dict(zip(ALPHABET, shuffled))


def encrypt(text: str, key: dict[str, str]) -> str:
    return "".join(key.get(ch, ch) for ch in text.upper())


def caesar(text: str, shift: int) -> str:
    out = []
    for ch in text.upper():
        if ch in ALPHABET:
            out.append(ALPHABET[(ALPHABET.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


def hint_for(plain: str, cipher: str, count: int, rng: random.Random) -> str:
    """Reveal `count` distinct letter mappings as a starter hint."""
    pairs = sorted({(c, p) for p, c in zip(plain.upper(), cipher) if p in ALPHABET})
    if not pairs:
        return ""
    chosen = rng.sample(pairs, min(count, len(pairs)))
    return "   ".join(f"{c} = {p}" for c, p in sorted(chosen))


def difficulty_for(index: int, total: int) -> tuple[str, int]:
    """Return (label, hint_count). The book gets harder as it goes."""
    third = max(1, total // 3)
    if index < third:
        return "Easy", 3
    if index < 2 * third:
        return "Medium", 1
    return "Hard", 0


def build(puzzles: int, seed: int, title: str) -> str:
    rng = random.Random(seed)
    pool = QUOTES[:]
    rng.shuffle(pool)
    if puzzles > len(pool):
        raise SystemExit(f"only {len(pool)} quotations available; ask for fewer puzzles")
    chosen = pool[:puzzles]

    pages, solutions = [], []
    for i, (quote, author) in enumerate(chosen, start=1):
        label, hints = difficulty_for(i - 1, puzzles)
        # Every fifth puzzle is a Caesar shift for variety; the rest are
        # full substitutions, which is what cryptogram solvers expect.
        if i % 5 == 0:
            shift = rng.randint(1, 25)
            ct = caesar(quote, shift)
            ct_author = caesar(author, shift)
            kind = "Caesar shift"
            hint_line = f"Hint: this one is a simple letter rotation." if hints else ""
            answer_key = f"shift of {shift}"
        else:
            key = random_key(rng)
            ct = encrypt(quote, key)
            ct_author = encrypt(author, key)
            kind = "Cryptogram"
            hint_line = f"Hint: {hint_for(quote, ct, hints, rng)}" if hints else ""
            answer_key = "substitution alphabet"

        words = "".join(
            f'<span class="w">{"".join(f"<span class=c>{html.escape(ch)}</span>" for ch in word)}</span>'
            for word in ct.split(" ")
        )
        pages.append(f"""  <section class="puzzle">
    <div class="phead"><span class="pnum">Puzzle {i}</span>
      <span class="ptype">{kind} · {label}</span></div>
    <div class="ct">{words}</div>
    <div class="author">— {html.escape(ct_author)}</div>
    {f'<div class="hint">{html.escape(hint_line)}</div>' if hint_line else ''}
  </section>""")
        solutions.append(
            f'<div class="sol"><b>{i}.</b> {html.escape(quote.capitalize())} '
            f'<i>— {html.escape(author)}</i> <span class="skey">({answer_key})</span></div>'
        )

    today = date.today().strftime("%B %Y")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  @page {{ size: letter; margin: 18mm 16mm; }}
  body {{ font: 12pt/1.5 Georgia, "Times New Roman", serif; color: #111; margin: 0; }}
  .cover {{ text-align: center; padding-top: 55mm; page-break-after: always; }}
  .cover h1 {{ font-size: 34pt; margin: 0 0 8mm; letter-spacing: -0.5pt; }}
  .cover .sub {{ font-size: 14pt; color: #444; margin-bottom: 30mm; }}
  .cover .meta {{ font-size: 10pt; color: #777; }}
  .intro {{ page-break-after: always; }}
  h2 {{ font-size: 16pt; margin: 0 0 4mm; }}
  .intro p, .intro li {{ font-size: 11pt; }}
  .puzzle {{ page-break-inside: avoid; margin-bottom: 11mm; padding-bottom: 5mm;
             border-bottom: 1px solid #ddd; }}
  .phead {{ display: flex; justify-content: space-between; align-items: baseline;
            margin-bottom: 4mm; }}
  .pnum {{ font-weight: bold; font-size: 12pt; }}
  .ptype {{ font-size: 9pt; color: #777; text-transform: uppercase;
            letter-spacing: 0.6pt; }}
  .ct {{ font-family: "Courier New", monospace; font-size: 13pt; line-height: 2.6; }}
  .w {{ display: inline-block; margin-right: 3.5mm; white-space: nowrap; }}
  .c {{ display: inline-block; width: 6.2mm; text-align: center;
        border-bottom: 1px solid #999; margin-right: 0.4mm; }}
  .author {{ font-family: "Courier New", monospace; font-size: 11pt; color: #555;
             text-align: right; margin-top: 2mm; }}
  .hint {{ font-size: 9.5pt; color: #666; margin-top: 3mm; font-style: italic; }}
  .solutions {{ page-break-before: always; }}
  .sol {{ font-size: 10pt; margin-bottom: 2.5mm; }}
  .skey {{ color: #888; font-size: 9pt; }}
  footer {{ page-break-before: always; font-size: 10pt; color: #555; }}
</style>
</head>
<body>

<div class="cover">
  <h1>{html.escape(title)}</h1>
  <p class="sub">{puzzles} classic cryptograms, graded easy to hard<br>with full solutions</p>
  <p class="meta">Volume seed {seed} · {today}</p>
</div>

<div class="intro">
  <h2>How to solve a cryptogram</h2>
  <p>Every puzzle in this book is a quotation in which each letter has been replaced by a
  different letter, consistently throughout. <b>A</b> might become <b>Q</b> everywhere it
  appears. Your job is to work backwards to the original words. Spaces and word lengths are
  preserved, and those are your best clues.</p>
  <ol>
    <li><b>Start with one-letter words.</b> In English they are almost always
    <b>A</b> or <b>I</b>.</li>
    <li><b>Attack the three-letter words.</b> The most common by far is <b>THE</b>. If a
    three-letter pattern appears repeatedly, try it — that single guess often gives you the
    three most useful letters in the puzzle at once.</li>
    <li><b>Look for doubled letters.</b> Doubles at the end of a word are usually
    <b>LL</b>, <b>SS</b>, <b>EE</b> or <b>OO</b>.</li>
    <li><b>Use word endings.</b> <b>ING</b>, <b>ED</b>, <b>TION</b> and <b>LY</b> are
    everywhere, and each one you spot confirms several letters.</li>
    <li><b>Count frequencies.</b> Across English text the order runs roughly
    <b>E T A O I N S H R D L U</b>. The most repeated symbol in a long puzzle is very likely
    <b>E</b>.</li>
    <li><b>Pencil, not pen.</b> Guesses that collapse three words later are part of the
    process.</li>
  </ol>
  <p>Puzzles marked <b>Easy</b> come with a few letters given. <b>Medium</b> gives you one.
  <b>Hard</b> gives you nothing but the text. Every fifth puzzle is a simple rotation cipher,
  where the whole alphabet has been shifted by the same amount — once you crack one letter of
  those, you have cracked them all.</p>
  <p>Solutions begin after the final puzzle. Good luck.</p>
</div>

{chr(10).join(pages)}

<div class="solutions">
  <h2>Solutions</h2>
  {chr(10).join(solutions)}
</div>

<footer>
  <p>Puzzles generated with <b>buttcrack</b>, an open-source automatic cipher breaker.
  Quotations are short fragments attributed to historical figures.</p>
  <p>Enjoyed these? The generator that made this book is free and open source — you can
  produce endless variations of it yourself.</p>
</footer>

</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--puzzles", type=int, default=60, help="how many puzzles (max 100)")
    ap.add_argument("--seed", type=int, default=1, help="change for a different volume")
    ap.add_argument("--title", default="The Cryptogram Collection")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    out = args.out or Path(__file__).with_name(f"cryptogram-pack-seed{args.seed}.html")
    out.write_text(build(args.puzzles, args.seed, args.title))
    print(f"wrote {out}  ({args.puzzles} puzzles, seed {args.seed})")
    print("Open it in a browser and use Print → Save as PDF to get a sellable file.")


if __name__ == "__main__":
    main()
