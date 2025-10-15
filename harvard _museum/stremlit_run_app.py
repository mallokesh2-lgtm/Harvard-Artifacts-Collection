import streamlit as st
import requests
import pandas as pd
import sqlite3

# ------------------------
# CONFIGURATION
# ------------------------
API_KEY = "3f0e515b-0f14-4ce3-a153-8cc06d99e948"
OBJECT_URL = "https://api.harvardartmuseums.org/object"

st.set_page_config(page_title="Harvard Artifacts Dashboard", layout="wide")

# ------------------------
# SESSION STORAGE
# ------------------------
if "meta_df" not in st.session_state:
    st.session_state.meta_df = pd.DataFrame()
    st.session_state.media_df = pd.DataFrame()
    st.session_state.color_df = pd.DataFrame()

# ------------------------
# CLASSIFICATION BAR
# ------------------------
classifications = ["Coins", "Paintings", "Drawings", "Jewelry", "Sculpture"]

st.title("🏛 Harvard Artifacts Collection")
st.subheader("Select Classification to fetch data")
selected_classification = st.selectbox("Pick one classification:", options=classifications)

collect_btn = st.button("🟠 Collect Data")

# ------------------------
# FETCH DATA FUNCTION
# ------------------------
def fetch_artifacts(classification, limit=2500):
    records = []
    page = 1
    page_size = 25
    max_pages = (limit + page_size - 1) // page_size

    progress_text = st.empty()
    progress_bar = st.progress(0)

    while len(records) < limit:
        params = {"apikey": API_KEY, "classification": classification, "size": page_size, "page": page}
        r = requests.get(OBJECT_URL, params=params)
        if r.status_code != 200:
            break
        data = r.json().get("records", [])
        if not data:
            break
        records.extend(data)
        page += 1

        progress_bar.progress(min(len(records) / limit, 1.0))
        progress_text.text(f"Fetching '{classification}': {len(records)} / {limit} records")

        if page > max_pages:
            break

    progress_text.text(f"✅ Completed fetching '{classification}' ({len(records)} records)")
    return records[:limit]

# ------------------------
# COLLECT DATA FUNCTIONALITY
# ------------------------
if collect_btn:
    meta, media, colors = [], [], []

    data = fetch_artifacts(selected_classification, limit=2500)
    for obj in data:
        oid = obj.get("objectid")
        meta.append({
            "objectid": oid,
            "title": obj.get("title"),
            "culture": obj.get("culture"),
            "period": obj.get("period"),
            "technique": obj.get("technique"),
            "dated": obj.get("dated"),
            "department": obj.get("department"),
            "accessionyear": obj.get("accessionyear"),
            "rank": obj.get("rank"),
            "colorcount": obj.get("colorcount"),
            "mediacount": obj.get("mediacount"),
            "classification": selected_classification
        })

        if obj.get("images"):
            for i in obj["images"]:
                media.append({
                    "objectid": oid,
                    "imageurl": i.get("baseimageurl"),
                    "rank": i.get("rank")
                })

        for c in obj.get("colors", []):
            colors.append({
                "objectid": oid,
                "color": c.get("color"),
                "hue": c.get("hue"),
                "percent": c.get("percent")
            })

    st.session_state.meta_df = pd.DataFrame(meta)
    st.session_state.media_df = pd.DataFrame(media)
    st.session_state.color_df = pd.DataFrame(colors)

    st.success(f"✅ {selected_classification} data collected successfully! Total records: {len(meta)}")

# ------------------------
# PAGE LAYOUT
# ------------------------
col1, col2, col3 = st.columns([2, 2, 2])

# ------------------------
# COLUMN 1 — SELECT YOUR DATA
# ------------------------
with col1:
    st.subheader("🟢 Select Your Data")
    with st.expander("View Metadata, Media, and Color tables"):
        inner_col1, inner_col2, inner_col3 = st.columns(3)
        with inner_col1:
            st.info("**Metadata**")
            if not st.session_state.meta_df.empty:
                st.dataframe(st.session_state.meta_df.head(10), height=300)
            else:
                st.info("No metadata loaded yet.")
        with inner_col2:
            st.info("**Media**")
            if not st.session_state.media_df.empty:
                st.dataframe(st.session_state.media_df.head(10), height=300)
            else:
                st.info("No media data loaded yet.")
        with inner_col3:
            st.info("**Colors**")
            if not st.session_state.color_df.empty:
                st.dataframe(st.session_state.color_df.head(10), height=300)
            else:
                st.info("No color data loaded yet.")

