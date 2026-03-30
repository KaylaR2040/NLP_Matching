# =============================================================================
# File: main.py
# Purpose: Load survey data, encode free-text, run weighted similarity matching,
#          honor admin overrides (blacklist/locks), and print a quick summary.
# =============================================================================

from pathlib import Path
import json
import re

from csv_parse import parse_mentor_csv, parse_mentee_csv
from direct_match import build_ranked_pairs, greedy_assign
from filters import apply_filters
from nlp_ai_prep import attach_embeddings

BASE_DIR = Path(__file__).resolve().parent

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "with",
    "was", "were", "will", "would", "you", "your", "i", "me", "my", "we", "our",
}


def segment_sentences(text: str):
    """Split text into sentences with a lightweight regex."""
    clean = (text or "").strip()
    if not clean:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]


def tokenize_text(text: str):
    """Split text into word and punctuation tokens."""
    return re.findall(r"\w+(?:'\w+)?|[^\w\s]", text or "")


def remove_stopwords(tokens):
    """Remove common stop words while preserving content tokens."""
    return [token for token in tokens if token.lower() not in STOP_WORDS]


def stem_tokens(tokens):
    """Apply a deterministic lightweight stemming fallback."""
    stems = []
    for token in tokens:
        lowered = token.lower()
        for suffix in ("ingly", "edly", "ing", "ed", "ly", "es", "s"):
            if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
                lowered = lowered[: -len(suffix)]
                break
        stems.append(lowered)
    return stems


def lemmatize_text(text: str):
    """Apply a simple lowercase lemma fallback for notebook-style preprocessing."""
    return [token.lower() for token in tokenize_text(text) if token.strip()]


def pos_tag_text(text: str):
    """Attach coarse fallback POS tags based on token shape."""
    tags = []
    for token in tokenize_text(text):
        if token.isalpha() and token[:1].isupper():
            pos = "PROPN"
        elif token.endswith("ing"):
            pos = "VERB"
        elif token.isalpha():
            pos = "NOUN"
        else:
            pos = "PUNCT"
        tags.append((token, pos))
    return tags


def named_entities(text: str):
    """Detect simple title-cased entities for CLI visibility."""
    entities = []
    for token in tokenize_text(text):
        if token.isalpha() and token[:1].isupper():
            entities.append((token, "PROPN"))
    return entities


def load_overrides(path: Path):
    """Load blacklist/locks file. Returns (blacklist_set, locked_pairs)."""
    if not path.exists():
        return set(), []
    with path.open() as f:
        data = json.load(f)
    blacklist = {(item[0], item[1]) for item in data.get("blacklist", [])}
    locks = [(item[0], item[1]) for item in data.get("locks", [])]
    return blacklist, locks


def attach_nlp_features(people, use_stemming: bool = False):
    """Run notebook-style NLP preprocessing and attach the results to each person."""
    for person in people:
        raw_text = getattr(person, "about", "") or ""

        # Step 1.1: Split the free-text profile into sentences.
        person.nlp_sentences = segment_sentences(raw_text)

        # Step 1.2: Break the profile text into word and punctuation tokens.
        person.nlp_tokens = tokenize_text(raw_text)

        # Step 1.3: Remove common stop words before deeper NLP analysis.
        person.nlp_filtered_tokens = remove_stopwords(person.nlp_tokens)

        # Step 2.1: Optionally stem tokens to shorter root-like forms.
        person.nlp_stemmed_tokens = (
            stem_tokens(person.nlp_filtered_tokens) if use_stemming else list(person.nlp_filtered_tokens)
        )

        # Step 2.2: Lemmatize tokens so related word forms map to a shared base.
        person.nlp_lemmatized_tokens = lemmatize_text(" ".join(person.nlp_filtered_tokens))

        # Step 2.3: Tag each token with its part of speech.
        person.nlp_pos_tags = pos_tag_text(raw_text)

        # Step 2.4: Detect named entities that may add semantic context.
        person.nlp_entities = named_entities(raw_text)

        # Step 3.0: Build the cleaned text string used by the embedding-based matcher.
        final_tokens = person.nlp_stemmed_tokens if use_stemming else person.nlp_lemmatized_tokens
        person.nlp_text = " ".join(token for token in final_tokens if str(token).strip())


