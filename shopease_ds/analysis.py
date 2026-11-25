# ============================================================
# analysis.py
# Data Science Analysis Module
# Generates statistics and Matplotlib charts for the
# ShopEase admin analytics page.
# ============================================================
#
# Charts generated:
#   1. category_distribution.png  — bar chart of products per category
#   2. price_distribution.png     — histogram of product prices
#   3. stock_analysis.png         — horizontal bar chart of stock levels
#   4. similarity_chart.png       — bar chart of similarity scores
#                                   (generated on-demand per product)
#
# All charts are saved as PNG files in static/charts/
# so Flask can serve them directly as <img src="/static/charts/...">
# Matplotlib is set to non-interactive (Agg) backend so it
# NEVER opens a window — safe for server use.
# ============================================================

import os
import sqlite3

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')          # Non-interactive backend — no window
import matplotlib.pyplot as plt

from recommendation import load_products_df, get_similarity_scores_for_chart


# ── Resolve paths relative to this file ─────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR   = os.path.join(_HERE, 'static', 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)   # Create folder if missing


# ── Shared color palette (matches website's orange/navy theme) ─
PRIMARY   = '#FF6B35'   # orange
SECONDARY = '#2D3748'   # dark navy
ACCENT    = '#00C9A7'   # teal
WARNING   = '#FED330'   # yellow
DANGER    = '#FC5C65'   # red
MUTED     = '#718096'   # grey

CATEGORY_COLORS = [
    PRIMARY, SECONDARY, ACCENT, WARNING, DANGER,
    '#8B5CF6', '#06B6D4', '#EC4899'
]


# ============================================================
# SECTION 1 — DATA SUMMARY STATISTICS
# Returns a dict of key metrics shown on the analysis page.
# ============================================================

def get_data_summary():
    """
    Load products from SQLite and return summary statistics:
      total_products, categories, avg_price, min_price,
      max_price, in_stock, out_of_stock, low_stock,
      category_counts (dict), total_orders, total_customers,
      total_revenue.

    Returns a dict of safe default values if the DB is empty
    or an error occurs.
    """
    default = {
        'total_products': 0, 'categories': 0,
        'avg_price': 0, 'min_price': 0, 'max_price': 0,
        'in_stock': 0, 'out_of_stock': 0, 'low_stock': 0,
        'category_counts': {}, 'total_stock': 0,
        'total_orders': 0, 'total_customers': 0, 'total_revenue': 0
    }

    try:
        df = load_products_df()
        if df.empty:
            return default

        # ── Product statistics ──────────────────────────────
        summary = {
            'total_products': len(df),
            'categories':     df['category'].nunique(),
            'avg_price':      round(float(df['price'].mean()), 2),
            'min_price':      round(float(df['price'].min()), 2),
            'max_price':      round(float(df['price'].max()), 2),
            'in_stock':       int((df['stock'] > 0).sum()),
            'out_of_stock':   int((df['stock'] == 0).sum()),
            'low_stock':      int(((df['stock'] > 0) & (df['stock'] < 5)).sum()),
            'total_stock':    int(df['stock'].sum()),
            'category_counts': df.groupby('category')['id']
                                  .count()
                                  .to_dict()
        }

        # ── Order / customer statistics ─────────────────────
        try:
            db_path = os.path.join(_HERE, 'ecommerce.db')
            conn = sqlite3.connect(db_path)
            orders_row   = conn.execute('SELECT COUNT(*), COALESCE(SUM(price),0) FROM orders').fetchone()
            customers_ct = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
            conn.close()
            summary['total_orders']    = int(orders_row[0])
            summary['total_revenue']   = round(float(orders_row[1]), 2)
            summary['total_customers'] = int(customers_ct)
        except Exception:
            summary.update({'total_orders': 0, 'total_customers': 0, 'total_revenue': 0})

        return summary

    except Exception as e:
        print(f"[Analysis] get_data_summary error: {e}")
        return default


# ============================================================
# SECTION 2 — CHART 1: CATEGORY DISTRIBUTION
# Bar chart showing the number of products in each category.
# ============================================================

