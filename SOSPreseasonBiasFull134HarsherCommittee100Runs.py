import random 
import copy
import matplotlib.pyplot as plt

# =========================
#  1) Simulation Parameters
# =========================
DEFAULT_NUM_TEAMS = 134
DEFAULT_NUM_WEEKS = 12
DEFAULT_RUNS = 100  # 100 runs to remove statisitcal anomalies 

# =========================
#  2) Generate Teams
# =========================
def generate_teams(num_teams=DEFAULT_NUM_TEAMS):
    """
    Each team: {
      'name': e.g. "Team #1", ..., "Team #134",
      'true_rank': 1..134 (1=best),
      'cfp_rank': 1..134 (1=top in CFP),
      'season_points': 0
    }
    Inverting the preseason CFP so the best team (true_rank=1) gets cfp_rank=134, etc.
    """
    teams = []
    for i in range(1, num_teams + 1):
        true_rank = i
        # Inverse assignment for initial CFP
        cfp_rank = num_teams - i + 1
        t = {
            'name': f"Team #{i}",
            'true_rank': true_rank,
            'cfp_rank': cfp_rank,
            'season_points': 0
        }
        teams.append(t)
    return teams

# =========================
#  3) Probability of Win (Game logic)
# =========================
def probability_of_win(team_a_true, team_b_true):
    """
    FBS-like logic:
      Let diff = (team_b_true - team_a_true).
      If diff>0 => team_a is better => base_prob for A
      If diff<0 => team_a is worse => 1 - base_prob

      Bins (abs_diff):
       <= 5     => 50/50
       6-10     => 65/35
       11-15    => 75/25
       16-25    => 85/15
       26-50    => 95/5
       51-100   => 98/2
       >100     => 99/1
    """
    diff = team_b_true - team_a_true
    abs_diff = abs(diff)
    
    if abs_diff <= 5:
        base_prob = 0.50
    elif abs_diff <= 10:
        base_prob = 0.65
    elif abs_diff <= 15:
        base_prob = 0.75
    elif abs_diff <= 25:
        base_prob = 0.85
    elif abs_diff <= 50:
        base_prob = 0.95
    elif abs_diff <= 100:
        base_prob = 0.98
    else:
        base_prob = 0.99
    
    if diff > 0:
        return base_prob
    else:
        return 1 - base_prob

# =========================
#  4) Determine CFP Points (Harsher Variation)
# =========================
def determine_cfp_points(team_cfp_rank, opponent_cfp_rank, did_win):
    """
    New 'harsh' system for CFP points:
    
    Winners:
      - 9 points: beating a stronger team (opponent_cfp_rank < yours)
      - 8 points: beating a team up to 7 spots below (diff ≤ 7)
      - 7 points: beating a team 8–24 spots below
      - 6 points: beating a team 25+ spots below

    Losers:
      - 4 points: losing to a stronger team (opponent_cfp_rank < yours)
      - 2 points: losing to a team 1–5 spots below (1 ≤ diff ≤ 5)
      - 1 point : losing to a team 6–24 spots below (6 ≤ diff ≤ 24)
      - 0 points: losing to a team 25+ spots below (diff ≥ 25)

    Here, "lower" means opponent_cfp_rank > team_cfp_rank (a worse rank number).
    """
    diff = opponent_cfp_rank - team_cfp_rank  # if negative => opponent is stronger
    if did_win:
        # Win:
        if opponent_cfp_rank < team_cfp_rank:
            # beating a stronger team
            return 9
        elif diff <= 7:
            return 8
        elif diff <= 24:
            return 7
        else:
            return 6
    else:
        # Loss:
        if opponent_cfp_rank < team_cfp_rank:
            # lost to a stronger team
            return 4
        else:
            if diff <= 5:
                return 2
            elif diff <= 24:
                return 1
            else:
                return 0

