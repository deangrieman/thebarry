import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime


# File to save/load data
DATA_FILE = "golf_tournament_data.json"


# Load data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": [], "rounds": {}, "holes": 18, "use_net_skins": False, "carry_over": True}


# Save data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


data = load_data()


st.set_page_config(page_title="Golf Tournament Tracker", layout="wide")
st.title("🏌️ The Barry Golf Tournament Tracker")
st.markdown("Track multiple rounds, **skins** for your group.")


# Sidebar setup
with st.sidebar:
    st.header("Setup")
    num_holes = st.number_input("Number of Holes", min_value=9, max_value=18, value=data.get("holes", 18))
    data["holes"] = num_holes
    
    use_net = st.checkbox("Use Net Scores for Skins (requires handicaps)", value=data.get("use_net_skins", False))
    data["use_net_skins"] = use_net
    
    carry = st.checkbox("Enable Skins Carry-Over", value=data.get("carry_over", True))
    data["carry_over"] = carry
    
    # Players
    st.subheader("Players")
    new_player = st.text_input("Add Player")
    if st.button("Add Player") and new_player.strip():
        if new_player.strip() not in data["players"]:
            data["players"].append(new_player.strip())
            save_data(data)
    
    if data["players"]:
        player_to_remove = st.selectbox("Remove Player", [""] + data["players"])
        if player_to_remove and st.button("Remove"):
            data["players"].remove(player_to_remove)
            save_data(data)
    
    st.write("**Current Players:**", ", ".join(data["players"]) if data["players"] else "None yet")


# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Add/Edit Scores", "Leaderboards", "Skins", "Putts & Stats"])


with tab1:
    st.header("Enter Scores")
    if not data["players"]:
        st.warning("Add players in the sidebar first!")
    else:
        round_name = st.text_input("Round Name (e.g., Round 1 - Day 1)", value=f"Round {len(data['rounds']) + 1}")
        
        if round_name not in data["rounds"]:
            data["rounds"][round_name] = {player: {"scores": [0]*num_holes, "putts": [0]*num_holes, "handicap": 0} for player in data["players"]}
        
        selected_player = st.selectbox("Select Player", data["players"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"{selected_player} - Strokes")
            for h in range(num_holes):
                key = f"score_{round_name}_{selected_player}_{h}"
                score = st.number_input(f"Hole {h+1}", min_value=0, max_value=20, value=data["rounds"][round_name][selected_player]["scores"][h], key=key)
                data["rounds"][round_name][selected_player]["scores"][h] = score
        
        with col2:
            st.subheader(f"{selected_player} - Putts")
            for h in range(num_holes):
                key = f"putt_{round_name}_{selected_player}_{h}"
                putts = st.number_input(f"Hole {h+1} Putts", min_value=0, max_value=10, value=data["rounds"][round_name][selected_player]["putts"][h], key=key)
                data["rounds"][round_name][selected_player]["putts"][h] = putts
        
        if st.button("Save Round Scores"):
            save_data(data)
            st.success(f"Scores saved for {round_name}!")


with tab2:
    st.header("Tournament Leaderboards")
    if data["rounds"]:
        round_list = list(data["rounds"].keys())
        selected_rounds = st.multiselect("Select Rounds to Include", round_list, default=round_list)
        
        totals = {}
        for player in data["players"]:
            total_strokes = 0
            total_putts = 0
            rounds_played = 0
            for rname in selected_rounds:
                if player in data["rounds"][rname]:
                    scores = data["rounds"][rname][player]["scores"]
                    total_strokes += sum(scores)
                    total_putts += sum(data["rounds"][rname][player]["putts"])
                    rounds_played += 1
            if rounds_played > 0:
                totals[player] = {
                    "Total Strokes": total_strokes,
                    "Avg Strokes/Round": round(total_strokes / rounds_played, 1),
                    "Total Putts": total_putts,
                    "Avg Putts/Round": round(total_putts / rounds_played, 1),
                    "Rounds Played": rounds_played
                }
        
        if totals:
            df = pd.DataFrame.from_dict(totals, orient="index").sort_values("Total Strokes")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No scores entered yet.")
    else:
        st.info("No rounds yet.")


with tab3:
    st.header("Skins")
    if not data["rounds"]:
        st.info("Enter scores first.")
    else:
        round_for_skins = st.selectbox("Calculate Skins for Round", list(data["rounds"].keys()))
        players_in_round = list(data["rounds"][round_for_skins].keys())
        
        # Build score matrix
        scores_df = pd.DataFrame(index=players_in_round, columns=[f"Hole {h+1}" for h in range(num_holes)])
        for p in players_in_round:
            scores_df.loc[p] = data["rounds"][round_for_skins][p]["scores"]
        
        st.subheader("Scores")
        st.dataframe(scores_df)
        
        # Calculate skins
        skins = {p: 0 for p in players_in_round}
        carry = 1 if data["carry_over"] else 0
        current_value = 1
        
        for h in range(num_holes):
            hole_scores = scores_df.iloc[:, h].astype(int)
            min_score = hole_scores.min()
            winners = hole_scores[hole_scores == min_score]
            
            if len(winners) == 1:  # Unique winner
                winner = winners.index[0]
                skins[winner] += current_value
                current_value = 1
            else:
                # Tie -> carry over
                if data["carry_over"]:
                    current_value += 1
                else:
                    current_value = 1  # or 0 depending on preference
        
        skins_df = pd.DataFrame.from_dict(skins, orient="index", columns=["Skins Won"]).sort_values("Skins Won", ascending=False)
        st.subheader("Skins Results")
        st.dataframe(skins_df)
        
        total_skins = sum(skins.values())
        st.write(f"Total skins awarded: **{total_skins}** (out of possible {num_holes} if no carries)")


with tab4:
    st.header("Putts & Detailed Stats")
    if data["rounds"]:
        round_choice = st.selectbox("View Putts for Round", list(data["rounds"].keys()))
        putts_df = pd.DataFrame(index=data["players"], columns=[f"Hole {h+1}" for h in range(num_holes)])
        for p in data["players"]:
            if p in data["rounds"][round_choice]:
                putts_df.loc[p] = data["rounds"][round_choice][p]["putts"]
        st.dataframe(putts_df)
        
        # Simple putts summary
        putts_total = putts_df.sum(axis=1).sort_values()
        st.bar_chart(putts_total)
        st.write("**Total Putts per Player** (lower is better)")


# Footer
st.sidebar.markdown("---")
if st.sidebar.button("Reset All Data"):
    if st.sidebar.checkbox("Confirm delete all data?"):
        os.remove(DATA_FILE) if os.path.exists(DATA_FILE) else None
        st.rerun()


st.caption("Data saved automatically to golf_tournament_data.json. Share the app or run it on Streamlit Cloud for group access.")
