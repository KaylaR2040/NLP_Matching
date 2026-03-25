### 1. Pre-Processing & "Hard" Filtering

Before any math happens, the system cleans the candidate pool to ensure we aren't matching people who shouldn't be in the program.

* **Data Normalization:** Converts list inputs into lowercase, stripped sets to prevent "Marketing" and "marketing" from being seen as different.
* **Experience Filter:** The `apply_filters` function currently removes any mentees who have already participated in prior mentorship, focusing resources on new participants.
* **Administrative Overrides:** The system loads a `blacklist` (combos that can never happen) and `locks` (combos that must happen) from a JSON file.

---

### 2. The "3-Level" Scoring Logic

The engine calculates a match score for every possible pair using two different mathematical approaches to ensure the match isn't just "keyword deep".

#### Level A: Categorical Overlap (Jaccard Similarity)

For structured data like **Industry**, **Major**, and **Interests**, the system uses the Jaccard formula:


$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

* **How it works:** It counts the number of shared items divided by the total unique items across both lists.
* **Why use it:** This prevents "over-use" of a mentor just because they have a long list of skills; it rewards a high *percentage* of overlap rather than just a high count.

#### Level B: Semantic (NLP & Cosine Similarity)

For the "About Me" free-text, we use the `all-MiniLM-L6-v2` transformer model.

* **Vectorization:** It converts a paragraph of text into a 384-dimensional numerical vector.
* **Cosine Similarity:** It measures the angle between the mentee’s vector and the mentor’s vector.
* **Why use it:** It recognizes that "I love coding" and "Software development is my passion" are the same thing, even though they share zero words.

#### Level C: Weighted Multi-Factor Formula

The system combines these scores into a single `match_score` using configurable weights (defaulting to 1.0).

* **The Formula:** `(Industry_Score * W1 + Degree_Score * W2 + Interest_Score * W3 + NLP_Score * 1.0) / Total_Weights`.

---

### 3. The Greedy Assignment (The Elimination Phase)

Once every possible pair has a score, the `greedy_assign` function builds the final list.

* **Step 1: Priority Seeding:** Any "Locked" pairs from the admin are assigned first and removed from the pool immediately.
* **Step 2: Global Ranking:** Every other possible pair is sorted from highest score (1.0) to lowest (0.0).
* **Step 3: The "Greedy" Loop:**
* The algorithm looks at the #1 best match in the entire dataset.
* It assigns them and then **eliminates** both that mentee and that mentor from the pool.
* It moves to the next highest score that involves people who haven't been assigned yet.


* **The Result:** This ensures that the absolute "best" matches are locked in first, preventing a scenario where a great mentor is "wasted" on a mediocre match.