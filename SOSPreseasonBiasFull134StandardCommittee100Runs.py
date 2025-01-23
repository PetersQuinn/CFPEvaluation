import random
import copy
import matplotlib.pyplot as plt

# =========================
#  1) Simulation Parameters
# =========================
DEFAULT_NUM_TEAMS = 134
DEFAULT_NUM_WEEKS = 12
DEFAULT_RUNS = 100  # 100 runs for averaging

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
        # Invert for initial CFP: best => cfp_rank=134, worst => cfp_rank=1
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
#  3) Probability of Win
# =========================
def probability_of_win(team_a_true, team_b_true):
    """
    FBS-like logic:
      Let diff = (team_b_true - team_a_true).
      If diff>0 => team_a is better => base_prob for team_a
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
#  4) Determine CFP Points
# =========================
def determine_cfp_points(team_cfp_rank, opponent_cfp_rank, did_win):
    """
    New CFP system:
      - 5 pts: Win vs. stronger team OR up to 7 spots below
      - 4 pts: Win vs. 8–24 spots below
      - 3 pts: Win vs. 25+ below OR lose to stronger team
      - 2 pts: Lose to a team 1–7 spots below
      - 1 pts: Lose to a team 8–24 spots below
      - 0 pts: Lose to a team 25+ below
    """
    if did_win:
        diff = opponent_cfp_rank - team_cfp_rank
        if opponent_cfp_rank < team_cfp_rank or diff <= 7:
            return 5
        elif diff <= 24:
            return 4
        else:
            return 3
    else:
        if opponent_cfp_rank < team_cfp_rank:
            return 3
        else:
            diff = opponent_cfp_rank - team_cfp_rank
            if diff <= 7:
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
    # Preseason CFP order
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
      1) avg_diff[w]      = average of |cfp_rank - true_rank| at week w
      2) max_diff[w]      = max of |cfp_rank - true_rank| at week w
      3) biggest_rise[w]  = largest improvement (old_rank - new_rank) from w-1 to w
      4) biggest_fall[w]  = largest drop  (new_rank - old_rank) from w-1 to w
      5) avg_diff25[w]    = average difference among only the top 25 teams
      6) max_diff25[w]    = max difference among only the top 25 teams

    For w=0, biggest_rise=0, biggest_fall=0 (no previous week).
    """
    num_weeks = len(weekly_rankings)
    avg_diff = [0]*num_weeks
    max_diff = [0]*num_weeks
    biggest_rise = [0]*num_weeks
    biggest_fall = [0]*num_weeks
    avg_diff25 = [0]*num_weeks
    max_diff25 = [0]*num_weeks
    
    # We'll create name->cfp_rank for each week for easy referencing
    week_to_map = []
    for w, snapshot in enumerate(weekly_rankings):
        d = {team['name']: team['cfp_rank'] for team in snapshot}
        week_to_map.append(d)
        
        # compute avg & max for all teams
        diffs = [abs(team['cfp_rank'] - team['true_rank']) for team in snapshot]
        avg_diff[w] = sum(diffs)/len(diffs)
        max_diff[w] = max(diffs)

        # For top 25 only (or fewer if <25 teams)
        top_25 = snapshot[:25]
        diffs25 = [abs(t['cfp_rank'] - t['true_rank']) for t in top_25]
        avg_diff25[w] = sum(diffs25)/len(diffs25)
        max_diff25[w] = max(diffs25)
    
    # biggest rise/fall among all teams (not top 25 only)
    for w in range(1, num_weeks):
        map_prev = week_to_map[w-1]
        map_this = week_to_map[w]
        
        best_improvement = 0
        worst_drop = 0
        for name in map_this:
            old_rank = map_prev[name]
            new_rank = map_this[name]
            movement = old_rank - new_rank
            if movement > best_improvement:
                best_improvement = movement
            drop = new_rank - old_rank
            if drop > worst_drop:
                worst_drop = drop
        
        biggest_rise[w] = best_improvement
        biggest_fall[w] = worst_drop
    
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

    Returns: a tuple of 6 lists of length (num_weeks+1):
      avg_avg_diff, avg_max_diff, avg_biggest_rise, avg_biggest_fall,
      avg_avg_diff25, avg_max_diff25
    """
    all_avg_diffs = []
    all_max_diffs = []
    all_biggest_rise = []
    all_biggest_fall = []
    all_avg_diffs25 = []
    all_max_diffs25 = []
    
    for _ in range(num_runs):
        weekly_rankings = simulate_single_season(num_teams, num_weeks, seed=None)
        (diff, mx, rise, fall, diff25, mx25) = compute_weekly_stats(weekly_rankings)
        
        all_avg_diffs.append(diff)
        all_max_diffs.append(mx)
        all_biggest_rise.append(rise)
        all_biggest_fall.append(fall)
        all_avg_diffs25.append(diff25)
        all_max_diffs25.append(mx25)
    
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
        sum_avg25 = sum(run[w] for run in all_avg_diffs25)
        sum_max25 = sum(run[w] for run in all_max_diffs25)
        
        avg_avg_diff[w] = sum_avg_d / num_runs
        avg_max_diff[w] = sum_max_d / num_runs
        avg_rise[w] = sum_rise / num_runs
        avg_fall[w] = sum_fall / num_runs
        avg_avg_diff25[w] = sum_avg25 / num_runs
        avg_max_diff25[w] = sum_max25 / num_runs
    
    return (avg_avg_diff, avg_max_diff,
            avg_rise, avg_fall,
            avg_avg_diff25, avg_max_diff25)

# =========================
# 9) Plot Aggregated Stats
# =========================
def plot_aggregated_stats(avg_avg_diff, avg_max_diff,
                          avg_biggest_rise, avg_biggest_fall,
                          avg_avg_diff25, avg_max_diff25,
                          num_runs):
    """
    Takes six lists (each length = num_weeks+1):
       1) average diff (all teams)
       2) max diff (all teams)
       3) biggest rise
       4) biggest fall
       5) average diff among top 25
       6) max diff among top 25
    and plots them in six separate line plots, weeks on x-axis.
    
    'num_runs' is used to clarify the title: "Averaged Over X Runs".
    """
    weeks_count = len(avg_avg_diff)
    x_vals = list(range(weeks_count))
    x_labels = [f"W{w}" for w in x_vals]

    # 1) Average Discrepancy
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_avg_diff, marker='o', label='Avg Discrepancy (All)')
    plt.title(f"Average |CFP Rank - True Rank| (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Average Discrepancy (All 134 Teams)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
    
    # 2) Maximum Discrepancy
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_max_diff, marker='o', color='red', label='Max Discrepancy (All)')
    plt.title(f"Maximum |CFP Rank - True Rank| (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Maximum Discrepancy (All 134 Teams)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.ylim(bottom=0)
    plt.show()
    
    # 3) Biggest Rise
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_biggest_rise, marker='o', color='green', label='Biggest Rise')
    plt.title(f"Biggest Rise in Rank (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Number of Spots Gained")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()
    
    # 4) Biggest Fall
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_biggest_fall, marker='o', color='orange', label='Biggest Fall')
    plt.title(f"Biggest Fall in Rank (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Number of Spots Dropped")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 5) Average Discrepancy in Top 25
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_avg_diff25, marker='o', label='Avg Diff (Top 25)')
    plt.title(f"Average |CFP Rank - True Rank| in Top 25 (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Average Discrepancy (Top 25)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 6) Maximum Discrepancy in Top 25
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_max_diff25, marker='o', color='purple', label='Max Diff (Top 25)')
    plt.title(f"Maximum |CFP Rank - True Rank| in Top 25 (Averaged Over {num_runs} Runs)")
    plt.xlabel("Week")
    plt.ylabel("Maximum Discrepancy (Top 25)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.ylim(bottom=0)
    plt.show()

# =========================
# 10) Main
# =========================
def main():
    num_runs = 100
    num_teams = 134
    num_weeks = 12
    
    print(f"Running {num_runs} simulations of {num_teams} teams for {num_weeks} weeks each...")

    (avg_avg_diff, avg_max_diff,
     avg_rise, avg_fall,
     avg_avg_diff25, avg_max_diff25) = run_multiple_simulations(
         num_runs=num_runs,
         num_teams=num_teams,
         num_weeks=num_weeks
    )

    # Print out the weekly data points
    print(f"\n=== Weekly Averages Over {num_runs} Runs ===")
    print(f"{'Week':<4} | {'AvgDiff':>8} | {'MaxDiff':>8} | {'MaxRise':>8} | {'MaxFall':>8} | {'AvgDiff25':>10} | {'MaxDiff25':>10}")
    print("-"*72)
    weeks_count = num_weeks + 1
    
    for w in range(weeks_count):
        print(f"{w:<4d} | "
              f"{avg_avg_diff[w]:8.2f} | "
              f"{avg_max_diff[w]:8.2f} | "
              f"{avg_rise[w]:8.2f} | "
              f"{avg_fall[w]:8.2f} | "
              f"{avg_avg_diff25[w]:10.2f} | "
              f"{avg_max_diff25[w]:10.2f}")

    # Now plot
    plot_aggregated_stats(avg_avg_diff, avg_max_diff,
                          avg_rise, avg_fall,
                          avg_avg_diff25, avg_max_diff25,
                          num_runs)

if __name__ == "__main__":
    main()