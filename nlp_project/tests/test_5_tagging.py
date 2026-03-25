import pytest

spacy = pytest.importorskip("spacy")

from nlp_pipeline.tagging import named_entities, pos_tag_text


@pytest.fixture(scope="module")
def has_spacy_model() -> bool:
    try:
        spacy.load("en_core_web_sm")
        return True
    except OSError:
        return False


def test_pos_tagging_invariants(has_spacy_model: bool) -> None:
    if not has_spacy_model:
        pytest.skip("spaCy model en_core_web_sm not installed")

    tags = dict(pos_tag_text("Cricket is popular in England."))
    assert "Cricket" in tags
    assert tags["Cricket"] in {"NOUN", "PROPN"}


def test_ner_invariants(has_spacy_model: bool) -> None:
    if not has_spacy_model:
        pytest.skip("spaCy model en_core_web_sm not installed")

    entities = dict(named_entities("Cricket is popular in England."))
    assert "England" in entities
    assert entities["England"] in {"GPE", "LOC"}
