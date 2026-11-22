import streamlit as st
import pandas as pd
import requests
import random
import time
import urllib.parse
import re
from collections import Counter
from datetime import datetime

st.set_page_config(page_title="SEO Viral Engine Pro v3 - RPM + Thumbnail", page_icon="🔥", layout="wide")

st.markdown("""
<style>
.main {background: #0B0B14;}
.stButton>button {background: linear-gradient(90deg,#FF0055,#7B00FF); color:white; border:none; border-radius:12px; padding:12px 18px; font-weight:700; width:100%; font-size:15px;}
.card {background:#15151F; border:1px solid #2A2A3A; border-radius:16px; padding:18px; margin:10px 0;}
.viral-card {background: linear-gradient(135deg,#1A0A1A,#150A2A); border:1px solid #FF0055; border-radius:16px; padding:18px; margin:10px 0;}
.success-card {background:#0F2A1A; border:1px solid #00FF88; border-radius:12px; padding:15px; margin:10px 0;}
.money-card {background: linear-gradient(135deg,#0A2A1A,#0A1A2A); border:1px solid #FFC107; border-radius:16px; padding:18px; margin:10px 0;}
.thumb-card {background:#1E1E32; border:1px solid #7B00FF; border-radius:14px; padding:14px; margin:8px 0;}
.small {color:#9A9AB0; font-size:13px;}
h1,h2,h3 {color:white !important;}
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state: st.session_state.data = None
if "analysis" not in st.session_state: st.session_state.analysis = None
if "generated" not in st.session_state: st.session_state.generated = False

# ---------- AI ----------
def ai_generate(prompt):
    try:
        r = requests.post("https://text.pollinations.ai/openai", json={"model": "openai", "messages": [{"role": "user", "content": prompt}]}, timeout=40)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            if len(text) > 50: return text, "Pollinations AI FREE"
    except: pass
    try:
        clean = urllib.parse.quote(prompt[:1000])
        r = requests.get(f"https://text.pollinations.ai/{clean}?model=mistral", timeout=30)
        if r.status_code == 200 and len(r.text) > 50: return r.text, "Backup Mistral"
    except: pass
    return "AI busy - Template used.", "Template"

# ---------- SCORING ----------
def calc_title_score(title, power_words):
    score = 72
    if any(w in title.lower() for w in power_words): score += 10
    if "?" in title or "!" in title: score += 5
    if 45 <= len(title) <= 75: score += 8
    if any(w in title.lower() for w in ["kya","kyun","kaise","secret","truth","twist"]): score += 5
    return min(99, score)

def calc_tag_score(vol, comp):
    base = {"High": 88, "Very High": 95, "Medium": 70}[vol]
    bonus = {"Very Low": 7, "Low": 4, "Medium": -8}[comp]
    return min(99, base + bonus)

# ---------- RPM LOGIC - NEW ----------
def get_rpm_data():
    # Title Type -> RPM Estimate (Pakistan vs Worldwide)
    return [
        {"Title Type": "Shocking Twist / Ending Revealed", "Example": "Ending Revealed - Kya Hoga Agay?", "RPM Pakistan": "$0.40 - $0.90", "RPM Worldwide": "$2.50 - $5.00", "RPM Score": 92, "Why": "High CTR + Long Watch Time = Advertisers zyada pay karte hain"},
        {"Title Type": "Secret / Truth Exposed", "Example": "Secret Finally Exposed! Truth Samne Agaya", "RPM Pakistan": "$0.35 - $0.80", "RPM Worldwide": "$2.20 - $4.50", "RPM Score": 90, "Why": "Curiosity high, audience end tak dekhta hai"},
        {"Title Type": "Full Episode Explained", "Example": "Full Episode Explained in Urdu", "RPM Pakistan": "$0.50 - $1.10", "RPM Worldwide": "$3.00 - $6.00", "RPM Score": 95, "Why": "8+ min video, Mid-roll ads lagte hain, RPM sab se high"},
        {"Title Type": "Next Episode Prediction", "Example": "Next Episode Prediction - Bara Dhamaka", "RPM Pakistan": "$0.30 - $0.70", "RPM Worldwide": "$1.80 - $3.50", "RPM Score": 82, "Why": "Short video hota hai, kam ads"},
        {"Title Type": "Emotional / Sad Scene", "Example": "Emotional Scene Ne Sab Ko Rula Diya", "RPM Pakistan": "$0.25 - $0.60", "RPM Worldwide": "$1.50 - $3.00", "RPM Score": 78, "Why": "Views zyada but watch time kam"},
        {"Title Type": "Love Story / Proposal", "Example": "Proposal Scene - Finally Love Complete", "RPM Pakistan": "$0.20 - $0.50", "RPM Worldwide": "$1.20 - $2.50", "RPM Score": 70, "Why": "Low advertiser competition"},
        {"Title Type": "News / Celebrity Update", "Example": "Drama Actor Ka Bara Bayan Samne Agaya", "RPM Pakistan": "$0.45 - $0.95", "RPM Worldwide": "$2.80 - $5.50", "RPM Score": 88, "Why": "News advertisers high bid lagate hain"},
        {"Title Type": "Viral Scene / Best Scene (Short)", "Example": "Viral Scene! 5M Views Wala Moment", "RPM Pakistan": "$0.15 - $0.40", "RPM Worldwide": "$0.80 - $2.00", "RPM Score": 60, "Why": "Short video, 1 ad bhi mushkil se lagta hai"},
    ]

def estimate_rpm_for_title(title):
    t = title.lower()
    if "explained" in t or "full episode" in t: return "$0.50-$1.10 PK / $3.00-$6.00 WW", 95, "8+ min video banao, 2-3 mid-roll ads = RPM double"
    if "secret" in t or "truth" in t or "exposed" in t: return "$0.35-$0.80 PK / $2.20-$4.50 WW", 90, "End tak suspense rakho, retention high = RPM high"
    if "ending" in t or "twist" in t or "shocking" in t: return "$0.40-$0.90 PK / $2.50-$5.00 WW", 92, "Title me Twist + Thumbnail me Shocked Face"
    if "prediction" in t or "next episode" in t: return "$0.30-$0.70 PK / $1.80-$3.50 WW", 82, "Video ko 8 min tak le jao, RPM barhega"
    if "emotional" in t or "sad" in t: return "$0.25-$0.60 PK / $1.50-$3.00 WW", 78, "Emotion ke sath analysis add karo, length barhao"
    if "love" in t or "proposal" in t: return "$0.20-$0.50 PK / $1.20-$2.50 WW", 70, "Sirf love scene mat dikhao, story + twist add karo"
    if "viral" in t or "best scene" in t: return "$0.15-$0.40 PK / $0.80-$2.00 WW", 60, "Short clip se RPM kam hota hai, isko Explain video banao"
    return "$0.30-$0.70 PK / $1.80-$3.50 WW", 80, "Video 8+ min rakho"

def get_posting_time(target):
    if target == "Pakistan":
        return {"Best Time 1": "Raat 8:00 - 10:00 PM (PKT)", "Best Time 2": "Dopahar 1:00 - 2:00 PM (Lunch Break)", "Best Time 3": "Raat 11:00 PM (Late Night Viewers)", "Best Day": "Friday, Saturday, Sunday", "Reason": "Pakistan me drama raat ko dekha jata hai. Episode ke 2 ghante baad video dalo."}
    elif target == "India + Pakistan":
        return {"Best Time 1": "Raat 8:30 - 10:30 PM (PKT/IST)", "Best Time 2": "Shaam 6:00 - 7:00 PM", "Best Time 3": "Dopahar 12:30 PM", "Best Day": "Friday - Sunday", "Reason": "Dono countries ka prime time overlap raat 8:30 hai. Is time pe upload karo."}
    else:
        return {"Best Time 1": "Raat 9:00 PM PKT = 12:00 PM USA (EST)", "Best Time 2": "Subah 10:00 AM PKT = UK Evening", "Best Time 3": "Raat 11:00 PM PKT = USA Afternoon", "Best Day": "Saturday, Sunday", "Reason": "Worldwide audience ke liye USA + UK time ko target karo. English subtitles lazmi rakho."}

def get_thumbnail_idea(title, topic):
    t = title.lower()
    if "shocking" in t or "twist" in t: return {"Text": "SHOCKING!", "Face": "Shocked / Mouth Open Face", "Color": "Red + Yellow Bold Text", "Arrow": "Red Arrow + Circle on Face", "BG": "Dark + Drama Scene Blur"}
    if "secret" in t or "truth" in t: return {"Text": "SECRET EXPOSED!", "Face": "Finger on Lips / Serious Face", "Color": "Black + Yellow", "Arrow": "Question Mark + Blurred Face", "BG": "Mystery Dark Background"}
    if "ending" in t: return {"Text": "ENDING?", "Face": "Crying / Sad Face", "Color": "Red + White", "Arrow": "Big ? Mark", "BG": "Last Scene Screenshot"}
    if "emotional" in t or "sad" in t: return {"Text": "RULA DIYA 😢", "Face": "Crying Face Close-up", "Color": "Blue + White", "Arrow": "Tear Effect", "BG": "Emotional Scene"}
    if "love" in t or "proposal" in t: return {"Text": "FINALLY! ❤️", "Face": "Smiling Couple", "Color": "Pink + White", "Arrow": "Heart Shape", "BG": "Romantic Scene"}
    return {"Text": "MUST WATCH!", "Face": "Surprised Face", "Color": "Yellow + Black", "Arrow": "Red Circle", "BG": "Best Scene Screenshot"}

# ---------- WORLDWIDE HIGH RPM TAGS - ALAG SE ----------
def get_worldwide_rpm_tags():
    return pd.DataFrame([
        {"#": 1, "Worldwide High RPM Tag": "pakistani drama explained in english", "RPM Boost": "Very High", "Competition": "Low", "Score": 98, "Use": "Worldwide audience + English advertisers"},
        {"#": 2, "Worldwide High RPM Tag": "pakistani drama with english subtitles", "RPM Boost": "Very High", "Competition": "Low", "Score": 97, "Use": "USA/UK viewers attract karta hai"},
        {"#": 3, "Worldwide High RPM Tag": "drama review and analysis", "RPM Boost": "High", "Competition": "Low", "Score": 94, "Use": "Analysis = Long watch time"},
        {"#": 4, "Worldwide High RPM Tag": "pakistani drama reaction", "RPM Boost": "High", "Competition": "Low", "Score": 93, "Use": "Reaction videos ka RPM high hota hai"},
        {"#": 5, "Worldwide High RPM Tag": "urdu drama hindi dubbed", "RPM Boost": "High", "Competition": "Very Low", "Score": 92, "Use": "India audience bhi cover"},
        {"#": 6, "Worldwide High RPM Tag": "pakistani drama ost review", "RPM Boost": "High", "Competition": "Low", "Score": 91, "Use": "Music advertisers high pay karte hain"},
        {"#": 7, "Worldwide High RPM Tag": "best pakistani drama 2026", "RPM Boost": "High", "Competition": "Low", "Score": 90, "Use": "Yearly search high rehta hai"},
        {"#": 8, "Worldwide High RPM Tag": "pakistani drama news update", "RPM Boost": "Very High", "Competition": "Low", "Score": 95, "Use": "News category ka RPM sab se high"},
        {"#": 9, "Worldwide High RPM Tag": "drama episode breakdown", "RPM Boost": "High", "Competition": "Very Low", "Score": 93, "Use": "English keyword = Worldwide RPM"},
        {"#": 10, "Worldwide High RPM Tag": "pakistani drama full story explained", "RPM Boost": "Very High", "Competition": "Low", "Score": 96, "Use": "Long video + High RPM combo"},
    ])

# ---------- YOUTUBE TOP 20 ----------
def get_top_20(query):
    api_key = ""
    try: api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    except: api_key = ""
    if api_key:
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "q": query, "type": "video", "order": "viewCount", "maxResults": 20, "key": api_key, "regionCode": "PK"}, timeout=15)
            if r.status_code == 200:
                videos = []
                for it in r.json().get("items", []):
                    vid = it["id"].get("videoId", "")
                    vr = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "statistics", "id": vid, "key": api_key}, timeout=10)
                    views, likes = 0, 0
                    if vr.status_code == 200 and vr.json().get("items"):
                        s = vr.json()["items"][0]["statistics"]; views = int(s.get("viewCount", 0)); likes = int(s.get("likeCount", 0))
                    videos.append({"Title": it["snippet"]["title"], "Channel": it["snippet"]["channelTitle"], "Published": it["snippet"]["publishedAt"][:10], "Views": views, "Likes": likes, "VideoID": vid, "Thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "URL": f"https://youtube.com/watch?v={vid}"})
                return videos, "YouTube Data v3 LIVE"
        except Exception as e: st.warning(f"YouTube API failed: {e}")
    patterns = ["SHOCKING Twist - Sab Kuch Badal Gaya","Ending Revealed - Kya Hoga Agay?","Full Episode Explained in Urdu","Truth Exposed - Hidden Secret Samne Agaya","Kya Hoga Agay? Next Episode Prediction","Secret Revealed - Hero Ka Asli Chehra","Emotional Scene - Sab Ro Paray","Big Fight - Family Me Tofan","Proposal Scene - Finally Love Story Complete","Death Twist - Sab Shocked Reh Gaye","New Entry - Story Me Bara Change","Love Story - Dil Jeet Liya","Revenge Plan - Ab Badla Hoga","Hidden Truth - 10 Saal Baad Pata Chala","Family Drama - Ghar Me Larai","Sad Ending - Last Scene Rula Dega","Happy Ending - Sab Khush","Viral Scene - 5M Views Cross","Best Scene - Top Moment","Full Episode Review - Must Watch"]
    demo_ids = ["dQw4w9WgXcQ","LXb3EKWsInQ","eKFTSSKCzWA","JGwWNGJdvx8","kXYiU_JCYtU","RgKAFK5djSk","OPf0YbXqDm0","09R8_2nJtjg","hTWKbfoikeg","pRpeEdMmmQ0","hLQl3WQQoQ0","uelHwf8o7_U","YQHsXMglC9A","fJ9rUzIMcZQ","60ItHLz5WEA","kffacxfA7Gg","SlPhMPnQ-Og","oHg5SJYRHA0","QH2-TGUlwu4","nfWlot6h_JM"]
    videos = []
    for i, p in enumerate(patterns):
        v = random.randint(600000, 5200000); vid = demo_ids[i]
        videos.append({"Title": f"{query} - {p} | Episode Review", "Channel": f"Drama World {i+1}", "Published": "2026-11-20", "Views": v, "Likes": int(v*0.06), "VideoID": vid, "Thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "URL": f"https://youtube.com/watch?v={vid}", "Tags": f"{query.lower()}, {p.lower()}, pakistani drama, drama review, viral drama"})
    return videos, "Demo Mode - Real Viral Pattern"

def get_trends(keyword):
    try:
        from pytrends.request import TrendReq
        py = TrendReq(hl='en-US', tz=300); py.build_payload([keyword], timeframe='now 7-d', geo='PK'); df = py.interest_over_time()
        if not df.empty:
            df2 = df.reset_index().rename(columns={keyword: "Interest"}); return df2[["Date","Interest"]], "PyTrends LIVE"
    except: pass
    return pd.DataFrame({"Date": pd.date_range("2026-11-15", periods=7), "Interest": [45,60,78,90,85,95,99]}), "PyTrends Demo"

def analyze_why_viral(df):
    all_titles = " ".join(df["Title"].tolist()).lower(); words = re.findall(r'\b\w+\b', all_titles); common = Counter(words).most_common(10)
    power = ["shocking","revealed","exposed","secret","truth","ending","twist","viral","emotional","big"]
    return {"avg_views": int(df["Views"].mean()), "top_video": df.sort_values("Views", ascending=False).iloc[0], "common_words": common, "power_words": [w for w in power if w in all_titles], "avg_len": int(df["Title"].apply(len).mean()), "total_views": int(df["Views"].sum())}

# ---------- HEADER ----------
st.title("🔥 SEO Viral Engine Pro v3")
st.markdown("**Top 20 Analysis + Thumbnail Ideas + Posting Time Calculator + RPM Booster + Worldwide High RPM Tags**")
with st.sidebar:
    st.title("🔥 SEO Viral Engine")
    st.write("✅ Top 20 With Thumbnails")
    st.write("✅ Thumbnail Generator")
    st.write("✅ Posting Time Calculator")
    st.write("✅ RPM Calculator + Booster")
    st.write("✅ Worldwide High RPM Tags")
    st.divider()
    st.info("Model: Pollinations AI FREE\nData: YouTube + Google Trends")

# ---------- INPUT ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("1. Enter Topic")
c1, c2 = st.columns(2)
with c1:
    topic = st.text_input("Topic / Drama Name", placeholder="Example: Tere Bin Season 2, Meem Se Mohabbat")
    category = st.selectbox("Category", ["Drama Review", "Drama Explain", "Entertainment News", "OST Review", "Celebrity"])
with c2:
    lang = st.selectbox("Title Language", ["Roman Urdu + English Mix", "Roman Urdu", "English"])
    target = st.selectbox("Target Audience", ["Pakistan", "India + Pakistan", "Worldwide"])
    st.session_state.target = target
if st.button("🔍 ANALYZE TOP 20 VIRAL VIDEOS"):
    if not topic: st.error("Please enter topic first!")
    else:
        with st.spinner("Analyzing Top 20 + Trends..."):
            videos, src = get_top_20(topic); st.session_state.data = videos; st.session_state.source = src; st.session_state.topic = topic
            trend_df, trend_src = get_trends(topic); st.session_state.trend_df = trend_df; st.session_state.trend_src = trend_src
            st.session_state.analysis = analyze_why_viral(pd.DataFrame(videos)); st.session_state.generated = False
            st.success(f"Done! {src} | {trend_src}"); time.sleep(0.3); st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ---------- ALWAYS SHOW - POSTING TIME + RPM GUIDE (Topic ke bagair bhi kaam karega) ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("⏰ Best Posting Time - Auto Calculator")
pt_target = st.selectbox("Apna Target Select Karo (Calculator)", ["Pakistan", "India + Pakistan", "Worldwide"], key="pt_calc")
pt = get_posting_time(pt_target)
pc1, pc2, pc3 = st.columns(3)
pc1.markdown(f"**🥇 Best Time 1**\n\n{pt['Best Time 1']}")
pc2.markdown(f"**🥈 Best Time 2**\n\n{pt['Best Time 2']}")
pc3.markdown(f"**🥉 Best Time 3**\n\n{pt['Best Time 3']}")
st.success(f"📅 Best Days: {pt['Best Day']} | 💡 {pt['Reason']}")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="money-card">', unsafe_allow_html=True)
st.subheader("💰 RPM Guide - Ye Title Hoga To RPM Ye Hoga")
st.write("Neeche wali table se samjho kaun sa title kitna paisa dega. **Full Episode Explained** sab se zyada RPM deta hai kyunki video lambi hoti hai aur 2-3 ads lagte hain.")
rpm_df = pd.DataFrame(get_rpm_data())
st.dataframe(rpm_df, use_container_width=True)
st.write("**🔥 RPM Barhane Ke 7 Golden Rules:**")
st.write("1. **Video 8+ Minute Ki Rakho** - 8 min se neeche video pe sirf 1 ad lagta hai, 8+ pe 2-3 mid-roll ads = RPM double")
st.write("2. **Worldwide Audience Target Karo** - Pakistan ka RPM $0.50 hai, USA ka $4-6 hai. English subtitles + English tags lagao")
st.write("3. **News / Explained Category** - In categories me advertisers zyada bid lagate hain")
st.write("4. **Watch Time Barhao** - Pehle 30 sec me hook do, end tak suspense rakho. Retention 50%+ ho to RPM auto barhega")
st.write("5. **Short Clips Se Bacho** - 1-2 min ke viral clips pe RPM sab se kam hota hai")
st.write("6. **High CPC Keywords** - Title/Description me 'Explained', 'Review', 'Analysis', 'News' words use karo")
st.write("7. **December + Ramadan Me RPM High** - Advertisers is season me zyada pay karte hain, zyada videos dalo")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("🌍 Worldwide High RPM Tags - Drama Se ALAG (Sirf RPM Ke Liye)")
st.write("Ye tags apne drama tags ke SATH lagao. Ye worldwide advertisers ko attract karte hain aur RPM $0.50 se $3-5 tak le jate hain.")
ww_df = get_worldwide_rpm_tags()
st.dataframe(ww_df, use_container_width=True)
ww_comma = ", ".join(ww_df["Worldwide High RPM Tag"].tolist())
st.markdown("**Copy All Worldwide RPM Tags:**")
st.text_area("Worldwide RPM Tags - Copy", value=ww_comma, height=80, key="ww_tags")
st.download_button("⬇️ Download Worldwide RPM Tags", data=ww_comma.encode(), file_name="worldwide_high_rpm_tags.txt")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- RESULTS ----------
if st.session_state.data:
    df = pd.DataFrame(st.session_state.data); analysis = st.session_state.analysis; topic = st.session_state.topic
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total Views Top 20", f"{analysis['total_views']:,}")
    m2.metric("Avg Views", f"{analysis['avg_views']:,}")
    m3.metric("Avg Title Length", f"{analysis['avg_len']} chars")
    m4.metric("Power Words Found", f"{len(analysis['power_words'])}")
    if st.session_state.trend_df is not None:
        st.subheader("📈 Google Trends - Last 7 Days")
        try: st.line_chart(st.session_state.trend_df.set_index("Date"))
        except: st.line_chart(st.session_state.trend_df)
    st.subheader(f"2. Top 20 Viral Videos - {topic}")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([1,3])
        with col1: st.image(row["Thumbnail"], use_container_width=True); st.markdown(f"[▶️ Watch]({row['URL']})")
        with col2:
            st.markdown(f"**{idx+1}. {row['Title']}**")
            st.markdown(f"<span class='small'>📺 {row['Channel']} | 📅 {row['Published']} | 👁️ {row['Views']:,} | 👍 {row['Likes']:,}</span>", unsafe_allow_html=True)
            st.code(row.get("Tags", f"{topic.lower()}, viral drama"), language="text")
        st.divider()
    st.markdown('<div class="viral-card">', unsafe_allow_html=True)
    st.subheader("3. 🧠 Why Viral?")
    st.write(f"**🏆 Most Viral:** {analysis['top_video']['Title']} - {analysis['top_video']['Views']:,} views")
    st.write(f"**🔑 Common Words:** {', '.join([w[0] for w in analysis['common_words']])}")
    st.write(f"**⚡ Power Words:** {', '.join(analysis['power_words'])}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4. Generate Titles + Tags + Thumbnail + RPM + Strategy")
    if st.button("✨ GENERATE FULL VIRAL PACK"):
        with st.spinner("Generating..."):
            prompt_titles = f"You are YouTube SEO expert. Topic: {topic}. Top viral: {', '.join(df['Title'].tolist()[:5])}. Generate 10 viral clickbait titles in Roman Urdu + English mix, 50-70 chars, power words. Numbered list."
            ai_titles, model = ai_generate(prompt_titles); st.session_state.ai_titles = ai_titles
            prompt_strategy = f"Create full viral strategy for {topic} in Roman Urdu + English mix. Include posting time, thumbnail, hook, retention, RPM tips."
            ai_strategy, _ = ai_generate(prompt_strategy); st.session_state.ai_strategy = ai_strategy
            base_tags = [(f"{topic.lower()} episode review","Very High","Very Low"),(f"{topic.lower()} full episode","Very High","Low"),(f"{topic.lower()} shocking twist","Very High","Very Low"),(f"{topic.lower()} ending revealed","High","Very Low"),(f"{topic.lower()} secret revealed","High","Low"),(f"{topic.lower()} explained in urdu","High","Very Low"),(f"{topic.lower()} next episode prediction","High","Low"),(f"{topic.lower()} viral scene","Very High","Low"),(f"{topic.lower()} emotional scene","High","Very Low"),(f"{topic.lower()} truth exposed","High","Very Low")]
            tags = [{"#": i+1, "Tag": t, "Search Volume": v, "Competition": c, "SEO Score": calc_tag_score(v,c)} for i,(t,v,c) in enumerate(base_tags)]
            st.session_state.tags_df = pd.DataFrame(tags).sort_values("SEO Score", ascending=False).reset_index(drop=True); st.session_state.tags_df["#"] = range(1,11)
            lines = [l.strip() for l in ai_titles.split("\n") if len(l.strip())>10]
            titles_data = []
            for i, line in enumerate(lines[:10]):
                ct = re.sub(r'^\d+[\.\)\-]\s*','',line).strip()
                rpm_text, rpm_score, rpm_tip = estimate_rpm_for_title(ct)
                titles_data.append({"#": i+1, "Title": ct, "Viral Score": calc_title_score(ct, analysis['power_words']), "RPM Estimate": rpm_text, "RPM Score": rpm_score, "Length": len(ct)})
            if len(titles_data)<5:
                fallbacks = [f"{topic} - SHOCKING Twist! Sab Kuch Badal Gaya?",f"{topic} Ending Revealed - Kya Hoga Agay?",f"{topic} Ka Secret Finally Exposed! Truth Samne Agaya",f"{topic} - Emotional Scene Ne Sab Ko Rula Diya",f"{topic} Full Episode Explained - Hidden Truth",f"{topic} - Death Twist! Koi Soch Bhi Nahi Sakta Tha",f"{topic} Next Episode Prediction - Bara Dhamaka",f"{topic} - Love Story Ka Sad Ending?",f"{topic} Revenge Plan Exposed - Ab Kya Hoga?",f"{topic} - Viral Scene! 5M Views Wala Moment"]
                titles_data = []
                for i,t in enumerate(fallbacks):
                    rpm_text, rpm_score, rpm_tip = estimate_rpm_for_title(t)
                    titles_data.append({"#": i+1, "Title": t, "Viral Score": calc_title_score(t, analysis['power_words']), "RPM Estimate": rpm_text, "RPM Score": rpm_score, "Length": len(t)})
                st.session_state.ai_titles = "\n".join([f"{d['#']}. {d['Title']}" for d in titles_data])
            st.session_state.titles_df = pd.DataFrame(titles_data).sort_values("Viral Score", ascending=False).reset_index(drop=True); st.session_state.titles_df["#"] = range(1,11)
            st.session_state.model_used = model; st.session_state.generated = True; st.success(f"Generated via {model}"); st.rerun()

    if st.session_state.generated:
        st.subheader("🏆 Top 10 Titles - With Viral Score + RPM Estimate")
        st.dataframe(st.session_state.titles_df, use_container_width=True)
        all_titles_text = "\n".join([f"{r['#']}. {r['Title']} [Viral: {r['Viral Score']}/100 | RPM: {r['RPM Estimate']} | RPM Score: {r['RPM Score']}]" for _,r in st.session_state.titles_df.iterrows()])
        st.text_area("Copy All Titles With Score + RPM", value=all_titles_text, height=220)
        st.download_button("⬇️ Download Titles", data=all_titles_text.encode(), file_name="viral_titles_rpm.txt")

        # THUMBNAIL GENERATOR - NEW
        st.subheader("🎨 Thumbnail Generator - Har Title Ke Liye Idea")
        st.write("Har title ke liye thumbnail ka text, face, color aur arrow ready hai. Isko Canva me bana lo.")
        for _, r in st.session_state.titles_df.iterrows():
            th = get_thumbnail_idea(r['Title'], topic)
            st.markdown(f'<div class="thumb-card"><b>📌 Title {r["#"]}: {r["Title"]}</b><br>🖼️ <b>Thumbnail Text:</b> {th["Text"]} | 😲 <b>Face:</b> {th["Face"]}<br>🎨 <b>Color:</b> {th["Color"]} | ➡️ <b>Arrow:</b> {th["Arrow"]} | 🖼️ <b>Background:</b> {th["BG"]}</div>', unsafe_allow_html=True)
        thumb_text = "\n\n".join([f"Title {r['#']}: {r['Title']}\nThumbnail Text: {get_thumbnail_idea(r['Title'], topic)['Text']} | Face: {get_thumbnail_idea(r['Title'], topic)['Face']} | Color: {get_thumbnail_idea(r['Title'], topic)['Color']} | Arrow: {get_thumbnail_idea(r['Title'], topic)['Arrow']}" for _,r in st.session_state.titles_df.iterrows()])
        st.text_area("Copy All Thumbnail Ideas", value=thumb_text, height=200)
        st.download_button("⬇️ Download Thumbnail Ideas", data=thumb_text.encode(), file_name="thumbnail_ideas.txt")

        # RPM CALCULATOR - NEW INTERACTIVE
        st.markdown('<div class="money-card">', unsafe_allow_html=True)
        st.subheader("💰 RPM Calculator - Apna Title Check Karo")
        selected_title = st.selectbox("Koi Title Select Karo - RPM Dekho", st.session_state.titles_df["Title"].tolist())
        if selected_title:
            rpm_text, rpm_score, rpm_tip = estimate_rpm_for_title(selected_title)
            st.metric("Is Title Ka RPM Estimate", rpm_text)
            st.metric("RPM Score", f"{rpm_score}/100")
            st.success(f"💡 RPM Barhane Ka Tip: {rpm_tip}")
            # Earning Estimate
            views_input = st.number_input("Agar Views Aayen (Example: 100000)", min_value=1000, value=100000, step=10000)
            # Pakistan RPM avg 0.6, Worldwide avg 3.5 - show both
            st.write(f"**Agar {views_input:,} views aayen to:**")
            st.write(f"🇵🇰 Pakistan Audience Se Earning: **${views_input/1000*0.6:.2f}** (RPM $0.60)")
            st.write(f"🌍 Worldwide Audience Se Earning: **${views_input/1000*3.5:.2f}** (RPM $3.50)")
            st.write(f"🔥 **Farq Dekho: Worldwide se {3.5/0.6:.1f}x zyada earning!** Isi liye English subtitles + Worldwide tags lagao.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("📝 SEO Description")
        desc = f"""{topic} ka sab se bara twist samne agaya! Top 20 viral videos analyze karke full review laya hoon.

00:00 - Shocking Hook
01:30 - Recap
04:00 - Twist Explained
07:00 - Analysis
09:00 - Next Prediction

LIKE + SUBSCRIBE zaroor karein!
#{topic.replace(' ','')} #DramaReview #PakistaniDrama"""
        st.text_area("Description", value=desc, height=180)
        st.subheader("🏷️ Top 10 Tags - Low Competition + High Search")
        st.dataframe(st.session_state.tags_df, use_container_width=True)
        all_tags_comma = ", ".join(st.session_state.tags_df["Tag"].tolist())
        st.text_area("All Drama Tags (Comma)", value=all_tags_comma, height=80)
        st.download_button("⬇️ Download Drama Tags", data=all_tags_comma.encode(), file_name="top10_tags.txt")
        st.subheader("🚀 Full Viral Strategy")
        st.text_area("Strategy", value=st.session_state.ai_strategy, height=350)
        # COMBINED PACK
        everything = f"TOP 10 TITLES + RPM:\n{all_titles_text}\n\nDRAMA TAGS:\n{all_tags_comma}\n\nWORLDWIDE RPM TAGS:\n{ww_comma}\n\nTHUMBNAILS:\n{thumb_text}\n\nDESCRIPTION:\n{desc}\n\nSTRATEGY:\n{st.session_state.ai_strategy}"
        st.subheader("📦 Copy EVERYTHING In One Click")
        st.text_area("Full Pack", value=everything, height=300)
        st.download_button("⬇️ DOWNLOAD FULL SEO + RPM PACK", data=everything.encode(), file_name="full_seo_rpm_pack.txt")
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("SEO Viral Engine Pro v3.0 | YouTube + PyTrends + RPM Booster + Thumbnail Generator")