# =========================
#  5) Tie-Break
# =========================
def break_ties(teams_sorted, teams_last_week):
    """
    Sort by season_points desc; if tie, keep last week's order
    """
    name_to_idx = {t['name']: i for i, t in enumerate(teams_last_week)}
    teams_sorted.sort(key=lambda t: name_to_idx[t['name']])
    teams_sorted.sort(key=lambda t: t['season_points'], reverse=True)
    return teams_sorted

# =========================
#  6) Single-Season Simulation
# =========================
def simulate_single_season(num_teams=DEFAULT_NUM_TEAMS, num_weeks=DEFAULT_NUM_WEEKS, seed=None):
    """
    Returns weekly_rankings: list of length num_weeks+1,
    each element is a deep copy of the teams in sorted CFP order for that week.
    """
    if seed is not None:
        random.seed(seed)
    else:
        random.seed()
    
    teams = generate_teams(num_teams)
    # Preseason
    current_cfp_order = sorted(teams, key=lambda t: t['cfp_rank'])
    weekly_rankings = [copy.deepcopy(current_cfp_order)]
    
    for w in range(1, num_weeks + 1):
        indices = list(range(num_teams))
        random.shuffle(indices)
        matchups = [(indices[i], indices[i+1]) for i in range(0, num_teams, 2)]
        
        # map from name->last week's CFP rank
        last_week_map = {t['name']: (idx+1) for idx, t in enumerate(current_cfp_order)}
        
        for idx_a, idx_b in matchups:
            team_a = teams[idx_a]
            team_b = teams[idx_b]
            
            p_a_wins = probability_of_win(team_a['true_rank'], team_b['true_rank'])
            a_wins = (random.random() < p_a_wins)
            
            cfp_a = last_week_map[team_a['name']]
            cfp_b = last_week_map[team_b['name']]
            
            pts_a = determine_cfp_points(cfp_a, cfp_b, a_wins)
            pts_b = determine_cfp_points(cfp_b, cfp_a, not a_wins)
            
            team_a['season_points'] += pts_a
            team_b['season_points'] += pts_b
        
        # Re-sort
        teams_sorted = sorted(teams, key=lambda t: t['season_points'], reverse=True)
        new_cfp_order = break_ties(teams_sorted, current_cfp_order)
        
        # Update cfp_rank
        for rank_pos, tdict in enumerate(new_cfp_order):
            tdict['cfp_rank'] = rank_pos + 1
        
        weekly_rankings.append(copy.deepcopy(new_cfp_order))
        current_cfp_order = new_cfp_order
    
    return weekly_rankings

# =========================
#  7) Compute Weekly Stats
# =========================
def compute_weekly_stats(weekly_rankings):
    """
    Returns 6 lists (each length = len(weekly_rankings)):
      avg_diff[w]      = average of |cfp_rank - true_rank| at week w
      max_diff[w]      = max of |cfp_rank - true_rank| at week w
      biggest_rise[w]  = largest improvement (old_rank - new_rank) from w-1 to w
      biggest_fall[w]  = largest drop  (new_rank - old_rank) from w-1 to w
      avg_diff25[w]    = average difference for top 25 teams only
      max_diff25[w]    = maximum difference for top 25 teams only

    For w=0, biggest_rise=0, biggest_fall=0 (no prior week).
    """
    num_weeks = len(weekly_rankings)
    avg_diff = [0]*num_weeks
    max_diff = [0]*num_weeks
    biggest_rise = [0]*num_weeks
    biggest_fall = [0]*num_weeks

    # Two new arrays for top-25 teams' difference metrics
    avg_diff25 = [0]*num_weeks
    max_diff25 = [0]*num_weeks

    # We'll create name->cfp_rank for each week for easy referencing
    week_to_map = []
    for w, snapshot in enumerate(weekly_rankings):
        d = {team['name']: team['cfp_rank'] for team in snapshot}
        week_to_map.append(d)
        
        # compute avg & max difference for all teams at week w
        diffs = [abs(team['cfp_rank'] - team['true_rank']) for team in snapshot]
        avg_diff[w] = sum(diffs)/len(diffs)
        max_diff[w] = max(diffs)

        # For the top 25 teams only (or fewer if snapshot < 25)
        top_25 = snapshot[:25]
        diffs_25 = [abs(t['cfp_rank'] - t['true_rank']) for t in top_25]
        avg_diff25[w] = sum(diffs_25)/len(diffs_25)
        max_diff25[w] = max(diffs_25)

    # biggest rise/fall among all teams (not just top-25)
    for w in range(1, num_weeks):
        map_prev = week_to_map[w-1]
        map_this = week_to_map[w]
        
        best_improvement = 0
        worst_fall = 0
        for name in map_this:
            old_rank = map_prev[name]
            new_rank = map_this[name]
            movement = old_rank - new_rank
            if movement > best_improvement:
                best_improvement = movement
            drop = new_rank - old_rank
            if drop > worst_fall:
                worst_fall = drop
        
        biggest_rise[w] = best_improvement
        biggest_fall[w] = worst_fall
    
    return avg_diff, max_diff, biggest_rise, biggest_fall, avg_diff25, max_diff25