# ------------------------
# COLUMN 2 — MIGRATE TO SQL
# ------------------------
with col2:
    st.subheader("🔵 Migrate to SQL")
    migrate_btn = st.button("💾 Insert to SQL")

    if migrate_btn:
        if st.session_state.meta_df.empty:
            st.warning("⚠️ Please collect data first!")
        else:
            conn = sqlite3.connect("harvard_artifacts.db")
            st.session_state.meta_df.to_sql("artifact_metadata", conn, if_exists="replace", index=False)
            st.session_state.media_df.to_sql("artifact_media", conn, if_exists="replace", index=False)
            st.session_state.color_df.to_sql("artifact_colors", conn, if_exists="replace", index=False)
            conn.close()
            st.success("✅ Data inserted to SQLite successfully!")
            st.dataframe(st.session_state.meta_df.head(50), height=300)

# ------------------------
# COLUMN 3 — SQL QUERIES
# ------------------------
with col3:
    st.subheader("🟣 SQL Queries")
    queries = {
        "List all artifacts from the 11th century belonging to Byzantine culture.": 
            "SELECT * FROM artifact_metadata WHERE culture='Byzantine' AND dated LIKE '%11th%';",
        "What are the unique cultures represented in the artifacts?": 
            "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",
        "List all artifacts from the Archaic Period.": 
            "SELECT * FROM artifact_metadata WHERE period LIKE '%Archaic%';",
        "List artifact titles ordered by accession year in descending order.": 
            "SELECT title, accessionyear FROM artifact_metadata ORDER BY accessionyear DESC;",
        "How many artifacts are there per department?": 
            "SELECT department, COUNT(*) AS total FROM artifact_metadata GROUP BY department;",
        "Which artifacts have more than 1 image?": 
            "SELECT objectid, COUNT(*) AS image_count FROM artifact_media GROUP BY objectid HAVING image_count > 1;",
        "What is the average rank of all artifacts?": 
            "SELECT AVG(rank) AS avg_rank FROM artifact_metadata;",
        "Which artifacts have a higher colorcount than mediacount?": 
            "SELECT objectid, title, colorcount, mediacount FROM artifact_metadata WHERE colorcount > mediacount;",
        "List all artifacts created between 1500 and 1600.": 
            "SELECT * FROM artifact_metadata WHERE dated LIKE '%15%' OR dated LIKE '%16%';",
        "How many artifacts have no media files?": 
            "SELECT * FROM artifact_metadata WHERE mediacount = 0 OR mediacount IS NULL;",
        "What are all the distinct hues used in the dataset?": 
            "SELECT DISTINCT hue FROM artifact_colors WHERE hue IS NOT NULL;",
        "What are the top 5 most used colors by frequency?": 
            "SELECT color, COUNT(*) AS freq FROM artifact_colors GROUP BY color ORDER BY freq DESC LIMIT 5;",
        "What is the average coverage percentage for each hue?": 
            "SELECT hue, AVG(percent) AS avg_percent FROM artifact_colors GROUP BY hue;",
        "List all colors used for a given artifact ID.": 
            "SELECT * FROM artifact_colors WHERE objectid = (SELECT objectid FROM artifact_metadata LIMIT 1);",
        "What is the total number of color entries in the dataset?": 
            "SELECT COUNT(*) AS total_colors FROM artifact_colors;",
        "List artifact titles and hues for all artifacts belonging to the Byzantine culture.": 
            "SELECT m.title, c.hue FROM artifact_metadata m JOIN artifact_colors c ON m.objectid = c.objectid WHERE m.culture='Byzantine';",
        "List each artifact title with its associated hues.": 
            "SELECT m.title, c.hue FROM artifact_metadata m LEFT JOIN artifact_colors c ON m.objectid=c.objectid;",
        "Get artifact titles, cultures, and media ranks where the period is not null.": 
            "SELECT m.title, m.culture, me.rank FROM artifact_metadata m JOIN artifact_media me ON m.objectid=me.objectid WHERE m.period IS NOT NULL;",
        "Find artifact titles ranked in the top 10 that include the color hue 'Grey'.": 
            "SELECT m.title, c.hue, m.rank FROM artifact_metadata m JOIN artifact_colors c ON m.objectid=me.objectid WHERE c.hue='Grey' ORDER BY m.rank DESC LIMIT 10;",
        "How many artifacts exist per classification, and what is the average media count for each?": 
            "SELECT classification, COUNT(*) AS total, AVG(mediacount) AS avg_media FROM artifact_metadata GROUP BY classification;"
    }

    selected_query = st.selectbox("Select a Query:", list(queries.keys()))
    sql_code = queries[selected_query]
    st.code(sql_code, language="sql")

    if st.button("▶ Run Query"):
        try:
            conn = sqlite3.connect("harvard_artifacts.db")
            df = pd.read_sql_query(sql_code, conn)
            conn.close()
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ SQL Error: {e}")
