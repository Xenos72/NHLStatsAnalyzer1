import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- Configuration ---
st.set_page_config(
    page_title="NHL Stats Analyzer",
    page_icon="🏒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants ---
BASE_URL = "https://api-web.nhle.com/v1"
SEARCH_URL = "https://search.d3.nhle.com/api/v1/search/player"

# Metrics Definition
METRIC_OPTIONS = {
    'cumulative': {
        'points': {'label': 'Points', 'unit': ''},
        'goals': {'label': 'Goals', 'unit': ''},
        'assists': {'label': 'Assists', 'unit': ''},
        'shots': {'label': 'Shots on Goal', 'unit': ''},
        'plusMinus': {'label': 'Plus/Minus', 'unit': ''},
        'evenStrengthPoints': {'label': 'Even Strength Points', 'unit': ''}
    },
    'projection': {
        'points': {'label': 'Points', 'unit': ''},
        'goals': {'label': 'Goals', 'unit': ''},
        'assists': {'label': 'Assists', 'unit': ''},
        'shots': {'label': 'Shots Per Game', 'unit': ''},
        'shootingPct': {'label': 'Shooting %', 'unit': '%'},
        'toi': {'label': 'Avg Time On Ice', 'unit': 'm'},
        'esToi': {'label': 'Avg Even Strength TOI', 'unit': 'm'},
        'evenStrengthPct': {'label': 'Even Strength % of Prod', 'unit': '%'},
        'plusMinus': {'label': 'Plus/Minus', 'unit': ''}
    },
    'distribution': {
        'pointsComp': {'label': 'Points (Goals vs Assists)', 'unit': ''},
        'pointsSit': {'label': 'Points Situation (ES/PP/SH)', 'unit': ''},
        'goalsSit': {'label': 'Goals Situation (ES/PP/SH)', 'unit': ''},
        'assistsSit': {'label': 'Assists Situation (ES/PP/SH)', 'unit': ''}
    }
}

COLORS = [
    '#38bdf8', # Blue
    '#f472b6', # Pink
    '#34d399'  # Emerald
]

# --- Helper Functions ---

def parse_toi(toi_str):
    if not toi_str:
        return 0.0
    try:
        mm, ss = map(int, toi_str.split(':'))
        return mm + (ss / 60.0)
    except:
        return 0.0

def format_season(season_id):
    s = str(season_id)
    return f"{s[2:4]}-{s[6:8]}"

@st.cache_data(ttl=3600)
def search_player(query):
    if len(query) < 3:
        return []
    try:
        url = f"{SEARCH_URL}?culture=en-us&limit=15&q={query}"
        resp = requests.get(url)
        data = resp.json()
        return data[:10]
    except Exception as e:
        return []

@st.cache_data(ttl=3600)
def get_player_details(player_id):
    try:
        url = f"{BASE_URL}/player/{player_id}/landing"
        resp = requests.get(url)
        return resp.json()
    except:
        return None

@st.cache_data(ttl=600)
def get_game_log(player_id, season):
    try:
        url = f"{BASE_URL}/player/{player_id}/game-log/{season}/2"
        resp = requests.get(url)
        return resp.json()
    except:
        return None

# --- Session State ---
if 'players' not in st.session_state:
    st.session_state.players = [] 

def add_player(player_data):
    if len(st.session_state.players) >= 3:
        st.warning("Maximum 3 players allowed.")
        return

    # Fetch details for seasons
    details = get_player_details(player_data['playerId'])
    if not details:
        st.error("Could not fetch player details.")
        return

    seasons = []
    if 'seasonTotals' in details:
        nhl_seasons = [s for s in details['seasonTotals'] if s['leagueAbbrev'] == 'NHL' and s['gameTypeId'] == 2]
        seen = set()
        for s in nhl_seasons:
            if s['season'] not in seen:
                seasons.append(s['season'])
                seen.add(s['season'])
        seasons.sort(reverse=True)
    
    if not seasons:
        seasons = [details.get('seasonId', 20232024)]

    st.session_state.players.append({
        'id': player_data['playerId'],
        'name': player_data.get('name', 'Unknown'),
        'team': player_data.get('teamAbbrev', 'NHL'),
        'selected_season': seasons[0],
        'available_seasons': seasons,
        'color_idx': len(st.session_state.players),
        'instance_id': datetime.now().timestamp()
    })

def remove_player(idx):
    st.session_state.players.pop(idx)
    for i, p in enumerate(st.session_state.players):
        p['color_idx'] = i

# --- Main Layout ---

st.title("NHL Stats Analyzer")
st.caption("A Xenos app based on live NHL API data")

# 1. Sidebar / Top Controls
with st.expander("Player Selection", expanded=True if not st.session_state.players else False):
    
    c1, c2 = st.columns([3, 1])
    with c1:
        search_q = st.text_input("Search Player (e.g. MacKinnon)", key="search_box")
    with c2:
        st.write("") 
        st.write("") 
        
    if len(search_q) >= 3:
        results = search_player(search_q)
        if results:
            st.markdown("### Results")
            for p in results:
                col_res, col_btn = st.columns([4, 1])
                with col_res:
                    st.write(f"**{p['name']}** ({p['teamAbbrev']})")
                with col_btn:
                    if st.button("Add", key=f"add_{p['playerId']}_{datetime.now()}"):
                        add_player(p)
                        st.rerun()

    if st.session_state.players:
        st.markdown("---")
        st.subheader("Selected Players")
        
        for i, p in enumerate(st.session_state.players):
            c_color, c_name, c_season, c_del = st.columns([0.2, 2, 2, 0.5])
            
            with c_color:
                st.markdown(f'<div style="background-color:{COLORS[p["color_idx"]]}; width:100%; height:20px; border-radius:4px; margin-top:10px;"></div>', unsafe_allow_html=True)
            
            with c_name:
                st.write(f"**{p['name']}**")
                st.caption(p['team'])
            
            with c_season:
                new_season = st.selectbox(
                    "Season", 
                    p['available_seasons'], 
                    index=p['available_seasons'].index(p['selected_season']),
                    format_func=format_season,
                    key=f"season_select_{i}_{p['instance_id']}",
                    label_visibility="collapsed"
                )
                if new_season != p['selected_season']:
                    st.session_state.players[i]['selected_season'] = new_season
                    st.rerun()
            
            with c_del:
                if st.button("✕", key=f"rem_{i}"):
                    remove_player(i)
                    st.rerun()

# 2. Configuration
st.divider()
col_mode, col_metric = st.columns(2)

with col_mode:
    view_mode = st.radio(
        "Analysis Mode", 
        ['Cumulative', '82-Gm Pace', 'Distribution'], 
        horizontal=True
    )
    mode_key = 'cumulative'
    if 'Pace' in view_mode: mode_key = 'projection'
    elif 'Distribution' in view_mode: mode_key = 'distribution'

with col_metric:
    options = METRIC_OPTIONS[mode_key]
    metric_keys = list(options.keys())
    metric_labels = [options[k]['label'] for k in metric_keys]
    
    selected_label = st.selectbox("Metric", metric_labels)
    selected_metric_id = next(k for k, v in options.items() if v['label'] == selected_label)
    selected_unit = options[selected_metric_id]['unit']

# 3. Data Processing & Visualization
if st.session_state.players:
    
    if st.button("Launch Analysis", type="primary", use_container_width=True):
        
        with st.spinner("Crunching numbers..."):
            
            all_dfs = []
            distribution_summaries = []
            
            for i, p in enumerate(st.session_state.players):
                log = get_game_log(p['id'], p['selected_season'])
                
                if log and 'gameLog' in log:
                    df = pd.DataFrame(log['gameLog'])
                    df['date_obj'] = pd.to_datetime(df['gameDate'])
                    df = df.sort_values('date_obj').reset_index(drop=True)
                    df['game_number'] = df.index + 1
                    
                    df['toi_val'] = df['toi'].apply(parse_toi)
                    df['pp_toi_val'] = df.get('powerPlayToi', pd.Series(['00:00']*len(df))).apply(parse_toi)
                    df['sh_toi_val'] = df.get('shorthandedToi', pd.Series(['00:00']*len(df))).apply(parse_toi)
                    
                    for col in ['goals', 'assists', 'points', 'shots', 'plusMinus', 'powerPlayPoints', 'shorthandedPoints', 'powerPlayGoals', 'shorthandedGoals']:
                        if col not in df.columns:
                            df[col] = 0

                    if mode_key == 'distribution':
                        totals = {
                            'goals': df['goals'].sum(),
                            'assists': df['assists'].sum(),
                            'points': df['points'].sum(),
                            'pp_goals': df['powerPlayGoals'].sum(),
                            'sh_goals': df['shorthandedGoals'].sum(),
                            'pp_points': df['powerPlayPoints'].sum(),
                            'sh_points': df['shorthandedPoints'].sum(),
                            'es_goals': df['goals'].sum() - df['powerPlayGoals'].sum() - df['shorthandedGoals'].sum(),
                            'es_points': df['points'].sum() - df['powerPlayPoints'].sum() - df['shorthandedPoints'].sum(),
                            'pp_assists': (df['powerPlayPoints'].sum() - df['powerPlayGoals'].sum()),
                            'sh_assists': (df['shorthandedPoints'].sum() - df['shorthandedGoals'].sum()),
                        }
                        totals['es_assists'] = df['assists'].sum() - totals['pp_assists'] - totals['sh_assists']
                        
                        dist_data = {'name': p['name'], 'season': format_season(p['selected_season']), 'color': COLORS[i]}
                        
                        if selected_metric_id == 'pointsComp':
                            dist_data['labels'] = ['Goals', 'Assists']
                            dist_data['values'] = [totals['goals'], totals['assists']]
                        elif selected_metric_id == 'pointsSit':
                            dist_data['labels'] = ['Even Strength', 'Power Play', 'Shorthanded']
                            dist_data['values'] = [totals['es_points'], totals['pp_points'], totals['sh_points']]
                        elif selected_metric_id == 'goalsSit':
                            dist_data['labels'] = ['Even Strength', 'Power Play', 'Shorthanded']
                            dist_data['values'] = [totals['es_goals'], totals['pp_goals'], totals['sh_goals']]
                        elif selected_metric_id == 'assistsSit':
                            dist_data['labels'] = ['Even Strength', 'Power Play', 'Shorthanded']
                            dist_data['values'] = [totals['es_assists'], totals['pp_assists'], totals['sh_assists']]
                            
                        distribution_summaries.append(dist_data)

                    else:
                        vals = []
                        
                        for _, row in df.iterrows():
                            val = 0
                            if selected_metric_id == 'points': val = row['points']
                            elif selected_metric_id == 'goals': val = row['goals']
                            elif selected_metric_id == 'assists': val = row['assists']
                            elif selected_metric_id == 'plusMinus': val = row['plusMinus']
                            elif selected_metric_id == 'shots': val = row['shots']
                            elif selected_metric_id == 'toi': val = row['toi_val']
                            elif selected_metric_id == 'esToi': val = max(0, row['toi_val'] - row['pp_toi_val'] - row['sh_toi_val'])
                            elif selected_metric_id == 'evenStrengthPoints': val = row['points'] - (row['powerPlayPoints'] + row['shorthandedPoints'])
                            
                            vals.append(val)
                        
                        df['stat_val'] = vals
                        
                        df['cum_val'] = df['stat_val'].cumsum()
                        df['cum_goals'] = df['goals'].cumsum()
                        df['cum_shots'] = df['shots'].cumsum()
                        df['cum_points'] = df['points'].cumsum()
                        df['cum_pp_sh_pts'] = (df['powerPlayPoints'] + df['shorthandedPoints']).cumsum()
                        
                        y_values = []
                        
                        for idx, row in df.iterrows():
                            gp = row['game_number']
                            res = 0
                            
                            if selected_metric_id == 'shootingPct':
                                res = (row['cum_goals'] / row['cum_shots'] * 100) if row['cum_shots'] > 0 else 0
                            elif selected_metric_id == 'evenStrengthPct':
                                res = ((row['cum_points'] - row['cum_pp_sh_pts']) / row['cum_points'] * 100) if row['cum_points'] > 0 else 0
                            elif selected_metric_id in ['toi', 'esToi']:
                                res = row['cum_val'] / gp 
                            elif selected_metric_id == 'shots' and mode_key == 'projection':
                                res = row['cum_val'] / gp 
                            else:
                                res = row['cum_val'] 
                            
                            final_val = res
                            if mode_key == 'projection':
                                is_rate = selected_metric_id in ['shootingPct', 'evenStrengthPct', 'toi', 'esToi', 'shots']
                                if not is_rate:
                                    final_val = (res / gp) * 82
                            
                            y_values.append(final_val)

                        df['y_final'] = y_values
                        df['player_name'] = p['name']
                        df['color'] = COLORS[i]
                        df['season_label'] = format_season(p['selected_season'])
                        
                        if mode_key == 'projection':
                            roll_y = []
                            for idx in range(len(df)):
                                if idx < 9:
                                    roll_y.append(None)
                                    continue
                                
                                slice_df = df.iloc[idx-9 : idx+1]
                                
                                s_val = slice_df['stat_val'].sum()
                                s_goals = slice_df['goals'].sum()
                                s_shots = slice_df['shots'].sum()
                                s_pts = slice_df['points'].sum()
                                s_spec = slice_df['powerPlayPoints'].sum() + slice_df['shorthandedPoints'].sum()
                                
                                r_res = 0
                                if selected_metric_id == 'shootingPct':
                                    r_res = (s_goals / s_shots * 100) if s_shots > 0 else 0
                                elif selected_metric_id == 'evenStrengthPct':
                                    r_res = ((s_pts - s_spec) / s_pts * 100) if s_pts > 0 else 0
                                elif selected_metric_id in ['toi', 'esToi']:
                                    r_res = s_val / 10
                                elif selected_metric_id == 'shots':
                                    r_res = s_val / 10 
                                else:
                                    r_res = s_val 
                                
                                r_final = r_res
                                is_rate = selected_metric_id in ['shootingPct', 'evenStrengthPct', 'toi', 'esToi', 'shots']
                                if not is_rate:
                                    r_final = (r_res / 10) * 82
                                
                                roll_y.append(r_final)
                            
                            df['y_rolling'] = roll_y

                        all_dfs.append(df)

            if mode_key == 'distribution':
                cols = st.columns(len(distribution_summaries))
                for idx, dist in enumerate(distribution_summaries):
                    with cols[idx]:
                        st.subheader(f"{dist['name']}")
                        st.caption(f"Season: {dist['season']}")
                        
                        fig = go.Figure(data=[go.Pie(
                            labels=dist['labels'],
                            values=dist['values'],
                            hole=.6,
                            marker_colors=[dist['color'], '#334155', '#94a3b8'],
                            textinfo='label+percent',
                            hoverinfo='label+value+percent'
                        )])
                        fig.update_layout(
                            showlegend=False,
                            margin=dict(t=0, b=0, l=0, r=0),
                            height=250,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white')
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        
                        data_rows = []
                        for l, v in zip(dist['labels'], dist['values']):
                            data_rows.append({"Category": l, "Value": f"{v:.1f}{selected_unit}"})
                        st.dataframe(pd.DataFrame(data_rows), hide_index=True, use_container_width=True)

            else:
                if not all_dfs:
                    st.warning("No game data available for selected parameters.")
                else:
                    fig = go.Figure()
                    
                    for i, df in enumerate(all_dfs):
                        fig.add_trace(go.Scatter(
                            x=df['game_number'],
                            y=df['y_final'],
                            mode='lines',
                            name=f"{df['player_name'][0]} ({df['season_label'][0]})",
                            line=dict(color=df['color'][0], width=3)
                        ))
                        
                        if mode_key == 'projection':
                            fig.add_trace(go.Scatter(
                                x=df['game_number'],
                                y=df['y_rolling'],
                                mode='lines',
                                name=f"{df['player_name'][0]} (Rolling)",
                                line=dict(color=df['color'][0], width=1, dash='dash'),
                                opacity=0.7
                            ))

                    fig.update_layout(
                        title=f"{selected_label} - {view_mode}",
                        xaxis_title="Game Number",
                        yaxis_title=f"{selected_label} ({selected_unit})" if selected_unit else selected_label,
                        hovermode="x unified",
                        height=500,
                        template="plotly_dark",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("View Raw Data"):
                        cols_to_show = ['player_name', 'game_number', 'y_final']
                        if mode_key == 'projection': cols_to_show.append('y_rolling')
                        combined = pd.concat(all_dfs)[cols_to_show]
                        st.dataframe(combined, use_container_width=True)

else:
    st.info("Please search and add players to begin.")
