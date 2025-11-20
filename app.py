import streamlit as st
import pandas as pd
import requests
import zipfile
import io
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. 系統全域設定 ---
st.set_page_config(page_title="房地產阿宥 - 大數據分析系統", layout="wide", page_icon="🏠")

# 縣市代碼對照表
CITY_CODE = {
    '臺北市': 'A', '新北市': 'F', '桃園市': 'H', '臺中市': 'B', '臺南市': 'D', '高雄市': 'E',
    '基隆市': 'C', '新竹市': 'O', '新竹縣': 'J', '宜蘭縣': 'G', '苗栗縣': 'K', 
    '彰化縣': 'N', '南投縣': 'L', '雲林縣': 'P', '嘉義市': 'I', '嘉義縣': 'Q', 
    '屏東縣': 'T', '花蓮縣': 'U', '臺東縣': 'V', '澎湖縣': 'X', '金門縣': 'W'
}

# --- 2. 核心功能模組 ---

@st.cache_data(ttl=3600)
def fetch_data(season_str):
    """下載內政部資料 (ZIP)"""
    url = f"https://plvr.land.moi.gov.tw//DownloadSeason?season={season_str}&type=zip&fileName=lvr_landcsv.zip"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"資料下載失敗: {e}")
        return None

def process_data(zip_content, city_name, district_list, type_filter):
    """資料清洗、計算屋齡、計算單價"""
    if not zip_content:
        return None
    
    city_char = CITY_CODE[city_name]
    filename = f"{city_char}_lvr_land_A.csv" # A代表買賣
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            if filename not in z.namelist():
                return None
                
            # 讀取並處理 Header (跳過英文說明)
            df = pd.read_csv(z.open(filename), dtype={'交易年月日': str, '建築完成年月': str})
            df = df.iloc[1:].copy()
            
            # 1. 篩選區域
            if district_list:
                df = df[df['鄉鎮市區'].isin(district_list)]
            
            # 2. 篩選標的
            if type_filter == "房地":
                df = df[df['交易標的'].str.contains('房地') | df['交易標的'].str.contains('建物')]
            elif type_filter == "土地":
                df = df[df['交易標的'].str.contains('土地') & ~df['交易標的'].str.contains('房地')]
            
            # 3. 數值轉型與填補
            cols = ['總價元', '單價元平方公尺', '建物移轉總面積平方公尺', '土地移轉總面積平方公尺']
            for c in cols:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            # 4. 計算單價與坪數
            df['總價_萬元'] = df['總價元'] / 10000
            df['面積_坪'] = df['建物移轉總面積平方公尺'] * 0.3025
            
            # 純土地處理
            mask_land = df['面積_坪'] == 0
            df.loc[mask_land, '面積_坪'] = df.loc[mask_land, '土地移轉總面積平方公尺'] * 0.3025
            
            # 重新計算單價 (避免原始資料缺失)
            df['單價_萬元_坪'] = df['總價_萬元'] / df['面積_坪']
            df['單價_萬元_坪'] = df['單價_萬元_坪'].replace([np.inf, -np.inf], 0).fillna(0)

            # 5. 處理日期與屋齡
            def parse_roc_year(x):
                try:
                    if pd.notna(x) and len(x) >= 6:
                        return int(x[:-4]) + 1911
                    return None
                except:
                    return None

            df['交易年_西元'] = df['交易年月日'].apply(parse_roc_year)
            df = df.dropna(subset=['交易年_西元'])
            
            # 計算屋齡 (空白=0)
            def calc_age(row):
                try:
                    build_date = row['建築完成年月']
                    if pd.isna(build_date) or len(str(build_date)) < 3:
                        return 0
                    build_year = int(str(build_date)[:-4]) + 1911
                    age = row['交易年_西元'] - build_year
                    return max(age, 0)
                except:
                    return 0
            
            df['屋齡'] = df.apply(calc_age, axis=1)
            
            # 6. 排除極端值
            df = df[(df['單價_萬元_坪'] > 0.1) & (df['單價_萬元_坪'] < 300)]
            
            return df
    except Exception as e:
        st.error(f"資料處理發生錯誤: {e}")
        return None

