import os
import re
from datetime import datetime
from collections import Counter

import streamlit as st
import pandas as pd

from pytrends.request import TrendReq
from googleapiclient.discovery import build


st.set_page_config(
    page_title="Viral SEO Generator",
    page_icon="🚀",
    layout="wide",
)

# API key: Streamlit Secrets se, warna environment variable se
YOUTUBE_API_KEY = ""
try:
    YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
except Exception:
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem; font-weight: 800;
        background: linear-gradient(90deg, #ff0000, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .title-box {
        background: #f0f2f6; padding: 12px; border-radius: 8px;
        margin-bottom: 8px; border-left: 4px solid #ff0000; color: #000;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def get_google_trends(keyword, region="PK"):
    try:
        pt = TrendReq(hl="en-US", tz=300, timeout=(10, 25))
        pt.build_payload([keyword], timeframe="now 7-d", geo=region)
        related = pt.related_queries()
        rising = related.get(keyword, {}).get("rising")
        top = related.get(keyword, {}).get("top")
        rising_list = rising.head(10).to_dict("records") if rising is not None and not rising.empty else []
        top_list = top.head(10).to_dict("records") if top is not None and not top.empty else []
        return {"rising": rising_list, "top": top_list}
    except Exception as e:
        return {"error": str(e), "rising": [], "top": []}


@st.cache_data(ttl=1800, show_spinner=False)
def get_youtube_videos(keyword, region="PK", max_results=20):
    if not YOUTUBE_API_KEY:
        return {"error": "YouTube API key missing in Secrets.", "videos": []}
    try:
        yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        s_resp = yt.search().list(
            q=keyword, part="snippet", type="video",
            maxResults=max_results, order="viewCount",
            regionCode=region, relevanceLanguage="en",
        ).execute()
        ids = [i["id"]["videoId"] for i in s_resp.get("items", [])]
        if not ids:
            return {"error": "No videos found.", "videos": []}
        v_resp = yt.videos().list(part="statistics,snippet", id=",".join(ids)).execute()
        videos = []
        for item in v_resp.get("items", []):
            s = item["statistics"]
            sn = item["snippet"]
            videos.append({
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


def extract_patterns(videos):
    p = {k: 0 for k in ["numbers", "question", "how_to", "negative",
                        "brackets", "caps", "curiosity", "urgency"]}
    num_re = re.compile(r"\b\d+\b")
    caps_re = re.compile(r"\b[A-Z]{3,}\b")
    neg = ["stop", "never", "don't", "mistake", "wrong", "avoid", "fail"]
    cur = ["secret", "truth", "nobody", "no one", "revealed", "hidden"]
    urg = ["now", "today", "fast", "quick", "2024", "2025", "2026", "new"]
    for v in videos:
        t = v["title"].lower()
        if num_re.search(t): p["numbers"] += 1
        if "?" in t: p["question"] += 1
        if "how to" in t: p["how_to"] += 1
        if any(w in t for w in neg): p["negative"] += 1
        if "[" in t or "(" in t: p["brackets"] += 1
        if caps_re.search(v["title"]): p["caps"] += 1
        if any(w in t for w in cur): p["curiosity"] += 1
        if any(w in t for w in urg): p["urgency"] += 1
    return p


def make_titles(keyword, patterns, rising):
    kw = keyword.title()
    year = datetime.now().year
    r = [x.get("query", "") for x in rising[:3] if x.get("query")]
    bonus = r[0] if r else keyword
    t = [
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
        t.append(f"10 {kw} Tricks That Actually Work in {year}")
    if patterns.get("curiosity", 0) > 3:
        t.append(f"The Hidden Side of {kw} Nobody Wants You to Know")
    if patterns.get("negative", 0) > 3:
        t.append(f"Never Do This With {kw} (It's Ruining Your Results)")
    return t


def make_desc(keyword, rising):
    kw = keyword.title()
    year = datetime.now().year
    r = [x.get("query", "") for x in rising[:5] if x.get("query")]
    h = keyword.replace(" ", "")
    d = f"""🎯 {kw} — Complete Guide ({year})

In this video, we break down everything about {keyword} — latest updates, hidden tips, and the exact strategy top creators use RIGHT NOW.

⏱️ TIMESTAMPS:
00:00 — Intro: Why {kw} Matters
00:45 — The Truth About {kw}
02:30 — Step-by-Step Breakdown
05:15 — Common Mistakes (Avoid!)
08:00 — Pro Tips & Secret Hacks
10:30 — Final Recommendation

🔗 USEFUL LINKS:
• Subscribe: [Your Channel]
• Playlist: [Related]

📌 RELATED SEARCHES:
"""
    for x in r:
        d += f"• {x}\n"
    d += f"""

💬 Comment below: What next?

# {h} #{h}{year} #{h}tips #{h}guide #viral
"""
    return d


def make_tags(keyword, videos, rising):
    c = Counter()
    for v in videos:
        for t in v.get("tags", []):
            c[t.lower().strip()] += 1
    kw = keyword.lower().strip()
    for v in [kw, f"{kw} {datetime.now().year}", f"{kw} tutorial", f"{kw} guide",
              f"how to {kw}", f"best {kw}", f"{kw} tips", f"{kw} tricks",
              f"{kw} explained", f"{kw} in pakistan", f"{kw} urdu", f"{kw} hindi"]:
        c[v] += 5
    for x in rising[:10]:
        q = x.get("query", "").lower().strip()
        if q: c[q] += 3
    return [t for t, _ in c.most_common(25)]


def make_strategy(patterns, videos):
    s = []
    if patterns.get("curiosity", 0) >= 3:
        s.append("✅ **Curiosity Gap:** 'secret/truth/nobody' titles = higher CTR")
    if patterns.get("negative", 0) >= 3:
        s.append("✅ **Loss Aversion:** 'stop/never/mistake' framing works")
    if patterns.get("numbers", 0) >= 5:
        s.append("✅ **Listicles:** Numbers (Top 5, 7 Tips) dominate")
    if patterns.get("question", 0) >= 3:
        s.append("✅ **Questions:** '?' titles improve CTR ~14%")
    if patterns.get("urgency", 0) >= 3:
        s.append("✅ **Urgency:** Include year / now / new")
    s.append("⏰ **Upload Timing:** Post during 'rising' phase (24–72h window)")
    s.append("🎯 **A/B Test:** If CTR < 3% in 48h, swap thumbnail + title")
    if videos:
        av = sum(v["views"] for v in videos) / len(videos)
        al = sum(v["likes"] for v in videos) / len(videos)
        if av > 0:
            s.append(f"📊 **Benchmark:** Top 20 avg like ratio: {(al/av)*100:.2f}%")
    return s


st.markdown('<h1 class="main-header">🚀 Viral SEO Generator</h1>', unsafe_allow_html=True)
st.caption("Google Trends + YouTube Top 20 → Titles, Descriptions, Tags")

with st.sidebar:
    st.header("⚙️ Settings")
    keyword = st.text_input("🔍 Keyword", value="chat gpt")
    region = st.selectbox("🌍 Region", ["PK", "IN", "US", "GB", "AE", "SA"], index=0)
    max_videos = st.slider("📹 Videos", 10, 20, 20)
    st.markdown("---")
    st.markdown("### 🔑 API Status")
    st.success("YouTube API ✅") if YOUTUBE_API_KEY else st.error("API key missing ❌")

if st.button("🔥 Analyze & Generate", use_container_width=True):
    if not keyword.strip():
        st.warning("Keyword daalein.")
        st.stop()

    with st.spinner("📈 Trends fetch ho rahe hain..."):
        trends = get_google_trends(keyword, region)
    with st.spinner("📹 YouTube videos analyze ho rahe hain..."):
        yt = get_youtube_videos(keyword, region, max_videos)

    if "error" in yt and not yt.get("videos"):
        st.error(f"YouTube Error: {yt['error']}")
        st.stop()

    videos = yt.get("videos", [])
    rising = trends.get("rising", [])
    top_q = trends.get("top", [])
    patterns = extract_patterns(videos)
    titles = make_titles(keyword, patterns, rising)
    description = make_desc(keyword, rising)
    tags = make_tags(keyword, videos, rising)
    strategy = make_strategy(patterns, videos)

    c1, c2, c3, c4 = st.columns(4)
    tv = sum(v["views"] for v in videos)
    tl = sum(v["likes"] for v in videos)
    av = tv // len(videos) if videos else 0
    c1.metric("📹 Videos", len(videos))
    c2.metric("👀 Total Views", f"{tv:,}")
    c3.metric("👍 Total Likes", f"{tl:,}")
    c4.metric("📊 Avg Views", f"{av:,}")

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Trends", "🎬 Videos", "✍️ Titles", "📝 Description", "🏷️ Tags & Strategy"]
    )

    with tab1:
        st.subheader(f"Google Trends — '{keyword}' ({region})")
        a, b = st.columns(2)
        with a:
            st.markdown("### 🔥 Rising")
            if rising:
                for r in rising[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{r.get("query","")}</b> — '
                        f'<span style="color:#ff0000;">+{r.get("value",0)}%</span></div>',
                        unsafe_allow_html=True)
            else:
                st.info("No rising data.")
        with b:
            st.markdown("### 🏆 Top")
            if top_q:
                for t in top_q[:10]:
                    st.markdown(
                        f'<div class="title-box"><b>{t.get("query","")}</b> — {t.get("value",0)}</div>',
                        unsafe_allow_html=True)
            else:
                st.info("No top data.")

    with tab2:
        st.subheader("Top 20 Viral Videos")
        if videos:
            df = pd.DataFrame(videos)[["title", "channel", "views", "likes", "comments", "published", "url"]]
            df["Like %"] = (df["likes"] / df["views"] * 100).round(2)
            st.dataframe(df, use_container_width=True,
                         column_config={"url": st.column_config.LinkColumn("Watch")})
            st.markdown("### 📊 Top 10 by Views")
            st.bar_chart(df.head(10).set_index("title")["views"], color="#ff0000")
            st.markdown("### 🧠 Title Patterns")
            pdata = pd.DataFrame([{"Pattern": k.replace("_", " ").title(), "Count": v}
                                  for k, v in patterns.items() if v > 0]).sort_values("Count", ascending=False)
            if not pdata.empty:
                st.bar_chart(pdata.set_index("Pattern")["Count"], color="#ff6b6b")
        else:
            st.warning("No videos.")

    with tab3:
        st.subheader("🎯 Clickbait Titles")
        for i, t in enumerate(titles, 1):
            st.markdown(f'<div class="title-box">#{i} — {t}</div>', unsafe_allow_html=True)

    with tab4:
        st.subheader("📝 SEO Description")
        st.text_area("Copy:", description, height=400)
        st.download_button("📥 Download", description,
                           file_name=f"{keyword.replace(' ', '_')}_desc.txt")

    with tab5:
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("🏷️ Top 25 Tags")
            tag_str = ", ".join(tags)
            st.code(tag_str, language="text")
            st.caption(f"{len(tag_str)}/500 chars")
            st.download_button("📥 Download Tags", tag_str,
                               file_name=f"{keyword.replace(' ', '_')}_tags.txt")
        with c_b:
            st.subheader("📊 Strategy")
            for s in strategy:
                st.markdown(f"- {s}")

    st.caption(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")

else:
    st.info("👈 Sidebar mein keyword daalein aur **🔥 Analyze & Generate** dabayein.")
