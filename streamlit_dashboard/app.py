import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# Page Config
st.set_page_config(
    page_title="Sentiment Tracker | AC Shadows",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .kpi-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 14px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        color: #f8fafc;
        font-size: 32px;
        font-weight: bold;
    }
    .success { color: #4ade80; }
    .danger { color: #f87171; }
</style>
""", unsafe_allow_html=True)

# Data Loading
@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = {
        'YouTube': os.path.join(base_dir, 'output', '_yt_sentiment_tmp', 'yt_sentiment.csv'),
        'Steam': os.path.join(base_dir, 'output', '_steam_sentiment_tmp', 'steam_sentiment.csv'),
        'Reddit': os.path.join(base_dir, 'output', '_reddit_sentiment_tmp', 'reddit_sentiment.csv')
    }
    
    data = {}
    for name, path in files.items():
        if os.path.exists(path):
            try:
                # Assuming CSV structure needs to be robust to string numbers
                df = pd.read_csv(path)
                # Clean numeric columns
                for col in ['pos_count', 'neg_count', 'context_count']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        
                data[name] = df
            except Exception as e:
                st.error(f"Error loading {name}: {e}")
    return data

data_sources = load_data()

# Navigation
st.sidebar.title("AC Shadows")
st.sidebar.header("Platform")

if not data_sources:
    st.error("No data found. Please ensure the CSV files are in the 'output' directory.")
    st.stop()

# Add 'Overall' option
options = ['Overall'] + list(data_sources.keys())
selected_platform = st.sidebar.radio("Select View", options)

# Aggregate Data for Overall
if selected_platform == 'Overall':
    # Combine all dataframes
    all_dfs = []
    for df in data_sources.values():
        all_dfs.append(df)
    
    if all_dfs:
        # For word cloud and top lists, we just concat
        # Note: Words might duplicate across platforms, aggregation would be ideal but concat is fast
        df = pd.concat(all_dfs, ignore_index=True)
    else:
        df = pd.DataFrame()
else:
    df = data_sources[selected_platform]

# KPI Calculations
total_pos = int(df['pos_count'].sum())
total_neg = int(df['neg_count'].sum())
total_mentions = total_pos + total_neg
sentiment_ratio = round((total_pos / total_mentions * 100), 1) if total_mentions > 0 else 0

# Dashboard Layout
st.title(f"Sentiment Analysis: {selected_platform}")

# KPI Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Total Mentions</div><div class="kpi-value">{total_mentions:,}</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Positive</div><div class="kpi-value success">{total_pos:,}</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Negative</div><div class="kpi-value danger">{total_neg:,}</div></div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Positive Ratio</div><div class="kpi-value">{sentiment_ratio}%</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# Charts
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Trending Keywords")
    if not df.empty:
        # Word Cloud
        # Safety check for empty dataframe or missing columns
        if 'word' in df.columns and 'context_count' in df.columns:
            # Positive/General Word Cloud
            word_dict = dict(zip(df['word'].astype(str), df['context_count']))
            word_dict = {k: v for k, v in word_dict.items() if v > 0}
            
            # Negative Word Cloud
            neg_word_dict = {}
            if 'neg_count' in df.columns:
                 neg_word_dict = dict(zip(df['word'].astype(str), df['neg_count']))
                 # Filter words that are visibly positive but appear in negative context (e.g. "not fun")
                 # User specifically requested removing "fun". Adding others for cleaner visualization.
                 exclusions = ['fun', 'good', 'great', 'love', 'best', 'better', 'awesome', 'amazing', 'nice']
                 neg_word_dict = {k: v for k, v in neg_word_dict.items() if v > 0 and k.lower() not in exclusions}

            # Layout for Word Clouds
            tab1, tab2 = st.tabs(["Overall/Positive", "Negative Focus"])
            
            with tab1:
                if word_dict:
                    wc = WordCloud(width=800, height=400, background_color=None, mode="RGBA").generate_from_frequencies(word_dict)
                    plt.figure(figsize=(10, 5))
                    plt.imshow(wc, interpolation='bilinear')
                    plt.axis('off')
                    st.pyplot(plt)
                    plt.clf()
                else:
                    st.info("Not enough data for Word Cloud.")
            
            with tab2:
                if neg_word_dict:
                    wc_neg = WordCloud(width=800, height=400, background_color=None, mode="RGBA", colormap="Reds").generate_from_frequencies(neg_word_dict)
                    plt.figure(figsize=(10, 5))
                    plt.imshow(wc_neg, interpolation='bilinear')
                    plt.axis('off')
                    st.pyplot(plt)
                    plt.clf()
                else:
                    st.info("Not enough negative data for Word Cloud.")

        else:
            st.warning("Data format incorrect for Word Cloud.")

with col_right:
    st.subheader("Sentiment Distribution")
    dist_data = pd.DataFrame({
        'Sentiment': ['Positive', 'Negative'],
        'Count': [total_pos, total_neg]
    })
    import altair as alt
    
    # Create the base chart
    base = alt.Chart(dist_data).encode(
        theta=alt.Theta("Count", stack=True)
    )
    
    # The donut chart
    pie = base.mark_arc(innerRadius=60).encode(
        color=alt.Color("Sentiment", scale=alt.Scale(domain=['Positive', 'Negative'], range=['#4ade80', '#f87171'])),
        order=alt.Order("Count", sort="descending"),
        tooltip=["Sentiment", "Count"]
    )
    
    # Text labels (Percentages)
    text = base.mark_text(radius=100).encode(
        text=alt.Text("Count", format=","),
        order=alt.Order("Count", sort="descending"), 
        color=alt.value("white")
    )
    
    st.altair_chart(pie + text, use_container_width=True)

# Top Lists
st.markdown("---")
col_pos, col_neg = st.columns(2)

limit = 10

with col_pos:
    st.subheader(f"Top {limit} Positive Topics")
    if 'pos_count' in df.columns:
        top_pos_df = df.nlargest(limit, 'pos_count')[['word', 'pos_count']].set_index('word')
        st.bar_chart(top_pos_df, color="#38bdf8")

with col_neg:
    st.subheader(f"Top {limit} Negative Topics")
    if 'neg_count' in df.columns:
        top_neg_df = df.nlargest(limit, 'neg_count')[['word', 'neg_count']].set_index('word')
        st.bar_chart(top_neg_df, color="#f87171")

# Recommendations & Verdict
# st.markdown("---")
# col_verdict, col_rec = st.columns([1, 2])

# with col_verdict:
#     st.subheader("🤖 AI Verdict")
    
#     verdict_color = ""
#     verdict_emoji = ""
#     verdict_text = ""
    
#     if sentiment_ratio >= 70:
#         verdict_color = "#4ade80" # Green
#         verdict_emoji = "🤩"
#         verdict_text = "OVERWHELMINGLY POSITIVE"
#         if selected_platform == 'Overall': 
#             st.balloons() # GIMMICK: Balloons for high score
#     elif sentiment_ratio >= 50:
#         verdict_color = "#fbbf24" # Yellow
#         verdict_emoji = "🤔"
#         verdict_text = "MIXED / AVERAGE"
#     else:
#         verdict_color = "#f87171" # Red
#         verdict_emoji = "🤬"
#         verdict_text = "NEGATIVE / CRITICAL"
#         if selected_platform == 'Overall':
#             st.snow() # GIMMICK: Snow for cold reception

#     st.markdown(f"""
#     <div style="background-color: {verdict_color}20; border: 2px solid {verdict_color}; border-radius: 10px; padding: 20px; text-align: center;">
#         <div style="font-size: 60px;">{verdict_emoji}</div>
#         <div style="color: {verdict_color}; font-size: 24px; font-weight: bold; margin-top: 10px;">{verdict_text}</div>
#         <div style="color: #94a3b8; font-size: 14px; margin-top: 5px;">Based on {total_mentions:,} data points</div>
#     </div>
#     """, unsafe_allow_html=True)

# with col_rec:
#     st.subheader("🔎 Strategic Recommendations")
    
#     rec_text = ""
#     if sentiment_ratio > 70:
#         rec_text = f"""
#         <div style="padding: 15px; border-left: 4px solid #4ade80; background: #4ade8010;">
#             <strong style="color: #4ade80">✅ Maintain Momentum:</strong><br>
#             The sentiment on {selected_platform} is excellent. Engage with the community to amplify this trust.
#             Consider hosting community events or "Dev Talks" to celebrate this success.
#         </div>
#         """
#     elif sentiment_ratio > 50:
#         rec_text = f"""
#         <div style="padding: 15px; border-left: 4px solid #fbbf24; background: #fbbf2410;">
#             <strong style="color: #fbbf24">⚠️ Mixed Signals:</strong><br>
#             Sentiment is balanced. While many enjoy the game, a significant portion has reservations.
#             Investigate the "Negative Focus" word cloud to identify specific pain points (e.g., optimization, bugs).
#         </div>
#         """
#     else:
#         rec_text = f"""
#         <div style="padding: 15px; border-left: 4px solid #f87171; background: #f8717110;">
#             <strong style="color: #f87171">🚨 Critical Action Needed:</strong><br>
#             Negative sentiment is prevailing. Review the top complaints immediately.
#             A transparent roadmap or bug-fix update is highly recommended to restore faith.
#         </div>
#         """
#     st.markdown(rec_text, unsafe_allow_html=True)

#     if 'neg_count' in df.columns and not df.empty:
#         top_negs = df.nlargest(3, 'neg_count')['word'].tolist()
#         st.markdown(f"**🔥 Hot Topics (Negative):** {', '.join([f'`{w}`' for w in top_negs])}")

# Interactive Word Search
st.markdown("---")
with st.expander("🕵️‍♀️ Word Detective (Cari kata spesifik)"):
    search_term = st.text_input("Ketik kata yang ingin dicek (misal: 'combat', 'story'):").lower().strip()
    if search_term and not df.empty:
        # Check if word exists
        found = df[df['word'] == search_term]
        if not found.empty:
            row = found.iloc[0]
            s_pos = int(row.get('pos_count', 0))
            s_neg = int(row.get('neg_count', 0))
            s_total = int(row.get('context_count', 0))
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Mentions", f"{s_total}")
            c2.metric("Positive Use", f"{s_pos}", delta=f"{round(s_pos/s_total*100)}%")
            c3.metric("Negative Use", f"{s_neg}", delta=f"-{round(s_neg/s_total*100)}%", delta_color="inverse")
            
            # Context bar
            chart_data = pd.DataFrame({'Type': ['Positive', 'Negative'], 'Count': [s_pos, s_neg]})
            st.altair_chart(alt.Chart(chart_data).mark_bar().encode(
                x='Count',
                y='Type',
                color=alt.Color('Type', scale=alt.Scale(domain=['Positive', 'Negative'], range=['#4ade80', '#f87171']))
            ), use_container_width=True)
        else:
            st.warning(f"Kata '{search_term}' tidak ditemukan dalam data {selected_platform}.")
