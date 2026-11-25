# ============================================================
# recommendation.py
# Online Shopping Recommendation System
# Algorithm: Content-Based Filtering
# Technique: TF-IDF Vectorization + Cosine Similarity
# ============================================================
#
# HOW IT WORKS (simple explanation):
#
#   1. Load all products from SQLite into a Pandas DataFrame.
#   2. Combine each product's name, category, description into
#      one text string called "features".
#   3. Convert those strings into numbers using TF-IDF:
#        - Words that appear in many products get LOW weight.
#        - Rare/distinctive words get HIGH weight.
#   4. Measure similarity between products using Cosine Similarity:
#        - 0.0  = completely different
#        - 1.0  = identical
#   5. For a given product, rank all other products by their
#      similarity score and return the top N.
#
# ============================================================

import os
import sqlite3
import re

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ── Resolve DB path relative to this file so the module works
# ── regardless of which directory the process is started from.
_HERE    = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(_HERE, 'ecommerce.db')


# ============================================================
# SECTION 1 — DATA LOADING
# Read the products table from SQLite into a Pandas DataFrame.
# ============================================================

def load_products_df():
    """
    Connect to SQLite and return the products table as a DataFrame.
    Returns an empty DataFrame with the correct columns on any error.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Read every column we need in one query
        df = pd.read_sql_query(
            "SELECT id, name, price, image, description, category, stock "
            "FROM products",
            conn
        )
        conn.close()
        return df
    except Exception as e:
        print(f"[Recommendation] DB load error: {e}")
        return pd.DataFrame(
            columns=['id', 'name', 'price', 'image',
                     'description', 'category', 'stock']
        )


# ============================================================
# SECTION 2 — TEXT PREPROCESSING
# Clean individual text fields and combine them into one
# "features" string per product for TF-IDF.
# ============================================================

def _clean(text):
    """
    Lowercase a string, remove punctuation, collapse whitespace.
    Returns '' for None / NaN values.

    Example:
        "Classic White Shirt!"  →  "classic white shirt"
        None                    →  ""
    """
    if not text or (isinstance(text, float) and np.isnan(text)):
        return ''
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)   # remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()     # collapse spaces
    return text


def _build_features(row):
    """
    Combine name, category (×3 for emphasis), and description
    into a single string that TF-IDF will process.

    Category is repeated 3 times so that two products in the
    SAME category always score higher than products that merely
    share a word in their names.

    Example output for "Classic White Shirt":
        "classic white shirt shirt shirt shirt premium cotton formal shirt"
    """
    name  = _clean(row.get('name',        ''))
    cat   = _clean(row.get('category',    ''))
    desc  = _clean(row.get('description', ''))
    # Repeat category 3 times to boost intra-category similarity
    return f"{name} {cat} {cat} {cat} {desc}".strip()


def preprocess_products(df):
    """
    Clean the products DataFrame:
      • Drop duplicate product IDs.
      • Fill NaN text fields with ''.
      • Build the 'features' column for TF-IDF.

    Returns the cleaned DataFrame (original is NOT modified).
    """
    if df.empty:
        return df

    df = df.drop_duplicates(subset='id').copy()

    # Fill missing text fields
    for col in ('name', 'category', 'description', 'image'):
        df[col] = df[col].fillna('')

    # Build combined feature string for every product
    df['features'] = df.apply(_build_features, axis=1)

    return df.reset_index(drop=True)


# ============================================================
# SECTION 3 — TF-IDF VECTORIZATION
# Convert the "features" strings into a numeric matrix.
# ============================================================

def build_tfidf_matrix(df):
    """
    Fit a TF-IDF vectorizer on df['features'] and return
    (tfidf_matrix, vectorizer).

    Returns (None, None) when fewer than 2 products exist,
    because cosine similarity needs at least 2 rows.

    Parameters used:
      stop_words='english' — ignore words like "the", "is", "a"
      ngram_range=(1,2)    — single words AND two-word phrases
      min_df=1             — include words that appear only once
    """
    if df.empty or len(df) < 2:
        return None, None

    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1
    )
    try:
        matrix = vectorizer.fit_transform(df['features'])
        return matrix, vectorizer
    except Exception as e:
        print(f"[Recommendation] TF-IDF error: {e}")
        return None, None


# ============================================================
# SECTION 4 — COSINE SIMILARITY
# Measure the angle between two product vectors.
# Score 0 = nothing in common; 1 = identical features.
# ============================================================

def compute_similarity_matrix(tfidf_matrix):
    """
    Compute the full N×N cosine similarity matrix.
    sim[i][j] = similarity score between product i and product j.
    Returns None if the matrix argument is None.
    """
    if tfidf_matrix is None:
        return None
    return cosine_similarity(tfidf_matrix, tfidf_matrix)


# ============================================================
# SECTION 5 — MAIN RECOMMENDATION FUNCTION
# Given a product_id, return the top-N most similar products.
# ============================================================

def get_recommendations(product_id, n=6):
    """
    Return up to n recommended products for the given product_id,
    ranked from most similar to least similar.

    Each result is a dict with keys:
        id, name, price, image, category, stock, similarity_score

    Returns [] when:
      • product_id not found in the database
      • fewer than 2 products exist
      • any unexpected error occurs
    """
    try:
        # ── 1. Load and preprocess ─────────────────────────
        df = load_products_df()
        df = preprocess_products(df)

        if df.empty or len(df) < 2:
            return []

        # ── 2. Build TF-IDF matrix ─────────────────────────
        tfidf_matrix, _ = build_tfidf_matrix(df)
        if tfidf_matrix is None:
            return []

        # ── 3. Cosine similarity matrix ────────────────────
        sim_matrix = compute_similarity_matrix(tfidf_matrix)
        if sim_matrix is None:
            return []

        # ── 4. Find the row index for the requested product ─
        id_list = df['id'].tolist()
        if product_id not in id_list:
            return []
        idx = id_list.index(product_id)

        # ── 5. Collect and sort similarity scores ──────────
        # sim_matrix[idx] is a 1-D array of scores vs every product
        scores = list(enumerate(sim_matrix[idx]))
        scores.sort(key=lambda x: x[1], reverse=True)  # highest first

        # ── 6. Remove the product itself ───────────────────
        scores = [(i, s) for i, s in scores if i != idx]

        # ── 7. Take top n ──────────────────────────────────
        top_n = scores[:n]

        # ── 8. Build result dicts ──────────────────────────
        recommendations = []
        for row_idx, score in top_n:
            row = df.iloc[row_idx]
            recommendations.append({
                'id':               int(row['id']),
                'name':             str(row['name']),
                'price':            float(row['price']),
                'image':            str(row['image']),
                'category':         str(row['category']),
                'stock':            int(row['stock']),
                'similarity_score': round(float(score), 4)
            })

        return recommendations

    except Exception as e:
        print(f"[Recommendation] get_recommendations error: {e}")
        return []


# ============================================================
# SECTION 6 — HOMEPAGE "POPULAR PRODUCTS"
# No user history exists, so we show one representative
# product from each category plus high-stock fillers.
# This is NOT personalized — labelled "Popular Products".
# ============================================================

def get_homepage_recommendations(n=8, exclude_id=None):
    """
    Return n products for the homepage Popular Products section.

    Strategy:
      1. Filter to in-stock products only.
      2. Pick the highest-stock product from EACH category.
         FIX: use groupby + idxmax instead of groupby.first()
              so the 'category' column is preserved correctly.
      3. Fill remaining slots with other high-stock products.
      4. Exclude exclude_id if provided.
      5. Return the list shuffled with a fixed seed for
         consistent but varied ordering.
    """
    try:
        df = load_products_df()
        if df.empty:
            return []

        # Only recommend products that are in stock
        available = df[df['stock'] > 0].copy()
        if available.empty:
            return []

        # ── FIX: get the index of the highest-stock row per category
        #        This preserves ALL columns including 'category'.
        best_idx = (
            available
            .groupby('category', sort=False)['stock']
            .idxmax()               # returns the row index of max stock per group
        )
        category_reps = available.loc[best_idx].copy()

        # Fill remaining slots with other in-stock products
        already_chosen = set(category_reps['id'].tolist())
        remaining = (
            available[~available['id'].isin(already_chosen)]
            .sort_values('stock', ascending=False)
        )

        combined = pd.concat(
            [category_reps, remaining],
            ignore_index=True
        ).drop_duplicates(subset='id')

        # Optionally exclude a specific product (e.g. the one being viewed)
        if exclude_id is not None:
            combined = combined[combined['id'] != exclude_id]

        # Take a pool of 2×n, shuffle with fixed seed, then take n
        pool = combined.head(n * 2)
        pool = pool.sample(frac=1, random_state=42).head(n)

        result = []
        for _, row in pool.iterrows():
            result.append({
                'id':       int(row['id']),
                'name':     str(row['name']),
                'price':    float(row['price']),
                'image':    str(row['image']),
                'category': str(row['category']),   # now always correct
                'stock':    int(row['stock'])
            })
        return result

    except Exception as e:
        print(f"[Recommendation] get_homepage_recommendations error: {e}")
        return []


# ============================================================
# SECTION 7 — SIMILARITY SCORES FOR CHART
# Returns name + score pairs used by analysis.py to draw a
# bar chart of the top-N similar products.
# ============================================================

def get_similarity_scores_for_chart(product_id, n=10):
    """
    Return a list of dicts [{name, score}] for the top-n products
    most similar to product_id.  Used by the analysis/charts page.
    """
    recs = get_recommendations(product_id, n=n)
    return [
        {'name': r['name'], 'score': r['similarity_score']}
        for r in recs
    ]


# ============================================================
# SECTION 8 — SELF-TEST  (python recommendation.py)
# ============================================================

if __name__ == '__main__':
    print("=" * 55)
    print("  Recommendation System — Self-Test")
    print("=" * 55)

    df_raw = load_products_df()
    print(f"\nTotal products loaded : {len(df_raw)}")

    if df_raw.empty:
        print("No products found. Run app.py once to seed the DB.")
    else:
        df_clean = preprocess_products(df_raw)
        print(f"Duplicate rows removed: "
              f"{len(df_raw) - len(df_clean)}")
        print(f"\nSample feature strings:")
        for _, r in df_clean.head(3).iterrows():
            print(f"  [{r['name']}]  →  \"{r['features'][:70]}...\"")

        # Test recommendations for first 3 products
        for i in range(min(3, len(df_clean))):
            pid   = int(df_clean.iloc[i]['id'])
            pname = df_clean.iloc[i]['name']
            recs  = get_recommendations(pid, n=4)
            print(f"\nRecommendations for  →  {pname}  (id={pid})")
            if recs:
                for r in recs:
                    bar = '█' * int(r['similarity_score'] * 20)
                    print(f"   {r['name']:30s}  "
                          f"{bar:<20s}  {r['similarity_score']:.4f}  "
                          f"[{r['category']}]")
            else:
                print("   (no recommendations)")

        # Test homepage picks
        home = get_homepage_recommendations(n=6)
        print(f"\nHomepage Popular Products ({len(home)} items):")
        for h in home:
            print(f"  {h['name']:30s}  cat={h['category']:12s}  "
                  f"stock={h['stock']}")

        print("\nSelf-test complete ✓")


# ============================================================
# SECTION 9 — CUSTOMER BEHAVIOR-BASED RECOMMENDATIONS
#
# Uses the customer's:
#   1. Previous orders  → products they already bought
#   2. Current cart     → products they are considering
#   3. Category browsed → category passed from the search bar
#
# Logic:
#   - Find all product_ids the user ordered or has in cart.
#   - Get the categories of those products.
#   - Also include the category they searched/browsed.
#   - Return in-stock products from those preferred categories,
#     excluding products they already bought/carted.
#   - If no history exists, fall back to get_homepage_recommendations().
# ============================================================

def get_behavior_recommendations(user_phone, browsed_category=None, n=8):
    """
    Return personalized recommendations based on:
      - user's past orders (from orders table)
      - user's current cart items (from cart table)
      - category the user is currently browsing (browsed_category)

    Returns a list of product dicts and a reason string
    so the template can show an honest label like
    "Based on your orders" or "Based on your browsing".

    Falls back to get_homepage_recommendations() if user has
    no order or cart history.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        ordered_product_ids  = []
        cart_product_ids     = []
        preferred_categories = []
        reason               = ''

        # ── 1. Get products the user has previously ordered ─
        if user_phone:
            rows = conn.execute(
                'SELECT DISTINCT product_id FROM orders WHERE user_phone=?',
                (user_phone,)
            ).fetchall()
            ordered_product_ids = [r['product_id'] for r in rows if r['product_id']]

        # ── 2. Get products currently in user's cart ────────
        if user_phone:
            rows = conn.execute(
                'SELECT DISTINCT product_id FROM cart WHERE user_phone=?',
                (user_phone,)
            ).fetchall()
            cart_product_ids = [r['product_id'] for r in rows if r['product_id']]

        # ── 2b. Get recently viewed products (last 10 views) ─
        viewed_product_ids = []
        if user_phone:
            rows = conn.execute(
                '''SELECT DISTINCT product_id FROM product_views
                   WHERE user_phone=?
                   ORDER BY viewed_at DESC LIMIT 10''',
                (user_phone,)
            ).fetchall()
            viewed_product_ids = [r['product_id'] for r in rows if r['product_id']]

        # ── 3. Find preferred categories from all interactions
        all_interacted_ids = list(set(ordered_product_ids + cart_product_ids + viewed_product_ids))
        if all_interacted_ids:
            placeholders = ','.join('?' * len(all_interacted_ids))
            rows = conn.execute(
                f'SELECT DISTINCT category FROM products WHERE id IN ({placeholders})',
                all_interacted_ids
            ).fetchall()
            preferred_categories = [r['category'] for r in rows if r['category']]

        # ── 4. Add the currently browsed category if provided
        if browsed_category and browsed_category != 'All':
            if browsed_category not in preferred_categories:
                preferred_categories.append(browsed_category)

        conn.close()

        # ── 5. Decide what to show and set reason label ─────
        if ordered_product_ids:
            reason = 'Based on your orders, views & browsing'
        elif viewed_product_ids and cart_product_ids:
            reason = 'Based on your views & cart'
        elif viewed_product_ids:
            reason = 'Based on products you viewed'
        elif preferred_categories and browsed_category:
            reason = f'Based on your interest in {browsed_category}'
        elif preferred_categories:
            reason = 'Based on your cart items'
        else:
            # No history at all — fall back to popular products
            fallback = get_homepage_recommendations(n=n)
            return fallback, 'Popular Products'

        # ── 6. Load all products into DataFrame ─────────────
        df = load_products_df()
        if df.empty:
            return [], ''

        # ── 7. Filter: preferred categories + in stock ───────
        mask = (
            df['category'].isin(preferred_categories) &
            (df['stock'] > 0) &
            (~df['id'].isin(all_interacted_ids))  # exclude already bought/carted
        )
        filtered = df[mask].copy()

        # ── 8. If not enough results, also add other categories
        if len(filtered) < n:
            extras = df[
                (df['stock'] > 0) &
                (~df['id'].isin(all_interacted_ids)) &
                (~df['id'].isin(filtered['id']))
            ].copy()
            filtered = pd.concat([filtered, extras], ignore_index=True)

        # ── 9. Sort by stock (highest first) and take n ─────
        filtered = filtered.sort_values('stock', ascending=False).head(n)

        result = []
        for _, row in filtered.iterrows():
            result.append({
                'id':       int(row['id']),
                'name':     str(row['name']),
                'price':    float(row['price']),
                'image':    str(row['image']),
                'category': str(row['category']),
                'stock':    int(row['stock'])
            })

        return result, reason

    except Exception as e:
        print(f'[Recommendation] get_behavior_recommendations error: {e}')
        return [], ''
