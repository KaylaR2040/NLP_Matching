# NLP Project

A stage-based NLP pipeline with:

1. Data Preparation Stage
   - Sentence segmentation
   - Tokenization
   - Stop-word removal
2. AI Prepping Stage
   - Optional stemming
   - Lemmatization
   - POS tagging
   - NER
3. AI Training Stage
   - TF-IDF vectorization
   - TensorFlow/Keras baseline classifier

## Install

```bash
pip install -e .
python -m spacy download en_core_web_sm
```

## Run tests

```bash
pytest -q
```

## Debugging Import Hangs

If a notebook appears to freeze on:

```python
from nlp_pipeline.segmentation import segment_sentences
```

use the following diagnostics from `nlp_project/`:

```bash
python -X importtime -c "from nlp_pipeline.segmentation import segment_sentences"
python -v -c "from nlp_pipeline.segmentation import segment_sentences"
python ../tools/diagnose_import_hang.py
```

### Findings and root cause

1. `nlp_pipeline/__init__.py` previously imported optional ML modules (`vectorize`, `pipeline`, `tf_model`) at package import time.
2. That eager import pulled in `sklearn`/`numpy` during `from nlp_pipeline.segmentation ...`, which can look like a hang in Jupyter on first import.
3. `segmentation.py` itself does not load large spaCy models at import time; it uses lazy sentencizer creation (`spacy.blank('en')`) inside a cached helper.
4. TensorFlow can also be expensive if imported eagerly, so `tf_model.py` now imports TensorFlow lazily inside functions.
5. No circular import loop was found in the current module graph after the package init was minimized.

### Fix rationale

- `nlp_pipeline/__init__.py` is now minimal and performs no submodule imports.
- Expensive setup (spaCy pipeline build, TF import/model creation) is lazy and function-scoped.
- `tests/test_0_import_speed.py` runs imports in subprocesses with timeout and speed checks to prevent regressions.

## Example usage

```python
from nlp_pipeline.pipeline import NLPPipeline

pipeline = NLPPipeline(use_stemming=False)

text = "Cricket is popular in England. Many people enjoy watching it."
processed = pipeline.preprocess(text)
print(processed["sentences"])
print(processed["entities"])

train_texts = [
    "great cricket match tonight",
    "team played excellent football",
    "stocks crashed in market trading",
    "investors expect heavy losses",
]
train_labels = ["sports", "sports", "finance", "finance"]

pipeline.train_classifier(train_texts, train_labels)
predictions = pipeline.predict_labels(["cricket team won", "market losses continue"])
print(predictions)
```
