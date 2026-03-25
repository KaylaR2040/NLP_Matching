from nlp_pipeline.stopwords import remove_stopwords


def test_stopword_removal_case_insensitive() -> None:
    tokens = ["This", "is", "A", "simple", "TEST"]
    filtered = remove_stopwords(tokens)

    assert "This" not in filtered
    assert "is" not in filtered
    assert "A" not in filtered
    assert "simple" in filtered
    assert "TEST" in filtered
