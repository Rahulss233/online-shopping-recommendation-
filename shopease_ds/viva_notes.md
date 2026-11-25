# Viva Notes — Online Shopping Recommendation System
## Simple explanations for college viva / project presentation

---

### 1. What is a Recommendation System?

A recommendation system is software that suggests items to a user based on some logic.

**Real-world examples:**
- YouTube suggests videos to watch next.
- Amazon shows "Customers who bought this also bought..."
- Netflix recommends movies based on what you watched.

**In our project:**
When a user opens a product like "Classic White Shirt", our system automatically suggests similar products like "Blue Denim Shirt" or "Polo T-Shirt" in a "Recommended Products" section.

---

### 2. What is Content-Based Filtering?

Content-based filtering recommends products **based on the properties of the product itself**, not based on what other users bought.

**Simple analogy:**
If you like action movies with fast cars, the system recommends other action movies with fast cars — because the *content* (genre, theme) is similar.

**In our project:**
We use the product's **name**, **category**, and **description** as content. A "Cotton Kurtha" is recommended near "Silk Kurtha" because their descriptions and category are similar.

**We did NOT use:**
- Customer purchase history (we don't have enough of it)
- Customer ratings (not in our database)
- What other users bought (that would be collaborative filtering)

---

### 3. What is TF-IDF?

TF-IDF stands for **Term Frequency – Inverse Document Frequency**.

It converts text into numbers so a computer can compare them.

**TF (Term Frequency):**
How often a word appears in ONE product's description.
Example: The word "shirt" appears 3 times in "Classic White Shirt" → high TF.

**IDF (Inverse Document Frequency):**
How rare a word is across ALL products.
Example: "shirt" appears in 5 out of 12 products → it gets a LOWER weight.
Example: "blazer" appears in only 1 product → it gets a HIGHER weight.

**Final TF-IDF score = TF × IDF**
Common words are down-weighted. Distinctive words get higher importance.

**In our project:**
We call `TfidfVectorizer` from Scikit-learn. It converts each product's feature string into a vector of numbers.

```
"Classic White Shirt" → [0.0, 0.45, 0.0, 0.72, 0.0, 0.31, ...]
"Blue Denim Shirt"    → [0.0, 0.38, 0.0, 0.61, 0.0, 0.29, ...]
```

Each number represents the TF-IDF weight of one word.

---

### 4. What is Cosine Similarity?

Cosine similarity measures how similar two vectors are by measuring the **angle between them**.

- If the angle is 0° → similarity = 1.0 (identical)
- If the angle is 90° → similarity = 0.0 (completely different)

**Simple analogy:**
Imagine two arrows pointing in similar directions = similar products.
Two arrows pointing in opposite directions = very different products.

**Formula:**
```
cosine_similarity(A, B) = (A · B) / (|A| × |B|)
```
Where A · B is the dot product of the two vectors.

**In our project:**
After TF-IDF, each product is a vector. We compute the similarity between every pair of products. The product with the highest similarity score (closest to 1.0) is the best recommendation.

**Example from our project:**
- Classic White Shirt vs Blue Denim Shirt → 0.534 (both are shirts, similar words)
- Classic White Shirt vs Winter Coat → 0.02 (very different products)

---

### 5. Why are Pandas and NumPy used?

**Pandas:**
- Loads the SQLite database into a DataFrame (like an Excel table in Python).
- Handles missing values (`fillna`).
- Groups products by category (`groupby`).
- Cleans and transforms data before the algorithm runs.

**NumPy:**
- Used internally by Pandas and Scikit-learn for fast numerical computations.
- Our TF-IDF matrix is a NumPy/SciPy sparse matrix.
- We use `numpy.isnan()` to detect missing values.

**In simple terms:**
Pandas organises the data. NumPy does the fast math.

---

### 6. What is Scikit-learn?

Scikit-learn (sklearn) is a Python library for machine learning.

**What we use from it:**
1. `TfidfVectorizer` — converts text to TF-IDF numeric vectors.
2. `cosine_similarity` — computes the similarity between all product vectors.

**Example code from our project:**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer   = TfidfVectorizer(stop_words='english', ngram_range=(1,2))
tfidf_matrix = vectorizer.fit_transform(df['features'])
sim_matrix   = cosine_similarity(tfidf_matrix, tfidf_matrix)
```

---

### 7. How does the Recommendation Algorithm Work? (Step by step)

**Step 1 — Load products from the database:**
```python
df = pd.read_sql_query("SELECT * FROM products", conn)
```

**Step 2 — Build a feature string for each product:**
```
"Classic White Shirt"  +  "Shirt Shirt Shirt"  +  "Premium cotton formal shirt"
→ "classic white shirt shirt shirt shirt premium cotton formal shirt"
```
Category is repeated 3 times to give it more weight.

**Step 3 — TF-IDF vectorization:**
Convert each product's feature string into a row of numbers.
Result: a matrix with 12 rows (products) × N columns (unique words).

**Step 4 — Cosine similarity:**
Compare every product with every other product.
Result: a 12×12 matrix of scores.

**Step 5 — Get recommendations:**
For product #1 (Classic White Shirt), read row 1 of the matrix.
Sort scores from highest to lowest.
Skip the product itself.
Return the top 6.

---

### 8. Why is SQLite used?

SQLite is a lightweight database that stores everything in a single file (`ecommerce.db`).

**Advantages for our project:**
- No separate server needed (unlike MySQL or PostgreSQL).
- Works directly in Python with the built-in `sqlite3` module.
- Perfect for small-to-medium projects and academic demonstrations.
- Easy to share — just copy the `.db` file.

**In our project:**
Products, orders, customers, and cart data are all stored in `ecommerce.db`.
Pandas reads from it using `pd.read_sql_query()`.

---

### 9. How does Flask connect the Model to the Website?

Flask is a Python web framework. It connects the recommendation algorithm (Python) with the HTML templates (user interface).

**Flow:**
```
User opens product page
        ↓
Flask route: /product/<id>  (in app.py)
        ↓
Call: get_recommendations(product_id)  (from recommendation.py)
        ↓
Returns: list of recommended products
        ↓
Flask passes list to: product_detail.html  (render_template)
        ↓
HTML displays the recommended product cards
```

**Code example:**
```python
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    recommendations = get_recommendations(product_id, n=6)
    return render_template('product_detail.html',
                           product=product,
                           recommendations=recommendations)
```

---

### 10. Why is Matplotlib used?

Matplotlib is a Python library for creating charts and graphs.

**In our project, we generate 4 charts:**
1. **Category Distribution** — bar chart of products per category.
2. **Price Distribution** — histogram showing price spread.
3. **Stock Analysis** — horizontal bar chart, colour-coded by stock level.
4. **Similarity Scores** — bar chart showing cosine scores for a product.

**Important: Non-interactive mode**
We use `matplotlib.use('Agg')` which saves charts as PNG files instead of opening a window. This is required for server-side use.

**Charts are saved to:**
`static/charts/` folder and served by Flask as normal image files.

---

### 11. What happens when a New Product is added?

The admin adds a product through the Admin Panel.
The product is inserted into the SQLite `products` table.

**The recommendation system automatically includes the new product:**
- There is no manual retraining step needed.
- Every time `get_recommendations()` is called, it freshly loads all products from the database and recomputes the TF-IDF matrix.
- The new product is immediately part of the recommendation pool.

**Limitation:**
For very large catalogues (1000+ products), recomputing on every request would be slow. In that case, caching the matrix would be a future improvement.

---

### 12. What are the Limitations of the System?

| Limitation | Explanation |
|------------|-------------|
| No personalization | Recommendations are based on product content, not user history |
| Cold start | Fewer than 2 products → no recommendations generated |
| English only | TF-IDF stop-word removal works best with English text |
| No recompute caching | Matrix rebuilt on every request (fine for small catalogues) |
| Small demo catalogue | 12 products may show obvious/expected recommendations |
| No rating data | Cannot improve with customer feedback |

---

### 13. How can the Project be Improved in the Future?

1. **Collaborative Filtering** — Analyse order history: "users who bought X also bought Y".
2. **Hybrid Model** — Combine content-based + collaborative filtering for better accuracy.
3. **Caching** — Store the TF-IDF matrix in memory, rebuild only when the product catalogue changes.
4. **Click tracking** — Log which products a user views to build a browsing history.
5. **Ratings** — Add a star rating feature; include ratings in the similarity score.
6. **Real-time updates** — Use a background job to retrain the model periodically.
7. **Deep learning** — Use word embeddings (Word2Vec, BERT) instead of TF-IDF for richer text understanding.

---

## End-to-End Workflow (for Presentation)

```
1. Admin adds products (name, category, description, price, stock)
            ↓
2. Products are stored in SQLite database (ecommerce.db)
            ↓
3. User opens a product page  →  /product/1
            ↓
4. Flask calls get_recommendations(1)  in recommendation.py
            ↓
5. Pandas loads all products from SQLite into a DataFrame
            ↓
6. Text preprocessing: name + category×3 + description → "features" string
            ↓
7. TF-IDF Vectorizer converts feature strings → numeric matrix (12 × N)
            ↓
8. Cosine Similarity computes 12×12 similarity scores
            ↓
9. Scores for product #1 are sorted; top 6 are selected (excluding itself)
            ↓
10. Recommended products are passed to product_detail.html
            ↓
11. User sees "Recommended Products" section with similarity scores
            ↓
12. Admin can view charts at /admin/analysis
            ↓
13. Matplotlib generates 4 charts saved in static/charts/
            ↓
14. Charts are displayed in the admin panel as <img> tags
```

---

*Prepared for college project viva — ShopEase, 2026*
