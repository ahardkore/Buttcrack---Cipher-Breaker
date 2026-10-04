"""Named language-signal providers; scores remain separate and explainable."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    name: str
    value: float
    explanation: str


class MonogramScore:
    name = "MonogramScore"

    def score(self, text):
        t = "".join(c for c in text.upper() if c.isalpha())
        n = len(t)
        counts = Counter(t)
        value = sum(v * (v - 1) for v in counts.values()) / (n * (n - 1)) if n > 1 else 0.0
        return Score(self.name, value, "index of coincidence over normalized letters")


class BigramScore:
    name = "BigramScore"

    def score(self, text):
        t = "".join(c for c in text.upper() if c.isalpha())
        common = ("TH", "HE", "IN", "ER", "AN", "RE", "ON", "AT")
        hits = sum(t.count(x) for x in common)
        return Score(self.name, hits / max(1, len(t) - 1), "count of common English bigrams")


class TrigramScore:
    name = "TrigramScore"

    def score(self, text):
        t = "".join(c for c in text.upper() if c.isalpha())
        common = ("THE", "AND", "ING", "ION", "HER", "ERE", "ENT")
        hits = sum(t.count(x) for x in common)
        return Score(self.name, hits / max(1, len(t) - 2), "count of common English trigrams")


class QuadgramScore:
    name = "QuadgramScore"

    def score(self, text):
        t = "".join(c for c in text.upper() if c.isalpha())
        common = ("TION", "THER", "WITH", "HERE", "OULD", "IGHT")
        hits = sum(t.count(x) for x in common)
        return Score(self.name, hits / max(1, len(t) - 3), "count of common English quadgrams")


class DictionaryCoverage:
    name = "DictionaryCoverage"

    def score(self, text):
        words = [x for x in text.upper().split() if x]
        common = {"THE", "AND", "OF", "TO", "IN", "IS", "A", "THAT", "WITH", "FOR"}
        value = sum(w in common for w in words) / len(words) if words else 0.0
        return Score(self.name, value, "fraction of whitespace-delimited words in a small common-word set")


class LanguageDetector:
    name = "LanguageDetector"

    def score(self, text):
        return Score(self.name, 0.0, "language detection is unavailable without a trained model; no claim made")


class RandomControl:
    name = "RandomControl"

    def score(self, text):
        return Score(self.name, 0.0, "control baseline must be generated for the same length and alphabet")


PROVIDERS = (
    MonogramScore,
    BigramScore,
    TrigramScore,
    QuadgramScore,
    DictionaryCoverage,
    LanguageDetector,
    RandomControl,
)


def score_all(text):
    return [provider().score(text) for provider in PROVIDERS]
