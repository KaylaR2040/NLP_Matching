from nlp_pipeline.segmentation import segment_sentences


def test_sentence_segmentation_boundaries() -> None:
    text = "Hello world. How are you? I am fine!"
    sentences = segment_sentences(text)

    assert len(sentences) == 3
    assert sentences[0] == "Hello world."
    assert sentences[1] == "How are you?"
    assert sentences[2] == "I am fine!"