def print_nlp_preview(people, label: str):
    """Print one compact NLP preview so the processing steps are visible in CLI runs."""
    if not people:
        return

    person = people[0]
    print(f"\n=== NLP Preview: {label} ===")
    print(f"Name: {person.name}")
    print(f"Raw About: {person.about or '[empty]'}")
    print(f"Sentences: {person.nlp_sentences}")
    print(f"Tokens: {person.nlp_tokens[:12]}")
    print(f"Filtered Tokens: {person.nlp_filtered_tokens[:12]}")
    print(f"Lemmas: {person.nlp_lemmatized_tokens[:12]}")
    print(f"POS Tags: {person.nlp_pos_tags[:8]}")
    print(f"Entities: {person.nlp_entities}")
    print(f"NLP Text: {person.nlp_text or '[empty]'}")


def run_matching_cycle(mentee_data, mentor_data, overrides_path: Path):
    """Core workflow used by CLI and (future) UI reruns."""
    blacklist, locks = load_overrides(overrides_path)

    # Step 0: Apply hard filters before scoring candidate matches.
    filtered_mentees, filtered_mentors = apply_filters(mentee_data, mentor_data)

    # Step 1: Run the notebook-style NLP preprocessing pipeline on mentees.
    attach_nlp_features(filtered_mentees)

    # Step 2: Run the notebook-style NLP preprocessing pipeline on mentors.
    attach_nlp_features(filtered_mentors)

    # Step 3: Encode the cleaned NLP text into vectors for semantic matching.
    attach_embeddings(filtered_mentees)
    attach_embeddings(filtered_mentors)

    # Step 4: Build ranked pairs while skipping any blacklisted combinations.
    ranked_pairs = build_ranked_pairs(filtered_mentees, filtered_mentors, prohibited=blacklist)

    # Step 5: Greedily assign mentors to mentees while honoring locked pairs.
    assignments = greedy_assign(ranked_pairs, locked=locks)

    return {
        "ranked_pairs": ranked_pairs,
        "assignments": assignments,
        "blacklist": blacklist,
        "locks": locks,
        "filtered_mentees": filtered_mentees,
        "filtered_mentors": filtered_mentors,
    }


def main():
    # CSV Default Locations (relative to this file)
    base_dir = BASE_DIR
    mentee_csv_path = base_dir / "data/sample_mentees.csv"
    mentor_csv_path = base_dir / "data/sample_mentors.csv"
    overrides_path = base_dir / "overrides.json"

    mentees = parse_mentee_csv(mentee_csv_path)
    mentors = parse_mentor_csv(mentor_csv_path)

    results = run_matching_cycle(mentees, mentors, overrides_path)
    ranked_pairs = results["ranked_pairs"]
    assignments = results["assignments"]

    # Step 6: Show one mentee NLP example so each preprocessing stage is visible.
    print_nlp_preview(results["filtered_mentees"], "Filtered Mentee")

    # Step 7: Show one mentor NLP example so the same pipeline is visible on both sides.
    print_nlp_preview(results["filtered_mentors"], "Filtered Mentor")

    print("\n=== Summary ===")
    print(f"Mentees parsed: {len(mentees)}")
    print(f"Mentees after filter: {len(results['filtered_mentees'])}")
    print(f"Mentors parsed: {len(mentors)}")
    print(f"Ranked pairs (after blacklist): {len(ranked_pairs)}")
    print(f"Assignments (with locks): {len(assignments)}")

    print("\nTop 3 Ranked Mentor–Mentee Matches\n" + "=" * 36)

    for rank, pair in enumerate(ranked_pairs[:3], start=1):
        print(f"\nMatch #{rank}")
        print("-" * 36)

        print("Mentee")
        print(f"  Name : {pair['mentee_name']}")
        print(f"  Email: {pair['mentee_email']}")

        print("\nMentor")
        print(f"  Name : {pair['mentor_name']}")
        print(f"  Email: {pair['mentor_email']}")

        print("\nScoring Breakdown")
        print(f"  Match % : {pair['match_score']*100:5.2f}%")

        weights = pair.get("weights", {})
        scores = pair.get("scores", {})
        for key in ["industry", "degree", "interest", "organization", "nlp"]:
            w = weights.get(key, 1.0 if key != "nlp" else 1.0)
            s = scores.get(key, 0.0)
            label = key.upper() if key == "nlp" else key.title()
            print(f"  - {label:<15} score={s:4.2f}  weight={w:3.1f}")

        print("-" * 36)


if __name__ == "__main__":
    main()
