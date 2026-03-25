from nlp_pipeline.tokenizing import tokenize_text


def test_tokenization_handles_punctuation_and_contractions() -> None:
    text = "I can't, won't stop."
    tokens = tokenize_text(text)

    assert "ca" in tokens or "can't" in tokens
    assert "n't" in tokens or "can't" in tokens
    assert "," in tokens
    assert "." in tokens