def generate_category_chart():
    """
    Create and save static/charts/category_distribution.png.
    Returns the relative URL string for use in <img src="...">.
    Returns None on failure.
    """
    try:
        df = load_products_df()
        if df.empty:
            return None

        counts = df.groupby('category')['id'].count().sort_values(ascending=False)

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#F7F8FC')   # match site background
        ax.set_facecolor('#F7F8FC')

        # Draw bars
        bars = ax.bar(
            counts.index,
            counts.values,
            color=CATEGORY_COLORS[:len(counts)],
            edgecolor='white',
            linewidth=1.5,
            width=0.6
        )

        # Add value labels on top of each bar
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.1,
                str(int(h)),
                ha='center', va='bottom',
                fontsize=11, fontweight='bold', color=SECONDARY
            )

        # Styling
        ax.set_title('Product Category Distribution',
                     fontsize=15, fontweight='bold', color=SECONDARY, pad=16)
        ax.set_xlabel('Category', fontsize=11, color=MUTED, labelpad=8)
        ax.set_ylabel('Number of Products', fontsize=11, color=MUTED, labelpad=8)
        ax.tick_params(colors=MUTED, labelsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(MUTED)
        ax.spines['bottom'].set_color(MUTED)
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.set_ylim(0, counts.max() + 1.5)

        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, 'category_distribution.png')
        plt.savefig(path, dpi=130, bbox_inches='tight')
        plt.close(fig)

        return '/static/charts/category_distribution.png'

    except Exception as e:
        print(f"[Analysis] category chart error: {e}")
        return None


# ============================================================
# SECTION 3 — CHART 2: PRICE DISTRIBUTION
# Histogram of product prices.
# ============================================================

def generate_price_chart():
    """
    Create and save static/charts/price_distribution.png.
    Returns the relative URL string or None on failure.
    """
    try:
        df = load_products_df()
        if df.empty:
            return None

        prices = df['price'].dropna()
        if len(prices) < 2:
            return None

        # Decide number of bins: min 5, max 15
        n_bins = min(15, max(5, len(prices) // 2))

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#F7F8FC')
        ax.set_facecolor('#F7F8FC')

        n, bins, patches = ax.hist(
            prices, bins=n_bins,
            color=PRIMARY, edgecolor='white', linewidth=1.2, alpha=0.85
        )

        # Overlay KDE-like smooth line
        try:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(prices, bw_method='silverman')
            x_range = np.linspace(prices.min(), prices.max(), 200)
            # Scale KDE to histogram height
            scale = (bins[1] - bins[0]) * len(prices)
            ax.plot(x_range, kde(x_range) * scale,
                    color=SECONDARY, linewidth=2, linestyle='--',
                    label='Density curve')
            ax.legend(fontsize=9)
        except ImportError:
            pass   # scipy optional — chart still works without it

        # Mean line
        ax.axvline(prices.mean(), color=ACCENT, linewidth=2, linestyle='-',
                   label=f'Mean ₹{prices.mean():.0f}')
        ax.legend(fontsize=9)

        # Styling
        ax.set_title('Product Price Distribution',
                     fontsize=15, fontweight='bold', color=SECONDARY, pad=16)
        ax.set_xlabel('Price (₹)', fontsize=11, color=MUTED, labelpad=8)
        ax.set_ylabel('Number of Products', fontsize=11, color=MUTED, labelpad=8)
        ax.tick_params(colors=MUTED, labelsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(MUTED)
        ax.spines['bottom'].set_color(MUTED)

        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, 'price_distribution.png')
        plt.savefig(path, dpi=130, bbox_inches='tight')
        plt.close(fig)

        return '/static/charts/price_distribution.png'

    except Exception as e:
        print(f"[Analysis] price chart error: {e}")
        return None


# ============================================================
# SECTION 4 — CHART 3: STOCK ANALYSIS
# Horizontal bar chart — stock level per product.
# ============================================================

def generate_stock_chart():
    """
    Create and save static/charts/stock_analysis.png.
    Shows each product's stock level as a horizontal bar,
    colour-coded by status: Out of Stock / Low / OK.
    Returns the relative URL string or None on failure.
    """
    try:
        df = load_products_df()
        if df.empty:
            return None

        # Sort by stock ascending so the highest bar is at the top
        df_sorted = df.sort_values('stock', ascending=True).copy()

        # Assign a color to each bar based on stock level
        def bar_color(stock):
            if stock == 0:
                return DANGER     # red — out of stock
            elif stock < 5:
                return WARNING    # yellow — low stock
            else:
                return ACCENT     # teal — ok

        colors = [bar_color(s) for s in df_sorted['stock']]

        fig_height = max(5, len(df_sorted) * 0.45)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        fig.patch.set_facecolor('#F7F8FC')
        ax.set_facecolor('#F7F8FC')

        bars = ax.barh(
            df_sorted['name'],
            df_sorted['stock'],
            color=colors,
            edgecolor='white',
            linewidth=1,
            height=0.6
        )

        # Value labels at end of each bar
        for bar, stock in zip(bars, df_sorted['stock']):
            ax.text(
                bar.get_width() + 0.3,
                bar.get_y() + bar.get_height() / 2,
                str(int(stock)),
                va='center', ha='left',
                fontsize=9, color=SECONDARY
            )

        # Legend
        from matplotlib.patches import Patch
        legend_items = [
            Patch(facecolor=ACCENT,   label='In Stock (≥5)'),
            Patch(facecolor=WARNING,  label='Low Stock (1-4)'),
            Patch(facecolor=DANGER,   label='Out of Stock (0)'),
        ]
        ax.legend(handles=legend_items, fontsize=9,
                  loc='lower right', framealpha=0.8)

        ax.set_title('Product Stock Analysis',
                     fontsize=15, fontweight='bold', color=SECONDARY, pad=16)
        ax.set_xlabel('Stock Quantity', fontsize=11, color=MUTED, labelpad=8)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(MUTED)
        ax.spines['bottom'].set_color(MUTED)
        ax.set_xlim(0, df_sorted['stock'].max() * 1.18)

        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, 'stock_analysis.png')
        plt.savefig(path, dpi=130, bbox_inches='tight')
        plt.close(fig)

        return '/static/charts/stock_analysis.png'

    except Exception as e:
        print(f"[Analysis] stock chart error: {e}")
        return None


# ============================================================
# SECTION 5 — CHART 4: SIMILARITY SCORES
# Bar chart of cosine similarity scores for a given product.
# Generated on-demand and cached as similarity_chart.png.
# ============================================================

def generate_similarity_chart(product_id, product_name='Product'):
    """
    Create and save static/charts/similarity_chart.png
    showing cosine similarity scores of the top-10 products
    most similar to product_id.

    Returns the relative URL string or None on failure.
    """
    try:
        scores = get_similarity_scores_for_chart(product_id, n=10)
        if not scores:
            return None

        names  = [s['name']  for s in scores]
        values = [s['score'] for s in scores]

        # Shorten long names for readability
        names_short = [n[:22] + '…' if len(n) > 22 else n for n in names]

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#F7F8FC')
        ax.set_facecolor('#F7F8FC')

        # Gradient colors: higher bar = more orange
        bar_colors = [PRIMARY if v == max(values) else SECONDARY
                      for v in values]

        bars = ax.bar(
            range(len(names_short)), values,
            color=bar_colors, edgecolor='white',
            linewidth=1.2, width=0.6
        )

        # Value labels on top of each bar
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f'{val:.3f}',
                ha='center', va='bottom',
                fontsize=8, color=SECONDARY
            )

        ax.set_xticks(range(len(names_short)))
        ax.set_xticklabels(names_short, rotation=30, ha='right', fontsize=9)
        ax.set_ylim(0, min(1.0, max(values) * 1.25))

        ax.set_title(f'Similarity Scores for: {product_name[:35]}',
                     fontsize=13, fontweight='bold', color=SECONDARY, pad=14)
        ax.set_xlabel('Recommended Products', fontsize=10, color=MUTED, labelpad=8)
        ax.set_ylabel('Cosine Similarity Score (0–1)',
                      fontsize=10, color=MUTED, labelpad=8)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(MUTED)
        ax.spines['bottom'].set_color(MUTED)

        plt.tight_layout()
        path = os.path.join(CHARTS_DIR, 'similarity_chart.png')
        plt.savefig(path, dpi=130, bbox_inches='tight')
        plt.close(fig)

        return '/static/charts/similarity_chart.png'

    except Exception as e:
        print(f"[Analysis] similarity chart error: {e}")
        return None


