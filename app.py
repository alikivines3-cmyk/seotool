import os
import re
from datetime import datetime
from collections import Counter

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from pytrends.request import TrendReq
from googleapiclient.discovery import build


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="Viral SEO Generator",
    page_icon="🚀",
    layout="wide",
)

# Streamlit Cloud Secrets support
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
if not YOUTUBE_API_KEY:
    try:
        YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
    except Exception:
        pass

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff0000, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .title-box {
        background: #f0f2f6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #ff0000;
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
# HELPERS
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends(keyword: str, region: str = "PK"):
    try:
        pytrends = TrendReq(hl="en-US", tz=300, timeout=(10, 25))
        pytrends.build_payload([keyword], timeframe="now 7-d", geo=region)
        related = pytrends.related_queries()
        rising = related.get(keyword, {}).get("rising")
        top = related.get(keyword, {}).get("top")

        rising_list = rising.head(10).to_dict("records") if rising is not None and not rising.empty else []
        top_list = top.head(10).to_dict("records") if top is not None and not top.empty else []
        return {"rising": rising_list, "top": top_list}
    except Exception as e:
        return {"error": str(e), "rising": [], "top": []}


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_top_videos(keyword: str, region: str = "PK", max_results: int = 20):
    if not YOUTUBE_API_KEY:
        return {"error": "YouTube API key missing. Add YOUTUBE_API_KEY in Streamlit Secrets.", "videos": []}
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        search_resp = youtube.search().list(
            q=keyword, part="snippet", type="video",
            maxResults=max_results, order="viewCount",
            regionCode=region, relevanceLanguage="en",
        ).execute()

        video_ids = [i["id"]["videoId"] for i in search_resp.get("items", [])]
        if not video_ids:
            return {"error": "No videos found.", "videos": []}

        stats_resp = youtube.videos().list(
            part="statistics,snippet", id=",".join(video_ids)
        ).execute()

        videos = []
        for item in stats_resp.get("items", []):
            s = item["statistics"]
            sn = item["snippet"]
            videos.append({
                "video_id": item["id"],
                "title": sn["title"],
                "channel": sn["channelTitle"],
                "published": sn["publishedAt"][:10],
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "tags": sn.get("tags", []),
                "url": f"https://youtube.com/watch?v={item['id']}",
            })
        videos.sort(key=lambda x: x["views"], reverse=True)
        return {"videos": videos[:20]}
    except Exception as e:
        return {"error": str(e), "videos": []}


def extract_title_patterns(videos):
    patterns = {k: 0 for k in ["numbers", "question", "how_to", "negative",
                                "brackets", "caps_words", "curiosity", "urgency"]}
    number_re = re.compile(r"\b\d+\b")
    caps_re = re.compile(r"\b[A-Z]{3,}\b")
    negative_words = ["stop", "never", "don't", "mistake", "wrong", "avoid", "fail", "won't"]
    curiosity_words = ["secret", "truth", "nobody", "no one", "revealed", "hidden", "actually", "really"]
    urgency_words = ["now", "today", "fast", "quick", "2024", "2025", "2026", "new"]

    for v in videos:
        t = v["title"].lower()
        if number_re.search(t): patterns["numbers"] += 1
        if "?" in t: patterns["question"] += 1
        if "how to" in t: patterns["how_to"] += 1
        if any(w in t for w in negative_words): patterns["negative"] += 1
        if "[" in t or "(" in t: patterns["brackets"] += 1
        if caps_re.search(v["title"]): patterns["caps_words"] += 1
        if any(w in t for w in curiosity_words): patterns["curiosity"] += 1
        if any(w in t for w in urgency_words): patterns["urgency"] += 1
    return patterns


def generate_clickbait_titles(keyword, patterns, rising):
    kw = keyword.title()
    year = datetime.now().year
    rising_terms = [r.get("query", "") for r in rising[:3] if r.get("query")]
    bonus = rising_terms[0] if rising_terms else keyword

    titles = [
        f"STOP Doing This With {kw} — You're Losing Money!",
        f"The TRUTH About {kw} Nobody Tells You ({year})",
        f"I Tried {kw} for 30 Days — Here's What Happened",
        f"How to {kw} in {year} (SECRET Method Revealed)",
        f"Why 99% of People FAIL at {kw} — Do THIS Instead",
        f"{kw}: 7 Mistakes You're Making RIGHT NOW",
        f"The ONLY {kw} Guide You'll Ever Need",
        f"Top 5 {kw} Secrets Experts Are Hiding",
        f"{bonus} — What Nobody Told You!",
        f"5-Minute {kw} Hack (Works Instantly!)",
        f"Don't Try {kw} Until You Watch This",
        f"How {kw} Will Change Everything in {year}",
    ]
    if patterns.get("numbers", 0) > 5:
        titles.append(f"10 {kw} Tricks That Actually Work in {year}")
    if patterns.get("curiosity", 0) > 3:
        titles.append(f"The Hidden Side of {kw} Nobody Wants You to Know")
    if patterns.get("negative", 0) > 3:
        titles.append(f"Never Do This With {kw} (It's Ruining Your Results)")
    return titles


def generate_description(keyword, rising):
    kw = keyword.title()
    year = datetime.now().year
    rising_terms = [r.get("query", "") for r in rising[:5] if r.get("query")]
    hashtag = keyword.replace(" ", "")

    desc = f"""🎯 {kw} — Complete Guide ({year})

In this video, we break down everything about {keyword} — latest updates, hidden tips, and the exact strategy top creators are using RIGHT NOW.

⏱️ TIMESTAMPS:
00:00 — Intro: Why {kw} Matters
00:45 — The Truth About {kw}
02:30 — Step-by-Step Breakdown
05:15 — Common Mistakes (Avoid These!)
08:00 — Pro Tips & Secret Hacks
10:30 — Final Recommendation

🔗 USEFUL LINKS:
• Subscribe: [Your Channel Link]
• Playlist: [Related Playlist]

📌 RELATED SEARCHES:
"""
    for term in rising_terms:
        desc += f"• {term}\n"

    desc += f"""
💬 Comment below: What should we cover next?

# {hashtag} #{hashtag}{year} #{hashtag}tips #{hashtag}guide #viral
"""
    return desc


def generate_tags(keyword, videos, rising):
    counter = Counter()
    for v in videos:
        for t in v.get("tags", []):
            counter[t.lower().strip()] += 1

    kw = keyword.lower().strip()
    variations = [
        kw, f"{kw} {datetime.now().year}", f"{kw} tutorial", f"{kw} guide",
        f"how to {kw}", f"best {kw}", f"{kw} tips", f"{kw} tricks",
        f"{kw} explained", f"{kw} in pakistan", f"{kw} urdu", f"{kw} hindi",
    ]
    for v in variations:
        counter[v] += 5

    for r in rising[:10]:
        q = r.get("query", "").lower().strip()
        if q:
            counter[q] += 3

    return [t for t, _ in counter.most_common(25)]


def viral_strategy_summary(patterns, videos):
    strategy = []
    if patterns.get("curiosity", 0) >= 3:
        strategy.append("✅ **Curiosity Gap:** Titles with 'secret/truth/nobody' get higher CTR.")
    if patterns.get("negative", 0) >= 3:
        strategy.append("✅ **Loss Aversion:** 'Stop/never/mistake' framing works.")
    if patterns.get("numbers", 0) >= 5:
        strategy.append("✅ **Listicles:** Numbers in titles (Top 5, 7 Tips) dominate.")
    if patterns.get("question", 0) >= 3:
        strategy.append("✅ **Questions:** Titles ending with '?' improve CTR ~14%.")
    if patterns.get("urgency", 0) >= 3:
        strategy.append("✅ **Urgency:** Include year, 'now', 'new' — higher engagement.")

    strategy.append("⏰ **Upload Timing:** Post during 'rising' phase (24–72h window) — low competition.")
    strategy.append("🎯 **A/B Test:** If CTR < 3% in 48h, swap thumbnail + title.")

    if videos:
        avg_v = sum(v["views"] for v in videos) / len(videos)
        avg_l = sum(v["likes"] for v in videos) / len(videos)
        if avg_v > 0:
            strategy.append(f"📊 **Benchmark:** Top 20 videos avg like ratio: {(avg_l/avg_v)*100:.2f}%")
    return strategy


# ============================================================
# UI
# ============================================================

st.markdown('<h1 class="main-header">🚀 Viral SEO Generator</h1>', unsafe_allow_html=True)
st.caption("Google Trends + YouTube Top 20 Analysis → Clickbait Titles, SEO Description & Tags")

with st.sidebar:
    st.header("⚙️ Settings")
    keyword = st.text_input("🔍 Keyword / Topic", value="chat gpt")
    region = st.selectbox("🌍 Region", ["PK", "IN", "US", "GB", "AE", "SA"], index=0)
    max_videos = st.slider("📹 Videos to Analyze", 10, 20, 20)

    st.markdown("---")
    st.markdown("### 🔑 API Status")
    if YOUTUBE_API_KEY:
        st.success("YouTube API ✅")
    else:
        st.error("API key missing ❌")

    st.markdown("---")
    st.caption("Made with ❤️ for creators")


if st.button("🔥 Analyze & Generate", use_container_width=True):
    if not keyword.strip():
        st.warning("Pehle keyword daalein.")
        st.stop()

    with st.spinner("📈 Google Trends fetch ho raha hai..."):
        trends = get_google_trends(keyword, region)

    with st.spinner("📹 Top 20 YouTube videos analyze ho rahe hain..."):
        yt = get_youtube_top_videos(keyword, region, max_videos)

    if "error" in yt and not yt.get("videos"):
        st.error(f"YouTube Error: {yt['error']}")
        st.stop()

    videos = yt.get("videos", [])
    rising = trends.get("rising", [])
    top_q = trends.get("top", [])

    patterns = extract_title_patterns(videos)
    titles = generate_clickbait_titles(keyword, patterns, rising)
    description = generate_description(keyword, rising)
    tags = generate_tags(keyword, videos, rising)
    strategy = viral_strategy_summary(patterns, videos)

    # --- Metrics ---
    c1, c2, c3, c4 = st.columns(4)
    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    avg_views = total_views // len(videos) if videos else 0
    c1.metric("📹 Videos", len(videos))
    c2.metric("👀 Total Views", f"{total_views:,}")
    c3.metric("👍 Total Likes", f"{total_likes:,}")
    c4.metric("📊 Avg Views", f"{avg_views:,}")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Trends", "🎬 Videos", "✍️ Titles", "📝 Description", "🏷️ Tags & Strategy"]
    )

    with tab1:
        st.subheader(f"Google Trends — '{keyword}' ({region})")
        a, b = st.columns(2)
        with a:
            st.markdown("### 🔥 Rising Queries")
            if rising:
                for r in rising[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{r.get("query","")}</b> — '
                        f'<span style="color:#ff0000;">+{r.get("value",0)}%</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No rising queries data.")
        with b:
            st.markdown("### 🏆 Top Queries")
            if top_q:
                for t in top_q[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{t.get("query","")}</b> — {t.get("value",0)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No top query data.")

    with tab2:
        st.subheader("Top 20 Viral Videos")
        if videos:
            df = pd.DataFrame(videos)[["title", "channel", "views", "likes", "comments", "published", "url"]]
            df["Like %"] = (df["likes"] / df["views"] * 100).round(2)
            st.dataframe(
                df, use_container_width=True,
                column_config={"url": st.column_config.LinkColumn("Watch")},
            )

            st.markdown("### 📊 Top 10 by Views")
            chart_df = df.head(10).set_index("title")["views"]
            st.bar_chart(chart_df, color="#ff0000")

            st.markdown("### 🧠 Viral Title Patterns")
            pdata = pd.DataFrame([
                {"Pattern": k.replace("_", " ").title(), "Count": v}
                for k, v in patterns.items() if v > 0
            ]).sort_values("Count", ascending=False)
            if not pdata.empty:
                st.bar_chart(pdata.set_index("Pattern")["Count"], color="#ff6b6b")
        else:
            st.warning("No videos found.")

    with tab3:
        st.subheader("🎯 Clickbait Titles")
        st.caption("Copy karein aur YouTube Studio mein paste karein")
        for i, t in enumerate(titles, 1):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f'<div class="title-box">#{i} — {t}</div>', unsafe_allow_html=True)
            with col_b:
                st.code(t, language="text")

        st.markdown("---")
        st.markdown("""
        **Title Rules:**
        - Length: 50–65 characters
        - Hook: Curiosity / Loss / Transformation
        - A/B test 2–3 variations for 48h
        """)

    with tab4:
        st.subheader("📝 SEO Description")
        st.text_area("Copy:", description, height=420)
        st.download_button(
            "📥 Download Description",
            description,
            file_name=f"{keyword.replace(' ', '_')}_description.txt",
        )

    with tab5:
        col_t, col_s = st.columns(2)
        with col_t:
            st.subheader("🏷️ Top 25 Tags")
            tag_str = ", ".join(tags)
            st.code(tag_str, language="text")
            st.caption(f"{len(tag_str)}/500 chars")
            st.download_button(
                "📥 Download Tags",
                tag_str,
                file_name=f"{keyword.replace(' ', '_')}_tags.txt",
            )
        with col_s:
            st.subheader("📊 Viral Strategy")
            for s in strategy:
                st.markdown(f"- {s}")

    st.markdown("---")
    st.caption(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Google Trends + YouTube API v3")

else:
    st.info("👈 Sidebar mein keyword daalein aur **🔥 Analyze & Generate** dabayein.")
    st.markdown("### 🎯 Yeh App Kya Karti Hai")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**📈 Trends**\n- Rising queries\n- Region-specific\n- Real-time demand")
    with c2:
        st.markdown("**📹 YouTube**\n- Top 20 videos\n- Pattern detection\n- Engagement data")
    with c3:
        st.markdown("**🚀 SEO Output**\n- Clickbait titles\n- Full description\n- 25 optimized tags")
