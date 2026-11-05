import streamlit as st
import re
import time
from datetime import datetime, date
import pandas as pd
from apify_client import ApifyClient

# Page Configuration
st.set_page_config(page_title="Instagram Influencer Keyword Scanner", page_icon="🔍", layout="wide")

st.title("🔍 Instagram Influencer Keyword Scanner")
st.markdown("Enter influencer profile links & keywords. Matching posts will be extracted automatically.")

# --- CHECK FOR SECRET TOKEN ---
secret_token = st.secrets.get("APIFY_API_TOKEN", "")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Search Filters")

# Agar Secret me token na mile to hi sidebar me box dikhaye
if not secret_token:
    api_token = st.sidebar.text_input(
        "🔑 Apify API Token:", 
        type="password",
        placeholder="apify_api_xxxxxxxxx"
    )
else:
    api_token = secret_token
    st.sidebar.success("🔒 System API Connected")

# Date Range Selection
st.sidebar.subheader("📅 Time Period")
start_date = st.sidebar.date_input("Start Date", value=date(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", value=date(2026, 10, 31))

# Keywords Input
st.sidebar.subheader("🔑 Keywords")
keywords_input = st.sidebar.text_area(
    "Keywords (comma ya new line se daalein):", 
    placeholder="Master Changan, car, byd"
)

# --- MAIN AREA: PROFILE LINKS ---
st.subheader("📋 Influencer Profile Links")
links_input = st.text_area(
    "Instagram profile links paste karein (Har link ek nayi line me ya comma se alag karein):",
    height=150,
    placeholder="https://www.instagram.com/irfanjunejo/\nhttps://www.instagram.com/minoqtopus/"
)

def extract_username(profile_link):
    profile_link = profile_link.strip().rstrip('/')
    match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]+)", profile_link)
    if match:
        return match.group(1)
    return profile_link.replace("@", "")

# --- ACTION BUTTON ---
if st.button("🚀 Start Scanning", type="primary"):
    raw_links = [l.strip() for l in re.split(r'[\n,]+', links_input) if l.strip()]
    raw_keywords = [k.strip().lower() for k in re.split(r'[\n,]+', keywords_input) if k.strip()]
    
    if not api_token.strip():
        st.error("⚠️ API Token configure nahi hai!")
    elif not raw_links:
        st.error("⚠️ Kam az kam ek Instagram profile link zaroor enter karein!")
    elif not raw_keywords:
        st.error("⚠️ Kam az kam ek keyword zaroor enter karein!")
    elif start_date > end_date:
        st.error("⚠️ Start Date, End Date se baad ki nahi ho sakti!")
    else:
        usernames = [extract_username(link) for link in raw_links]
        
        st.info(f"🚀 Scanning initiated for: {', '.join(['@'+u for u in usernames])}")
        
        s_dt = datetime.combine(start_date, datetime.min.time())
        e_dt = datetime.combine(end_date, datetime.max.time())
        
        results = []
        
        with st.spinner("⏳ Instagram posts fetch ho rahi hain... Please wait..."):
            try:
                client = ApifyClient(api_token.strip())
                
                run_input = {
                    "username": usernames,
                    "resultsLimit": 30
                }
                
                run = client.actor("apify/instagram-post-scraper").call(run_input=run_input)
                dataset_id = getattr(run, "default_dataset_id", None) or (run.get("defaultDatasetId") if isinstance(run, dict) else None)
                
                dataset_items = list(client.dataset(dataset_id).iterate_items())
                
                for item in dataset_items:
                    post_timestamp = item.get("timestamp")
                    if not post_timestamp:
                        continue
                        
                    if isinstance(post_timestamp, str):
                        post_date = datetime.fromisoformat(post_timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                    else:
                        post_date = datetime.utcfromtimestamp(post_timestamp)
                        
                    if post_date > e_dt or post_date < s_dt:
                        continue
                        
                    caption = (item.get("caption") or "").lower()
                    post_url = item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/"
                    owner = item.get("ownerUsername") or "Unknown"
                    
                    for kw in raw_keywords:
                        if kw in caption:
                            results.append({
                                "Influencer": f"@{owner}",
                                "Date": post_date.strftime("%Y-%m-%d"),
                                "Matched Keyword": kw,
                                "Post Link": post_url,
                                "Caption Preview": (item.get("caption")[:120] + "...") if item.get("caption") and len(item.get("caption")) > 120 else (item.get("caption") or "No Caption")
                            })
                            break
                            
            except Exception as e:
                st.error(f"❌ Error during scanning: {e}")

        # --- DISPLAY RESULTS ---
        if results:
            df = pd.DataFrame(results)
            st.success(f"🎉 Total **{len(results)}** matching posts mili hain!")
            
            st.dataframe(
                df,
                column_config={
                    "Post Link": st.column_config.LinkColumn("Post Link")
                },
                use_container_width=True
            )
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Results as CSV (Excel)",
                data=csv,
                file_name=f"instagram_results_{date.today()}.csv",
                mime="text/csv"
            )
        else:
            st.warning("❌ Diye gaye time period aur keywords ke mutabiq koi post nahi mili.")