# ============================================================
# SECTION 6 — GENERATE ALL STATIC CHARTS AT ONCE
# Called by app.py when the analysis page is loaded.
# ============================================================

def generate_all_charts():
    """
    Generate charts 1, 2, and 3.
    Returns a dict of {chart_name: url_or_None}.
    Chart 4 (similarity) is generated per-product on demand.
    """
    return {
        'category': generate_category_chart(),
        'price':    generate_price_chart(),
        'stock':    generate_stock_chart(),
    }


# ============================================================
# SECTION 7 — SELF-TEST  (python analysis.py)
# ============================================================

if __name__ == '__main__':
    print("=" * 55)
    print("  Analysis Module — Self-Test")
    print("=" * 55)

    print("\n[1] Data Summary:")
    s = get_data_summary()
    for k, v in s.items():
        if k != 'category_counts':
            print(f"    {k:20s}: {v}")
    print(f"    {'category_counts':20s}: {s['category_counts']}")

    print("\n[2] Generating all charts...")
    charts = generate_all_charts()
    for name, path in charts.items():
        status = '✓' if path else '✗'
        print(f"    {status} {name:15s}: {path}")

    print("\n[3] Generating similarity chart for product id=1...")
    sim_path = generate_similarity_chart(1, 'Classic White Shirt')
    print(f"    {'✓' if sim_path else '✗'} similarity  : {sim_path}")

    print(f"\nCharts saved to: {CHARTS_DIR}")
    print("\nSelf-test complete ✓")