# =========================
#  8) Multiple Runs & Aggregation
# =========================
def run_multiple_simulations(num_runs=DEFAULT_RUNS,
                             num_teams=DEFAULT_NUM_TEAMS,
                             num_weeks=DEFAULT_NUM_WEEKS):
    """
    Run the simulation `num_runs` times.
    For each run, compute the 6 weekly stats arrays.
    Then average them across all runs.

    Returns:
      avg_avg_diff, avg_max_diff, avg_biggest_rise, avg_biggest_fall, avg_avg_diff25, avg_max_diff25
      (each a list of length num_weeks+1)
    """
    all_avg_diffs = []
    all_max_diffs = []
    all_biggest_rise = []
    all_biggest_fall = []
    all_avg_diff25 = []
    all_max_diff25 = []
    
    for _ in range(num_runs):
        weekly_rankings = simulate_single_season(num_teams, num_weeks, seed=None)
        # Now compute the 6 arrays from this single run
        ad, md, rise, fall, ad25, md25 = compute_weekly_stats(weekly_rankings)
        
        all_avg_diffs.append(ad)
        all_max_diffs.append(md)
        all_biggest_rise.append(rise)
        all_biggest_fall.append(fall)
        all_avg_diff25.append(ad25)
        all_max_diff25.append(md25)
    
    weeks_count = num_weeks + 1
    avg_avg_diff = [0]*(weeks_count)
    avg_max_diff = [0]*(weeks_count)
    avg_rise = [0]*(weeks_count)
    avg_fall = [0]*(weeks_count)
    avg_avg_diff25 = [0]*(weeks_count)
    avg_max_diff25 = [0]*(weeks_count)
    
    for w in range(weeks_count):
        sum_avg_d = sum(run[w] for run in all_avg_diffs)
        sum_max_d = sum(run[w] for run in all_max_diffs)
        sum_rise  = sum(run[w] for run in all_biggest_rise)
        sum_fall  = sum(run[w] for run in all_biggest_fall)
        sum_ad25  = sum(run[w] for run in all_avg_diff25)
        sum_md25  = sum(run[w] for run in all_max_diff25)

        avg_avg_diff[w] = sum_avg_d / num_runs
        avg_max_diff[w] = sum_max_d / num_runs
        avg_rise[w] = sum_rise / num_runs
        avg_fall[w] = sum_fall / num_runs
        avg_avg_diff25[w] = sum_ad25 / num_runs
        avg_max_diff25[w] = sum_md25 / num_runs
    
    return (avg_avg_diff, avg_max_diff,
            avg_rise, avg_fall,
            avg_avg_diff25, avg_max_diff25)

