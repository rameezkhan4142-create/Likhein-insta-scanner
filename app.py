import streamlit as st
import re
import time
from datetime import datetime, date
import pandas as pd
from apify_client import ApifyClient

# Page Configuration
st.set_page_config(page_title="Instagram Influencer & Brand Campaign Tracker", page_icon="📊", layout="wide")

st.title("📊 Instagram Influencer & Brand Campaign Tracker")
st.markdown("Track brand campaigns, identify influencer rosters, and filter **commercial partnerships**.")

# --- CHECK FOR SECRET TOKEN SAFELY ---
secret_token = ""
try:
    if "APIFY_API_TOKEN" in st.secrets:
        secret_token = st.secrets["APIFY_API_TOKEN"]
except Exception:
    secret_token = ""

# --- SIDEBAR: SETTINGS & FILTERS ---
st.sidebar.header("⚙️ Settings & Filters")

# Token Handling
if not secret_token:
    api_token = st.sidebar.text_input(
        "🔑 Apify API Token:", 
        type="password",
        placeholder="apify_api_xxxxxxxxx"
    )
    st.sidebar.caption("👉 Get your API token: [apify.com](https://console.apify.com/account#/integrations)")
else:
    api_token = secret_token
    st.sidebar.success("🔒 System API Connected")

# Time Period
st.sidebar.subheader("📅 Time Period")
start_date = st.sidebar.date_input("Start Date", value=date(2026, 1, 1))
end_date = st.sidebar.date_input("End Date", value=date(2026, 10, 31))

# Paid Filter Toggle (Pakistani Market Optimized)
st.sidebar.subheader("🎯 Campaign Type")
only_paid = st.sidebar.checkbox("Strictly Commercial / Sponsored Campaigns Only", value=True)
st.sidebar.caption("Detects @mentions, campaign hashtags (#brand), PR tags, and official disclosures.")

# Helper Functions
def extract_username(profile_link):
    profile_link = profile_link.strip().rstrip('/')
    match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]+)", profile_link)
    if match:
        return match.group(1)
    return profile_link.replace("@", "").replace(" ", "")

def is_commercial_campaign(caption, target_brand, item):
    """
    Pakistani Market Optimized Commercial Detection:
    Checks for official disclosures, brand @mentions, #brand hashtags, and PR/Collab keywords.
    """
    caption_lower = (caption or "").lower()
    brand_clean = target_brand.lower().replace("@", "").replace(" ", "")
    
    # 1. Standard Disclosures
    standard_tags = ["#ad", "#sponsored", "#collab", "#paidpartnership", "#incollaborationwith", "#brandpartner", "paid partnership"]
    for tag in standard_tags:
        if tag in caption_lower:
            return True, f"Official Tag: '{tag}'"
            
    # 2. Instagram Built-in Paid Tag
    if item.get("isSponsored") or item.get("isPaidPartnership") or item.get("commercialityStatus") == "commercial":
        return True, "Instagram Official Paid Tag"
        
    # 3. Brand Handle Mention (e.g., @lorealpakistan, @bydpakistan)
    if f"@{brand_clean}" in caption_lower or (brand_clean in caption_lower and "@" in caption_lower):
        return True, f"Brand Handle Tagged: '@{brand_clean}'"
        
    # 4. Brand Campaign Hashtag (e.g., #lorealparis, #bydpakistan, #drivewithbyd)
    if f"#{brand_clean}" in caption_lower:
        return True, f"Campaign Hashtag: '#{brand_clean}'"
        
    # 5. Local PR / Gifting / Campaign keywords
    local_pr_keywords = ["thank you @", "thanks to @", "pr package", "gifted", "courtesy of @", "code:", "discount code", "link in bio to shop"]
    for kw in local_pr_keywords:
        if kw in caption_lower:
            return True, f"Commercial Indicator: '{kw}'"
            
    return False, "Organic / Personal Mention"

# --- MAIN INTERFACE: TABS ---
tab1, tab2 = st.tabs(["🏢 Track by Brand Name", "👤 Scan Specific Influencer Profiles"])

# ==========================================
# TAB 1: TRACK BY BRAND (REVERSE SEARCH)
# ==========================================
with tab1:
    st.subheader("Discover All Influencers Who Ran Campaigns for a Brand")
    brand_input = st.text_input(
        "Enter Brand Name or Instagram Handle:", 
        placeholder="e.g., Loreal, lorealpakistan, BYD, Master Changan, Khaadi"
    )
    max_posts = st.slider("Number of recent brand posts/mentions to scan:", min_value=20, max_value=150, value=50, step=10)
    run_brand_search = st.button("🚀 Track Brand Campaigns", type="primary")

# ==========================================
# TAB 2: SPECIFIC PROFILES SCANNER
# ==========================================
with tab2:
    st.subheader("Check Specific Influencer Profiles for Keywords")
    links_input = st.text_area(
        "Paste Influencer Profile Links (One per line or comma-separated):",
        height=120,
        placeholder="https://www.instagram.com/irfanjunejo/\nhttps://www.instagram.com/minoqtopus/"
    )
    keywords_input = st.text_area(
        "Keywords / Brand to search in captions (comma-separated):", 
        placeholder="byd, changan, loreal, car, ev"
    )
    run_profile_search = st.button("🔍 Scan Influencer Profiles", type="primary")

