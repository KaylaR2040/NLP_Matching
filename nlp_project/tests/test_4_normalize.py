from nlp_pipeline.normalize import lemmatize_text, stem_tokens


def test_stemming_is_deterministic() -> None:
    tokens = ["running", "played", "cars"]
    first = stem_tokens(tokens)
    second = stem_tokens(tokens)

    assert first == second


def test_lemmatization_produces_non_empty_output() -> None:
    lemmas = lemmatize_text("The striped bats are hanging on their feet for best")

    assert len(lemmas) > 0
    assert all(isinstance(item, str) and item for item in lemmas)
