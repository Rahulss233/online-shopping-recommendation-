# ShopEase — Online Shopping Recommendation System

## Project Title
Online Shopping Recommendation System integrated into an existing Flask E-Commerce Website

---

## Project Abstract

The Online Shopping Recommendation System integrates Data Science techniques into the ShopEase e-commerce website to identify and recommend relevant products automatically. The system analyses product attributes such as names, categories, and descriptions using Python, Pandas, and Scikit-learn. TF-IDF vectorization converts product text into numeric vectors, and cosine similarity measures how similar two products are. Recommendation results are integrated into the Flask website connected to an SQLite database. Matplotlib generates visual charts showing product distributions and similarity scores. The system improves product discovery and provides relevant recommendations while preserving all existing shopping, cart, checkout, and admin features.

---

## Problem Statement

A conventional e-commerce website displays products through static categories and search results. Customers must browse manually to find alternatives or similar products. There is no automatic system to suggest related products based on product content. This slows product discovery and reduces the chance of finding relevant items.

---

## Objectives

1. Integrate a content-based recommendation system into the existing ShopEase e-commerce website.
2. Analyse and preprocess product data using Pandas and NumPy.
3. Apply TF-IDF vectorization and cosine similarity for product recommendations.
4. Display recommendations on the product detail page and homepage.
5. Visualize product statistics using Matplotlib (4 charts).
6. Preserve all existing shopping, cart, order, and admin features.
7. Provide a Data Science analysis page in the admin panel.

---

## Technologies Used

| Technology       | Purpose                                          |
|------------------|--------------------------------------------------|
| Python 3.8+      | Backend logic, algorithm implementation          |
| Flask 2.3+       | Web framework, routing, template rendering       |
| SQLite3          | Lightweight database for products and orders     |
| Pandas 2.0+      | Data loading, preprocessing, groupby operations  |
| NumPy 1.24+      | Numerical operations, array handling             |
| Scikit-learn 1.3+| TF-IDF Vectorizer, cosine similarity             |
| Matplotlib 3.7+  | Chart generation saved as PNG files              |
| HTML + CSS       | Frontend templates with internal styling         |
| Jinja2           | Template engine built into Flask                 |

---

## Project Structure

```
ecommerce/
│
├── app.py                  ← Flask application (all routes)
├── recommendation.py       ← Recommendation engine (TF-IDF + Cosine Similarity)
├── analysis.py             ← Data analysis + Matplotlib chart generation
├── requirements.txt        ← Python package dependencies
├── README.md               ← This file
├── viva_notes.md           ← Viva preparation notes
├── ecommerce.db            ← SQLite database (auto-created on first run)
│
├── static/
│   └── charts/             ← Generated Matplotlib chart PNG files
│       ├── category_distribution.png
│       ├── price_distribution.png
│       ├── stock_analysis.png
│       └── similarity_chart.png
│
└── templates/
    ├── base.html           ← Shared navbar, CSS, footer
    ├── index.html          ← Homepage with Popular Products section
    ├── product_detail.html ← Product page with Recommended Products section
    ├── cart.html
    ├── checkout.html
    ├── buy_now.html
    ├── orders.html
    ├── login.html
    └── admin/
        ├── base_admin.html ← Admin sidebar layout
        ├── dashboard.html
        ├── products.html
        ├── product_form.html
        ├── orders.html
        ├── customers.html
        └── analysis.html   ← NEW: Data Science analysis page
```

---

## Database Schema

### products
| Column      | Type    | Description                    |
|-------------|---------|--------------------------------|
| id          | INTEGER | Primary key                    |
| name        | TEXT    | Product name                   |
| price       | REAL    | Price in rupees                |
| image       | TEXT    | Image URL                      |
| description | TEXT    | Product description            |
| category    | TEXT    | Category (Shirt, T-Shirt, etc.)|
| stock       | INTEGER | Available quantity             |

### orders, customers, cart — preserved from original project.

---

## Recommendation Algorithm

### Type: Content-Based Filtering

**Step-by-step:**

