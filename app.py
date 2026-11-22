
import os
import re
import time
from datetime import datetime, timedelta
from collections import Counter

import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

from pytrends.request import TrendReq
from googleapiclient.discovery import build


# ============================================================
# CONFIG & SETUP
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="Viral SEO Generator - YouTube",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff0000, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .metric-card {
        background: #1e1e2e;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff0000;
    }
    .title-box {
        background: #f0f2f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #ff0000;
        color: #000;
    }
    .tag-box {
        display: inline-block;
        background: #e1e1e1;
        padding: 4px 10px;
        border-radius: 15px;
        margin: 3px;
        font-size: 0.85rem;
        color: #000;
    }
    .stButton>button {
        background: linear-gradient(90deg, #ff0000, #ff6b6b);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 10px 25px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends(keyword: str, region: str = "PK"):
    """Fetch Google Trends rising & related queries."""
    try:
        pytrends = TrendReq(hl="en-US", tz=300, timeout=(10, 25))
        pytrends.build_payload([keyword], timeframe="now 7-d", geo=region)

        related_queries = pytrends.related_queries()
        rising = related_queries.get(keyword, {}).get("rising")
        top = related_queries.get(keyword, {}).get("top")

        rising_list = []
        if rising is not None and not rising.empty:
            rising_list = rising.head(10).to_dict("records")

        top_list = []
        if top is not None and not top.empty:
            top_list = top.head(10).to_dict("records")

        return {"rising": rising_list, "top": top_list}
    except Exception as e:
        return {"error": str(e), "rising": [], "top": []}


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_top_videos(keyword: str, region: str = "PK", max_results: int = 20):
    """Fetch top videos for a keyword using YouTube Data API."""
    if not YOUTUBE_API_KEY:
        return {"error": "YouTube API key missing. Set YOUTUBE_API_KEY in .env file."}

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        # --- Search for videos ---
        search_response = youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            maxResults=max_results,
            order="viewCount",
            regionCode=region,
            relevanceLanguage="en",
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        if not video_ids:
            return {"error": "No videos found for this keyword.", "videos": []}

        # --- Get video statistics ---
        stats_response = youtube.videos().list(
            part="statistics,contentDetails,snippet",
            id=",".join(video_ids),
        ).execute()

        videos = []
        for item in stats_response.get("items", []):
            stats = item["statistics"]
            snippet = item["snippet"]
            videos.append({
                "video_id": item["id"],
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
                "channel": snippet["channelTitle"],
                "published": snippet["publishedAt"][:10],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "url": f"https://youtube.com/watch?v={item['id']}",
            })

        # --- Sort by views (desc) ---
        videos.sort(key=lambda x: x["views"], reverse=True)
        return {"videos": videos[:20]}

    except Exception as e:
        return {"error": str(e), "videos": []}


def extract_title_patterns(videos: list) -> dict:
    """Analyze titles from top videos to detect viral patterns."""
    patterns = {
        "numbers": 0,
        "question": 0,
        "how_to": 0,
        "negative": 0,
        "brackets": 0,
        "caps_words": 0,
        "curiosity": 0,
        "urgency": 0,
    }

    number_re = re.compile(r"\b\d+\b")
    caps_re = re.compile(r"\b[A-Z]{3,}\b")
    negative_words = ["stop", "never", "don't", "mistake", "wrong", "avoid", "fail", "won't", "isn't"]
    curiosity_words = ["secret", "truth", "nobody", "no one", "revealed", "hidden", "actually", "really"]
    urgency_words = ["now", "today", "fast", "quick", "immediately", "2024", "2025", "2026", "new"]

    for v in videos:
        title = v["title"].lower()
        if number_re.search(title):
            patterns["numbers"] += 1
        if "?" in title:
            patterns["question"] += 1
        if "how to" in title:
            patterns["how_to"] += 1
        if any(w in title for w in negative_words):
            patterns["negative"] += 1
        if "[" in title or "(" in title:
            patterns["brackets"] += 1
        if caps_re.search(v["title"]):
            patterns["caps_words"] += 1
        if any(w in title for w in curiosity_words):
            patterns["curiosity"] += 1
        if any(w in title for w in urgency_words):
            patterns["urgency"] += 1

    return patterns


def generate_clickbait_titles(keyword: str, patterns: dict, rising: list) -> list:
    """Generate clickbait titles based on analyzed patterns + rising queries."""
    titles = []

    # Rising query integration
    rising_terms = [r.get("query", "") for r in rising[:3] if r.get("query")]
    bonus = rising_terms[0] if rising_terms else keyword

    # Base title templates (all proven viral formats)
    templates = [
        f"STOP Doing This With {keyword.title()} — You're Losing Money!",
        f"The TRUTH About {keyword.title()} Nobody Tells You ({datetime.now().year})",
        f"I Tried {keyword.title()} for 30 Days — Here's What Happened",
        f"How to {keyword.title()} in 2026 (SECRET Method Revealed)",
        f"Why 99% of People FAIL at {keyword.title()} — Do THIS Instead",
        f"{keyword.title()}: 7 Mistakes You're Making RIGHT NOW",
        f"The ONLY {keyword.title()} Guide You'll Ever Need",
        f"Top 5 {keyword.title()} Secrets Experts Are Hiding",
        f"{bonus} — What Nobody Told You!",
        f"5-Minute {keyword.title()} Hack (Works Instantly!)",
        f"Don't Try {keyword.title()} Until You Watch This",
        f"How {keyword.title()} Will Change Everything in 2026",
    ]

    # Add pattern-driven suggestions
    if patterns.get("numbers", 0) > 5:
        titles.append(f"10 {keyword.title()} Tricks That Actually Work in 2026")
    if patterns.get("curiosity", 0) > 3:
        titles.append(f"The Hidden Side of {keyword.title()} Nobody Wants You to Know")
    if patterns.get("negative", 0) > 3:
        titles.append(f"Never Do This With {keyword.title()} (It's Ruining Your Results)")

    return templates + titles


def generate_description(keyword: str, rising: list, video_titles: list) -> str:
    """Generate SEO-optimized description."""
    rising_terms = [r.get("query", "") for r in rising[:5] if r.get("query")]
    hashtag_base = keyword.replace(" ", "")

    desc = f"""🎯 {keyword.title()} — Complete Guide ({datetime.now().year})

In this video, we break down everything about {keyword} — the latest updates, hidden tips, and the exact strategy that top creators are using RIGHT NOW.

⏱️ TIMESTAMPS:
00:00 — Intro: Why {keyword} Matters
00:45 — The Truth About {keyword}
02:30 — Step-by-Step Breakdown
05:15 — Common Mistakes (Avoid These!)
08:00 — Pro Tips & Secret Hacks
10:30 — Final Recommendation

🔗 USEFUL LINKS:
• Subscribe: [Your Channel Link]
• Playlist: [Related Playlist]
• Instagram: [Your Handle]

📌 RELATED SEARCHES:
"""
    for term in rising_terms:
        desc += f"• {term}\n"

    desc += f"""
💬 Comment below: What should we cover next?

# {hashtag_base} #{hashtag_base}2026 #{hashtag_base}tips #{hashtag_base}guide #viral
"""
    return desc


def generate_tags(keyword: str, videos: list, rising: list) -> list:
    """Generate tags using top video tags + rising queries."""
    tag_counter = Counter()

    # Tags from top videos
    for v in videos:
        for t in v.get("tags", []):
            tag_counter[t.lower().strip()] += 1

    # Add keyword variations
    kw = keyword.lower().strip()
    variations = [
        kw,
        f"{kw} 2026",
        f"{kw} tutorial",
        f"{kw} guide",
        f"how to {kw}",
        f"best {kw}",
        f"{kw} tips",
        f"{kw} tricks",
        f"{kw} explained",
        f"{kw} in pakistan",
        f"{kw} urdu",
        f"{kw} hindi",
    ]
    for v in variations:
        tag_counter[v] += 5  # boost priority

    # Rising queries
    for r in rising[:10]:
        q = r.get("query", "").lower().strip()
        if q:
            tag_counter[q] += 3

    # Return top 25 tags
    return [tag for tag, _ in tag_counter.most_common(25)]


def viral_strategy_summary(patterns: dict, videos: list) -> list:
    """Create a human-readable strategy list."""
    strategy = []

    if patterns.get("curiosity", 0) >= 3:
        strategy.append("✅ **Curiosity Gap Title:** Top videos use curiosity ('secret', 'truth', 'nobody'). Use it in title within first 60 chars.")
    if patterns.get("negative", 0) >= 3:
        strategy.append("✅ **Loss Aversion:** Titles with 'stop/never/mistake' get higher CTR. Use loss framing.")
    if patterns.get("numbers", 0) >= 5:
        strategy.append("✅ **Listicles Work:** Numbers in titles (Top 5, 7 Tips) are dominant. Use them.")
    if patterns.get("question", 0) >= 3:
        strategy.append("✅ **Questions Hook Viewers:** Titles ending with '?' improve CTR by ~14%.")
    if patterns.get("urgency", 0) >= 3:
        strategy.append("✅ **Urgency Sells:** Include '2026', 'now', 'new' — trends show higher engagement.")

    # Timing insight
    strategy.append("⏰ **Upload Timing:** Post when Google Trends shows 'rising' (24-72h window) — competition is low, search volume is climbing.")
    strategy.append("🎯 **Thumbnail + Title A/B Test:** Run YouTube's native A/B test. If CTR < 3% in 48h, swap title.")

    # Engagement insight
    if videos:
        avg_views = sum(v["views"] for v in videos) / len(videos)
        avg_likes = sum(v["likes"] for v in videos) / len(videos)
        if avg_views > 0:
            like_ratio = (avg_likes / avg_views) * 100
            strategy.append(f"📊 **Engagement Benchmark:** Top 20 videos average {like_ratio:.2f}% like ratio. Aim to beat this.")

    return strategy


# ============================================================
# UI — MAIN APP
# ============================================================

st.markdown('<h1 class="main-header">🚀 Viral SEO Generator</h1>', unsafe_allow_html=True)
st.caption("Google Trends + YouTube Data → Clickbait Titles, SEO Descriptions & Tags")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    keyword = st.text_input("🔍 Keyword / Topic", value="chat gpt", help="E.g., cricket, ai tools, forex")
    region = st.selectbox("🌍 Region", ["PK", "IN", "US", "GB", "AE", "SA"], index=0)
    max_videos = st.slider("📹 Videos to Analyze", 10, 20, 20)

    st.markdown("---")
    st.markdown("### 📌 API Status")
    if YOUTUBE_API_KEY:
        st.success("YouTube API ✅")
    else:
        st.error("YouTube API ❌ — Add key in .env")

    st.markdown("---")
    st.caption("Made with ❤️ for creators")

# --- Main Button ---
if st.button("🔥 Analyze & Generate", use_container_width=True):

    if not keyword.strip():
        st.warning("Please enter a keyword first.")
        st.stop()

    # ---------------- STEP 1: Google Trends ----------------
    with st.spinner("📈 Fetching Google Trends data..."):
        trends_data = get_google_trends(keyword, region)

    # ---------------- STEP 2: YouTube Videos ----------------
    with st.spinner("📹 Analyzing top 20 YouTube videos..."):
        yt_data = get_youtube_top_videos(keyword, region, max_videos)

    if "error" in yt_data and not yt_data.get("videos"):
        st.error(f"YouTube API Error: {yt_data['error']}")
        st.info("Make sure YOUTUBE_API_KEY is correctly set in .env file.")
        st.stop()

    videos = yt_data.get("videos", [])
    rising = trends_data.get("rising", [])
    top_queries = trends_data.get("top", [])

    # ---------------- STEP 3: Pattern Analysis ----------------
    patterns = extract_title_patterns(videos)

    # ---------------- STEP 4: Generate Output ----------------
    titles = generate_clickbait_titles(keyword, patterns, rising)
    description = generate_description(keyword, rising, [v["title"] for v in videos])
    tags = generate_tags(keyword, videos, rising)
    strategy = viral_strategy_summary(patterns, videos)

    # ============================================================
    # DASHBOARD
    # ============================================================

    # --- Top Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    avg_views = total_views // len(videos) if videos else 0

    col1.metric("📹 Videos Analyzed", len(videos))
    col2.metric("👀 Total Views", f"{total_views:,}")
    col3.metric("👍 Total Likes", f"{total_likes:,}")
    col4.metric("📊 Avg Views/Video", f"{avg_views:,}")

    st.markdown("---")

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Trends", "🎬 Top 20 Videos", "✍️ Titles", "📝 Description", "🏷️ Tags & Strategy"]
    )

    # ---------------- TAB 1: TRENDS ----------------
    with tab1:
        st.subheader(f"Google Trends — '{keyword}' ({region})")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("### 🔥 Rising Queries")
            if rising:
                for r in rising[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{r.get("query", "N/A")}</b> — '
                        f'<span style="color:#ff0000;">+{r.get("value", 0)}%</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No rising queries (trend may be stable).")

        with c2:
            st.markdown("### 🏆 Top Queries")
            if top_queries:
                for t in top_queries[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{t.get("query", "N/A")}</b> — Value: {t.get("value", 0)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No top query data.")

    # ---------------- TAB 2: VIDEOS ----------------
    with tab2:
        st.subheader("Top 20 Viral Videos Analysis")

        if videos:
            df = pd.DataFrame(videos)[["title", "channel", "views", "likes", "comments", "published", "url"]]
            df["CTR_Like_%"] = (df["likes"] / df["views"] * 100).round(2)

            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "url": st.column_config.LinkColumn("Watch"),
                    "views": st.column_config.NumberColumn("Views", format="%d"),
                },
            )

            # Chart
            fig = px.bar(
                df.head(10),
                x="views",
                y="title",
                orientation="h",
                title="Top 10 by Views",
                color="views",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=450, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

            # Pattern analysis
            st.markdown("### 🧠 Detected Title Patterns")
            pattern_df = pd.DataFrame([
                {"Pattern": k.replace("_", " ").title(), "Count": v}
                for k, v in patterns.items() if v > 0
            ]).sort_values("Count", ascending=False)

            if not pattern_df.empty:
                fig2 = px.bar(
                    pattern_df, x="Pattern", y="Count",
                    color="Count", color_continuous_scale="OrRd",
                    title="What Makes These Titles Viral?",
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("No videos found.")

    # ---------------- TAB 3: TITLES ----------------
    with tab3:
        st.subheader("🎯 Clickbait Titles (Copy-Paste Ready)")
        st.caption("Based on top 20 viral video patterns + trending search terms")

        for i, t in enumerate(titles, 1):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f'<div class="title-box">#{i} — {t}</div>', unsafe_allow_html=True)
            with col_b:
                st.code(t, language="text")

        st.markdown("---")
        st.markdown("### 💡 Title Writing Rules")
        st.markdown("""
        - **Length:** 50–65 characters (mobile-friendly)
        - **Hook:** Curiosity / Loss / Transformation
        - **A/B Test:** Run 2–3 title variations for 48h
        - **Avoid:** ALL CAPS in whole title (only 1-2 words)
        """)

    # ---------------- TAB 4: DESCRIPTION ----------------
    with tab4:
        st.subheader("📝 SEO-Optimized Description")
        st.caption("Primary keyword in first 150 chars, timestamps, hashtags, CTA included")
        st.text_area("Copy this:", description, height=450, key="desc_area")
        st.download_button(
            "📥 Download Description",
            data=description,
            file_name=f"{keyword.replace(' ', '_')}_description.txt",
            mime="text/plain",
        )

    # ---------------- TAB 5: TAGS & STRATEGY ----------------
    with tab5:
        col_t, col_s = st.columns([1, 1])

        with col_t:
            st.subheader("🏷️ SEO Tags (Top 25)")
            tag_str = ", ".join(tags)
            st.code(tag_str, language="text")
            st.caption(f"Total characters: {len(tag_str)}/500 (YouTube limit)")

            st.download_button(
                "📥 Download Tags",
                data=tag_str,
                file_name=f"{keyword.replace(' ', '_')}_tags.txt",
                mime="text/plain",
            )

        with col_s:
            st.subheader("📊 Viral Strategy")
            for s in strategy:
                st.markdown(f"- {s}")

    # --- Footer ---
    st.markdown("---")
    st.caption(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data: Google Trends + YouTube API v3")


else:
    # --- Landing State ---
    st.info("👈 Enter a keyword in the sidebar and click **🔥 Analyze & Generate** to start.")

    st.markdown("### 🎯 What This App Does")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **📈 Google Trends**
        - Rising & top queries
        - Region-specific
        - Real-time demand
        """)
    with c2:
        st.markdown("""
        **📹 YouTube Analysis**
        - Top 20 videos by views
        - Pattern detection
        - Engagement benchmarks
        """)
    with c3:
        st.markdown("""
        **🚀 Auto-Generated SEO**
        - Clickbait titles
        - Full descriptions
        - Optimized tags
        """)

    st.markdown("### ⚙️ Setup Checklist")
    st.markdown("""
    1. ✅ Install: `pip install -r requirements.txt`
    2. ✅ Get YouTube API key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
    3. ✅ Add key to `.env`: `YOUTUBE_API_KEY=your_key_here`
    4. ✅ Run: `streamlit run app.py`
    """)