# ==========================================
# EXECUTION LOGIC
# ==========================================
s_dt = datetime.combine(start_date, datetime.min.time())
e_dt = datetime.combine(end_date, datetime.max.time())

# --- RUN TAB 1 ---
if run_brand_search:
    if not api_token.strip():
        st.error("⚠️ API Token is not configured. Please enter it in the sidebar.")
    elif not brand_input.strip():
        st.error("⚠️ Please enter a brand name or handle.")
    elif start_date > end_date:
        st.error("⚠️ Start Date cannot be later than End Date.")
    else:
        brand_handle = extract_username(brand_input)
        st.info(f"🚀 Scanning campaign footprint for brand: **@{brand_handle}**...")
        
        results = []
        with st.spinner("⏳ Fetching brand mentions & posts via Apify Cloud... Please wait..."):
            try:
                client = ApifyClient(api_token.strip())
                run_input = {"username": [brand_handle], "resultsLimit": max_posts}
                
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
                        
                    caption = item.get("caption") or ""
                    owner = item.get("ownerUsername") or "Unknown"
                    post_url = item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/"
                    
                    is_commercial, evidence = is_commercial_campaign(caption, brand_handle, item)
                    
                    if only_paid and not is_commercial:
                        continue
                        
                    results.append({
                        "Influencer / Creator": f"@{owner}",
                        "Date": post_date.strftime("%Y-%m-%d"),
                        "Campaign Status": "Commercial / Sponsored" if is_commercial else "Organic Mention",
                        "Evidence": evidence,
                        "Post Link": post_url,
                        "Caption Preview": (caption[:120] + "...") if len(caption) > 120 else caption
                    })
                    
            except Exception as e:
                st.error(f"❌ Error during search: {e}")

        if results:
            df = pd.DataFrame(results)
            st.success(f"🎉 Found **{len(results)}** campaign posts for **@{brand_handle}**!")
            st.dataframe(df, column_config={"Post Link": st.column_config.LinkColumn("Post Link")}, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Campaign Report as CSV", csv, f"{brand_handle}_report.csv", "text/csv")
        else:
            st.warning(f"❌ No matching campaign posts found for @{brand_handle} within the selected dates.")

# --- RUN TAB 2 ---
if run_profile_search:
    raw_links = [l.strip() for l in re.split(r'[\n,]+', links_input) if l.strip()]
    raw_keywords = [k.strip().lower() for k in re.split(r'[\n,]+', keywords_input) if k.strip()]
    
    if not api_token.strip():
        st.error("⚠️ API Token is not configured. Please enter it in the sidebar.")
    elif not raw_links:
        st.error("⚠️ Please enter at least one influencer profile link.")
    elif not raw_keywords:
        st.error("⚠️ Please enter at least one keyword.")
    elif start_date > end_date:
        st.error("⚠️ Start Date cannot be later than End Date.")
    else:
        usernames = [extract_username(link) for link in raw_links]
        st.info(f"🚀 Scanning {len(usernames)} profiles for keywords...")
        
        results = []
        with st.spinner("⏳ Scanning profiles via Apify Cloud... Please wait..."):
            try:
                client = ApifyClient(api_token.strip())
                run_input = {"username": usernames, "resultsLimit": 30}
                
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
                        
                    caption = item.get("caption") or ""
                    caption_lower = caption.lower()
                    owner = item.get("ownerUsername") or "Unknown"
                    post_url = item.get("url") or f"https://www.instagram.com/p/{item.get('shortCode')}/"
                    
                    matched_kw = None
                    for kw in raw_keywords:
                        if kw in caption_lower:
                            matched_kw = kw
                            break
                            
                    if not matched_kw:
                        continue
                        
                    is_commercial, evidence = is_commercial_campaign(caption, matched_kw, item)
                    
                    if only_paid and not is_commercial:
                        continue
                        
                    results.append({
                        "Influencer": f"@{owner}",
                        "Date": post_date.strftime("%Y-%m-%d"),
                        "Matched Keyword": matched_kw,
                        "Campaign Status": "Commercial / Sponsored" if is_commercial else "Organic Mention",
                        "Evidence": evidence,
                        "Post Link": post_url,
                        "Caption Preview": (caption[:120] + "...") if len(caption) > 120 else caption
                    })
            except Exception as e:
                st.error(f"❌ Error during scanning: {e}")

        if results:
            df = pd.DataFrame(results)
            st.success(f"🎉 Found **{len(results)}** matching posts!")
            st.dataframe(df, column_config={"Post Link": st.column_config.LinkColumn("Post Link")}, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results as CSV", csv, f"influencer_results_{date.today()}.csv", "text/csv")
        else:
            st.warning("❌ No matching posts found matching your criteria.")