# =========================
# 9) Plot Aggregated Stats
# =========================
def plot_aggregated_stats(avg_avg_diff, avg_max_diff, avg_biggest_rise, avg_biggest_fall,
                          avg_avg_diff25, avg_max_diff25, num_runs):
    """
    Takes six lists (each length = num_weeks+1):
      1) avg_avg_diff     (all teams)
      2) avg_max_diff     (all teams)
      3) avg_biggest_rise (all teams)
      4) avg_biggest_fall (all teams)
      5) avg_avg_diff25   (Top 25)
      6) avg_max_diff25   (Top 25)

    and plots them, weeks on x-axis.
    """
    weeks_count = len(avg_avg_diff)
    x_vals = list(range(weeks_count))
    x_labels = [f"W{w}" for w in x_vals]

    # 1) Average Discrepancy (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_avg_diff, marker='o', label='Avg Diff (All)')
    plt.title(f"Average |CFP - True| (Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Average Discrepancy (All)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 2) Max Discrepancy (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_max_diff, marker='o', color='red', label='Max Diff (All)')
    plt.title(f"Maximum |CFP - True| (Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Maximum Discrepancy (All)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.ylim(bottom=0)
    plt.tight_layout()
    plt.show()

    # 3) Biggest Rise (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_biggest_rise, marker='o', color='green', label='Biggest Rise')
    plt.title(f"Biggest Rise in Rank (All) (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Number of Spots Gained")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 4) Biggest Fall (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_biggest_fall, marker='o', color='orange', label='Biggest Fall')
    plt.title(f"Biggest Fall in Rank (All) (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Number of Spots Dropped")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 5) Average Discrepancy (Top 25)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_avg_diff25, marker='o', label='Avg Diff (Top25)')
    plt.title(f"Average |CFP - True| (Top 25) (Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Average Discrepancy (Top 25)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 6) Max Discrepancy (Top 25)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_max_diff25, marker='o', color='purple', label='Max Diff (Top25)')
    plt.title(f"Maximum |CFP - True| (Top 25) (Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Maximum Discrepancy (Top 25)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.ylim(bottom=0)
    plt.tight_layout()
    plt.show()

# =========================
# 10) Main
# =========================
def main():
    num_runs = 100
    num_teams = 134
    num_weeks = 12
    
    print(f"Running {num_runs} simulations [Harsh Committee Variation] with {num_teams} teams for {num_weeks} weeks each...")
    
    (avg_avg_diff, avg_max_diff, 
     avg_biggest_rise, avg_biggest_fall,
     avg_avg_diff25, avg_max_diff25) = run_multiple_simulations(
         num_runs=num_runs,
         num_teams=num_teams,
         num_weeks=num_weeks
    )
    
    # Print out the weekly data points, including the new top-25 columns
    print("\n=== Weekly Averages (Harsh Committee) Over 100 Runs ===")
    print(f"{'Week':<4} | {'AvgDiff':>8} | {'MaxDiff':>8} | {'MaxRise':>8} | {'MaxFall':>8} | {'AvgD25':>8} | {'MaxD25':>8}")
    print("-"*62)
    weeks_count = num_weeks + 1
    
    for w in range(weeks_count):
        print(f"{w:<4d} | "
              f"{avg_avg_diff[w]:8.2f} | "
              f"{avg_max_diff[w]:8.2f} | "
              f"{avg_biggest_rise[w]:8.2f} | "
              f"{avg_biggest_fall[w]:8.2f} | "
              f"{avg_avg_diff25[w]:8.2f} | "
              f"{avg_max_diff25[w]:8.2f}")

    # Now plot the aggregated results, including the new top-25 metrics
    plot_aggregated_stats(avg_avg_diff, avg_max_diff,
                          avg_biggest_rise, avg_biggest_fall,
                          avg_avg_diff25, avg_max_diff25,
                          num_runs)

if __name__ == "__main__":
    main()