1. **Load** — All products are loaded from SQLite using `pandas.read_sql_query()`.
2. **Preprocess** — Name, category (repeated ×3 for emphasis), and description are cleaned and combined into one text string called `features`.
3. **TF-IDF** — `TfidfVectorizer` (Scikit-learn) converts each product's `features` string into a numeric vector. Rare/distinctive words get higher weights; common words get lower weights.
4. **Cosine Similarity** — The full N×N similarity matrix is computed. Each entry [i][j] is the similarity score between product i and product j (0 = nothing in common, 1 = identical).
5. **Rank** — For a given product, similarity scores vs all other products are sorted in descending order.
6. **Return** — Top N products (excluding the viewed product itself) are returned as recommendations.

**Why category is repeated ×3:**
Two products in the same category should always rank higher than products that coincidentally share a word in their name. Repeating the category string triples its TF-IDF weight.

---

## Data Visualizations

| Chart | File | Description |
|-------|------|-------------|
| Category Distribution | category_distribution.png | Bar chart of products per category |
| Price Distribution    | price_distribution.png    | Histogram with mean line |
| Stock Analysis        | stock_analysis.png        | Horizontal bar, colour-coded by status |
| Similarity Scores     | similarity_chart.png      | Bar chart of cosine scores per product |

All charts are generated using **Matplotlib** with `Agg` backend (no GUI window). Saved as PNG and served via Flask's static file route.

---

## Installation Steps

### 1. Extract the project ZIP
Unzip `ecommerce_shopease_ds.zip` into a folder.

### 2. Open terminal in the project folder
```bash
cd ecommerce
```

### 3. (Optional) Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 4. Install all dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the application
```bash
python app.py
```

### 6. Open in browser
```
http://127.0.0.1:5000
```

---

## How to Test the Recommendation System

### User side:
1. Open any product (e.g., "Classic White Shirt").
2. Scroll below the product details.
3. You will see a **"🎯 Recommended Products"** section.
4. Each card shows a **Match score %** (cosine similarity × 100).
5. Click any recommended card — it opens that product's detail page.

### Admin side:
1. Login with: Name=`Rahul S S`, Phone=`963852741`, Email=`wasd951@gmail.com`
2. Click **"📈 DS Analysis"** in the sidebar.
3. View summary statistics, 3 product charts, and the similarity chart.
4. Use the dropdown to select any product and click **"⚡ Generate Chart"**.
5. The similarity bar chart updates without reloading the page (AJAX).

### Test the recommendation module directly:
```bash
python recommendation.py
```

### Test the analysis module directly:
```bash
python analysis.py
```

---

## Admin Credentials

| Field | Value            |
|-------|------------------|
| Name  | Rahul S S        |
| Phone | 963852741        |
| Email | wasd951@gmail.com|

---

## Expected Outputs

- Homepage shows **"🔥 Popular Products"** section (one product per category).
- Product detail page shows **"🎯 Recommended Products"** with similarity scores.
- Admin analysis page shows 3 charts + interactive similarity chart.
- `static/charts/` folder contains 4 PNG chart files after first visit.

---

## Limitations

1. **No user history** — Recommendations are content-based only. No personalization based on purchase or browsing history (collaborative filtering not implemented).
2. **Cold start** — With fewer than 2 products, no recommendations are generated.
3. **English only** — TF-IDF uses English stop-word removal. Other languages may not work correctly.
4. **No real-time retraining** — The TF-IDF matrix is rebuilt on every request from the database. For large catalogues (1000+ products), caching would improve performance.
5. **Small catalogue** — With only 12 demo products, similarity scores may not perfectly reflect real-world ranking behaviour.

---

## Future Enhancements

1. **Collaborative filtering** — Use order history to recommend products that similar customers bought.
2. **Hybrid model** — Combine content-based and collaborative filtering.
3. **Matrix caching** — Cache the TF-IDF matrix in memory and rebuild only when products change.
4. **User click tracking** — Record which products users view to improve personalization.
5. **Ratings system** — Allow customers to rate products and use ratings in recommendations.

---

© 2026 ShopEase