def analyze_best_range(df, col, step):
    """找出交易量最大的價格區間"""
    if df.empty: return None, 0
    min_v = int(df[col].min())
    max_v = int(df[col].quantile(0.95))
    if max_v <= min_v: max_v = min_v + step
    
    bins = range(min_v, max_v + step, step)
    out = pd.cut(df[col], bins=bins, include_lowest=True)
    counts = out.value_counts().sort_values(ascending=False)
    if counts.empty: return None, 0
    return counts.index[0], counts.iloc[0]

# --- 3. 使用者介面 (UI) ---

# 頁首橫幅
st.markdown("""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='color: white; text-align: center; margin: 0;'>🏠 房地產阿宥 - 大數據分析系統</h1>
        <p style='color: #e0e0e0; text-align: center; margin: 5px 0 0 0;'>群義房屋雲科店 | 專業證照：(111)登字第412217號 | ☎️ 0906-707-964</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("🔍 房產分析設定")
st.sidebar.write("自動爬取內政部實價登錄資料")

# 下拉選單
season = st.sidebar.selectbox("1. 選擇季度", ['113S2', '113S1', '112S4', '112S3', '112S2', '112S1'], index=0)

# 預設雲林縣
city_list = list(CITY_CODE.keys())
default_city_index = city_list.index('雲林縣') if '雲林縣' in city_list else 0
city = st.sidebar.selectbox("2. 選擇縣市", city_list, index=default_city_index)

# 觸發爬蟲
zip_file = fetch_data(season)

if zip_file:
    # 預先讀取鄉鎮市區列表
    temp_df = process_data(zip_file, city, [], "全部")
    if temp_df is not None:
        districts = sorted(temp_df['鄉鎮市區'].unique())
        
        # 預設選擇前2個行政區
        default_districts = districts[:2] if len(districts) >= 2 else districts
        selected_dist = st.sidebar.multiselect("3. 選擇鄉鎮市區 (可複選)", districts, default=default_districts)
        target_type = st.sidebar.radio("4. 交易標的", ["房地", "土地"])
        
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🚀 開始分析", type="primary"):
            if not selected_dist:
                st.warning("請至少選擇一個行政區！")
            else:
                with st.spinner('資料清洗與計算中...'):
                    df_final = process_data(zip_file, city, selected_dist, target_type)
                
                if df_final is not None and not df_final.empty:
                    # --- 主畫面 ---
                    st.title(f"📊 {city} {season} 市場分析報告")
                    st.markdown(f"針對 **{'、'.join(selected_dist)}** 之 **{target_type}** 交易資料分析")
                    
                    # 關鍵指標 (KPI)
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                    kpi1.metric("成交筆數", f"{len(df_final):,} 筆")
                    kpi2.metric("平均單價", f"{df_final['單價_萬元_坪'].mean():.1f} 萬/坪")
                    kpi3.metric("單價中位數", f"{df_final['單價_萬元_坪'].median():.1f} 萬/坪")
                    kpi4.metric("平均總價", f"{df_final['總價_萬元'].mean():.0f} 萬元")
                    
                    st.markdown("---")

                    # --- AI 自動解讀區 ---
                    st.subheader("🤖 市場行情自動解讀")
                    
                    best_price_range, best_price_count = analyze_best_range(df_final, '單價_萬元_坪', 5)
                    best_total_range, best_total_count = analyze_best_range(df_final, '總價_萬元', 100)
                    
                    col_txt1, col_txt2 = st.columns(2)
                    with col_txt1:
                        if best_price_range is not None:
                            st.info(f"**🔥 最熱門單價帶：{best_price_range.left:.1f} ~ {best_price_range.right:.1f} 萬/坪**\n\n"
                                    f"此區間成交 {best_price_count} 筆，是市場接受度最高的價格。")
                    with col_txt2:
                        if best_total_range is not None:
                            st.success(f"**💰 最熱門總價帶：{best_total_range.left:.0f} ~ {best_total_range.right:.0f} 萬元**\n\n"
                                       f"若是投資或自住，此總價區間流動性最好。")

                    # --- 圖表區 ---
                    
                    # 1. 價格分佈圖
                    tab1, tab2 = st.tabs(["單價分佈 (Histogram)", "總價分佈 (Histogram)"])
                    with tab1:
                        fig_p = px.histogram(df_final, x="單價_萬元_坪", nbins=40, title="單價分佈圖", color_discrete_sequence=['#636EFA'])
                        fig_p.add_vline(x=df_final['單價_萬元_坪'].median(), line_dash="dash", line_color="red", annotation_text="中位數")
                        st.plotly_chart(fig_p, use_container_width=True)
                    with tab2:
                        fig_t = px.histogram(df_final, x="總價_萬元", nbins=40, title="總價分佈圖", color_discrete_sequence=['#00CC96'])
                        st.plotly_chart(fig_t, use_container_width=True)

                    # 2. 趨勢分析
                    st.subheader("📈 時間趨勢分析")
                    df_final['交易年月'] = df_final['交易年月日'].str[:-2]
                    trend = df_final.groupby('交易年月').agg({'單價_萬元_坪': 'mean', '總價_萬元': 'count'}).reset_index()
                    trend.columns = ['交易年月', '平均單價', '成交量']
                    trend = trend.sort_values('交易年月')

                    fig_combo = go.Figure()
                    fig_combo.add_trace(go.Bar(x=trend['交易年月'], y=trend['成交量'], name="成交量", marker_color='rgba(200, 200, 200, 0.7)'))
                    fig_combo.add_trace(go.Scatter(x=trend['交易年月'], y=trend['平均單價'], name="平均單價", yaxis='y2', line=dict(color='red', width=3)))
                    fig_combo.update_layout(
                        yaxis=dict(title="成交量 (筆)"),
                        yaxis2=dict(title="平均單價 (萬/坪)", overlaying='y', side='right'),
                        title="量價走勢圖"
                    )
                    st.plotly_chart(fig_combo, use_container_width=True)

                    # 3. 屋齡與行政區分析
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.subheader("🏚️ 屋齡與價格關係")
                        df_final['屋齡分類'] = pd.cut(df_final['屋齡'], bins=[-1, 5, 20, 100], labels=['新成屋(0-5)', '中古屋(5-20)', '老屋(>20)'])
                        fig_age = px.box(df_final, x="屋齡分類", y="單價_萬元_坪", color="屋齡分類", title="不同屋齡之單價行情")
                        st.plotly_chart(fig_age, use_container_width=True)
                    
                    with col_chart2:
                        st.subheader("📍 各行政區價格比較")
                        fig_dist = px.box(df_final, x="鄉鎮市區", y="單價_萬元_坪", title="行政區價格比較")
                        st.plotly_chart(fig_dist, use_container_width=True)

                    # --- 資料下載區 ---
                    st.markdown("---")
                    st.subheader("📥 資料下載")
                    csv = df_final.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="下載整理好的 CSV 資料表",
                        data=csv,
                        file_name=f'{city}_{season}_analyzed.csv',
                        mime='text/csv',
                        type="primary"
                    )
                    
                    with st.expander("點擊查看詳細資料表"):
                        st.dataframe(df_final[['鄉鎮市區', '交易年月日', '屋齡', '單價_萬元_坪', '總價_萬元', '面積_坪']].head(100))
                else:
                    st.error("查無資料，請嘗試放寬篩選條件。")
    else:
        st.error("無法讀取資料，請確認網路連線或稍後再試。")
else:
    st.info("正在連接內政部伺服器...")

# 頁尾
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>© 2024 房地產阿宥 | 群義房屋雲科店 | 資料來源：內政部實價登錄</p>
        <p>專業證照：(111)登字第412217號 | 聯絡電話：0906-707-964</p>
    </div>
""", unsafe_allow_html=True)
