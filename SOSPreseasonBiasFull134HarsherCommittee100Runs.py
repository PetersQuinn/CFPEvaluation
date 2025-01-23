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
#  2) Generate Teams (true ranks)
# =========================
def generate_teams(num_teams=DEFAULT_NUM_TEAMS):
    """
    Each team: {
      'name': e.g. "Team #1", ..., "Team #134",
      'true_rank': 1..134 (1=best),
      'cfp_rank': 1..134 (1=top in CFP),
      'season_points': 0
    }
    We'll assign 'true_rank' straightforwardly: 1..134.
    The actual tier-based preseason cfp_rank assignment
    is done after this in 'assign_preseason_tiers()'.
    """
    teams = []
    for i in range(1, num_teams + 1):
        # i=1 => best, i=134 => worst
        team_dict = {
            'name': f"Team #{i}",
            'true_rank': i,
            # We'll fill cfp_rank below, in a tier-based random approach
            'cfp_rank': None,
            'season_points': 0
        }
        teams.append(team_dict)
    return teams

# =========================
#  2b) Assign Preseason Tiers
# =========================
def assign_preseason_tiers(teams):
    """
    3-tier preseason ranking approach:
      Tier 1: true_rank 1..34   (top 34)
      Tier 2: true_rank 35..84  (next 50)
      Tier 3: true_rank 85..134 (last 50)

    We'll shuffle each tier internally and then place them in
    cfp_rank order (1..134), i.e., a random arrangement within each tier,
    but Tier1 teams occupy cfp_ranks ~1..34, Tier2 occupy ~35..84, Tier3 ~85..134.
    """
    # 1) Sort teams by true_rank
    sorted_by_true = sorted(teams, key=lambda t: t['true_rank'])
    # tiers:
    tier1 = sorted_by_true[:34]   # top 34
    tier2 = sorted_by_true[34:84] # next 50
    tier3 = sorted_by_true[84:]   # last 50

    # 2) Shuffle within each tier
    random.shuffle(tier1)
    random.shuffle(tier2)
    random.shuffle(tier3)

    # 3) Concatenate them back as [tier1 + tier2 + tier3]
    preseason_list = tier1 + tier2 + tier3
    # Now, tier1 teams get cfp_rank=1..34, tier2=35..84, tier3=85..134
    for i, team in enumerate(preseason_list):
        team['cfp_rank'] = i + 1  # i=0 => cfp_rank=1

    # Return a list sorted by cfp_rank
    return sorted(preseason_list, key=lambda t: t['cfp_rank'])

# =========================
#  3) Probability of Win
# =========================
def probability_of_win(team_a_true, team_b_true):
    """
    FBS-like logic:
      Let diff = (team_b_true - team_a_true).
      If diff>0 => team_a is better => base_prob
      If diff<0 => team_a is worse => 1 - base_prob

      Bins (abs_diff):
       <=5 => 50/50
       6-10 => 65/35
       11-15 => 75/25
       16-25 => 85/15
       26-50 => 95/5
       51-100 => 98/2
       >100 => 99/1
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
    The existing 'standard' or 'harsh' logic:
      - 5 pts: Win vs. stronger or up to 7 below
      - 4 pts: Win vs. 8–24 below
      - 3 pts: Win vs. 25+ below OR lose to stronger
      - 2 pts: Lose to 1–7 below
      - 1 pts: Lose to 8–24 below
      - 0 pts: Lose to 25+ below
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
    Sort by season_points desc; if tie, preserve last week's order
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

    Now uses tier-based random initial ranking:
      1) Generate teams by true rank
      2) Assign them a tier-based preseason cfp_rank
      3) Then proceed as usual
    """
    if seed is not None:
        random.seed(seed)
    else:
        random.seed()

    # 1) Create teams with true_rank
    teams = generate_teams(num_teams)

    # 2) Assign cfp_rank based on 3-tier approach
    #    randomizing within each tier
    current_cfp_order = assign_preseason_tiers(teams)

    # 3) Keep a snapshot of Week0
    weekly_rankings = [copy.deepcopy(current_cfp_order)]

    for w in range(1, num_weeks + 1):
        indices = list(range(num_teams))
        random.shuffle(indices)
        matchups = [(indices[i], indices[i+1]) for i in range(0, num_teams, 2)]
        
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
        
        teams_sorted = sorted(teams, key=lambda t: t['season_points'], reverse=True)
        new_cfp_order = break_ties(teams_sorted, current_cfp_order)
        
        for rank_pos, tdict in enumerate(new_cfp_order):
            tdict['cfp_rank'] = rank_pos + 1
        
        weekly_rankings.append(copy.deepcopy(new_cfp_order))
        current_cfp_order = new_cfp_order

    return weekly_rankings

# =========================
#  7) Tier-based Preseason
# =========================
def assign_preseason_tiers(teams):
    """
    3-tier approach to the initial preseason cfp_rank:
      Tier 1: top 34 in true_rank
      Tier 2: next 50
      Tier 3: last 50
    We'll randomize within each tier, then assign cfp_rank=1..134
    """
    # Sort by true_rank ascending
    sorted_by_true = sorted(teams, key=lambda t: t['true_rank'])
    tier1 = sorted_by_true[:34]
    tier2 = sorted_by_true[34:84]  # 50 teams
    tier3 = sorted_by_true[84:]    # 50 teams

    random.shuffle(tier1)
    random.shuffle(tier2)
    random.shuffle(tier3)

    # Combine
    combined = tier1 + tier2 + tier3
    for i, tm in enumerate(combined):
        tm['cfp_rank'] = i + 1
    # Return them sorted by cfp_rank
    return sorted(combined, key=lambda t: t['cfp_rank'])

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
    
    week_to_map = []
    for w, snapshot in enumerate(weekly_rankings):
        d = {team['name']: team['cfp_rank'] for team in snapshot}
        week_to_map.append(d)
        
        # all teams
        diffs = [abs(team['cfp_rank'] - team['true_rank']) for team in snapshot]
        avg_diff[w] = sum(diffs)/len(diffs)
        max_diff[w] = max(diffs)

        # top25
        top_25 = snapshot[:25]
        diffs25 = [abs(t['cfp_rank'] - t['true_rank']) for t in top_25]
        avg_diff25[w] = sum(diffs25)/len(diffs25)
        max_diff25[w] = max(diffs25)
    
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

    Returns a tuple of:
      avg_avg_diff, avg_max_diff, avg_rise, avg_fall,
      avg_avg_diff25, avg_max_diff25
      (each a list of length num_weeks+1)
    """
    all_avg_diff = []
    all_max_diff = []
    all_rise = []
    all_fall = []
    all_avg25 = []
    all_max25 = []
    
    for _ in range(num_runs):
        weekly_rankings = simulate_single_season(num_teams, num_weeks, seed=None)
        (ad, mx, rise, fall, ad25, mx25) = compute_weekly_stats(weekly_rankings)
        
        all_avg_diff.append(ad)
        all_max_diff.append(mx)
        all_rise.append(rise)
        all_fall.append(fall)
        all_avg25.append(ad25)
        all_max25.append(mx25)
    
    weeks_count = num_weeks + 1
    avg_avg_diff = [0]*weeks_count
    avg_max_diff = [0]*weeks_count
    avg_biggest_rise = [0]*weeks_count
    avg_biggest_fall = [0]*weeks_count
    avg_avg_diff25 = [0]*weeks_count
    avg_max_diff25 = [0]*weeks_count
    
    for w in range(weeks_count):
        sum_ad = sum(run[w] for run in all_avg_diff)
        sum_mx = sum(run[w] for run in all_max_diff)
        sum_rise = sum(run[w] for run in all_rise)
        sum_fall = sum(run[w] for run in all_fall)
        sum_ad25 = sum(run[w] for run in all_avg25)
        sum_mx25 = sum(run[w] for run in all_max25)

        avg_avg_diff[w]    = sum_ad / num_runs
        avg_max_diff[w]    = sum_mx / num_runs
        avg_biggest_rise[w]= sum_rise / num_runs
        avg_biggest_fall[w]= sum_fall / num_runs
        avg_avg_diff25[w]  = sum_ad25 / num_runs
        avg_max_diff25[w]  = sum_mx25 / num_runs
    
    return (avg_avg_diff, avg_max_diff,
            avg_biggest_rise, avg_biggest_fall,
            avg_avg_diff25, avg_max_diff25)

# =========================
# 9) Single-Run Chart with Tier Colors
# =========================
def single_run_tier_chart(num_teams=DEFAULT_NUM_TEAMS, num_weeks=DEFAULT_NUM_WEEKS, seed=1234):
    """
    Run a single season once, using the new tier-based
    preseason approach, then color each team's line
    by its original tier:

    Tier 1 (true_rank <= 34) => red
    Tier 2 (35..84) => orange
    Tier 3 (85..134) => blue

    We'll label the chart "Committee Viewpoint: Tiered Colors".
    """
    # 1) run a single season
    weekly_rankings = simulate_single_season(num_teams, num_weeks, seed)

    # 2) build data
    # For tier-based color, we rely on the team's *true_rank*:
    #   if true_rank <= 34 => red
    #   if 35..84 => orange
    #   if 85..134 => blue
    name_to_true = {}
    name_to_ranks = {}

    for w, snapshot in enumerate(weekly_rankings):
        for team in snapshot:
            nm = team['name']
            if nm not in name_to_ranks:
                name_to_ranks[nm] = []
                name_to_true[nm] = team['true_rank']
            name_to_ranks[nm].append(team['cfp_rank'])

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10,6))
    weeks_x = range(len(weekly_rankings))

    for nm in sorted(name_to_ranks.keys(), key=lambda n: name_to_true[n]):
        ranks_list = name_to_ranks[nm]
        t = name_to_true[nm]
        if t <= 34:
            c = 'red'
        elif t <= 84:
            c = 'orange'
        else:
            c = 'blue'
        ax.plot(weeks_x, ranks_list, marker='o', color=c, linewidth=1)

    ax.invert_yaxis()
    ax.set_xlabel("Week")
    ax.set_ylabel("CFP Rank (1 is best)")
    ax.set_title("Committee Viewpoint: Tiered Colors (Single Run)")
    ax.set_xticks(list(weeks_x))
    ax.set_xticklabels([f"W{w}" for w in weeks_x])
    plt.tight_layout()
    plt.show()

# =========================
# 9) Plot Aggregated Stats
# =========================
def plot_aggregated_stats(avg_avg_diff, avg_max_diff,
                          avg_biggest_rise, avg_biggest_fall,
                          avg_avg_diff25, avg_max_diff25,
                          num_runs):
    """
    Takes six lists:
      1) avg_avg_diff
      2) avg_max_diff
      3) avg_biggest_rise
      4) avg_biggest_fall
      5) avg_avg_diff25
      6) avg_max_diff25
    each is length num_weeks+1
    """
    weeks_count = len(avg_avg_diff)
    x_vals = range(weeks_count)
    x_labels = [f"W{w}" for w in x_vals]

    # 1) Average Diff (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_avg_diff, marker='o', label='Avg Diff (All)')
    plt.title(f"Average |CFP - True| (Over {num_runs} Runs) - Committee View")
    plt.xlabel("Week")
    plt.ylabel("Average Discrepancy (All)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 2) Max Diff (All)
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_max_diff, marker='o', color='red', label='Max Diff (All)')
    plt.title(f"Maximum |CFP - True| (Over {num_runs} Runs) - Committee View")
    plt.xlabel("Week")
    plt.ylabel("Maximum Discrepancy (All)")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.ylim(bottom=0)
    plt.tight_layout()
    plt.show()

    # 3) Biggest Rise
    plt.figure(figsize=(8,5))
    plt.plot(x_vals, avg_biggest_rise, marker='o', color='green', label='Biggest Rise')
    plt.title(f"Biggest Rise in Rank (All) (Over {num_runs} Runs) - Committee View")
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
    plt.title(f"Biggest Fall in Rank (All) (Over {num_runs} Runs) - Committee View")
    plt.xlabel("Week")
    plt.ylabel("Number of Spots Dropped")
    plt.xticks(x_vals, x_labels)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 5) Average Diff (Top 25)
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

    # 6) Max Diff (Top 25)
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
    # 1) Single run with a Tier-based color chart
    single_run_tier_chart(num_teams=134, num_weeks=12, seed=42)

    # 2) Then do the 100-run aggregator
    num_runs = 100
    num_teams = 134
    num_weeks = 12
    print(f"Running {num_runs} simulations (Tier-based Preseason) with {num_teams} teams for {num_weeks} weeks each...")

    (avg_avg_diff, avg_max_diff,
     avg_rise, avg_fall,
     avg_avg_diff25, avg_max_diff25) = run_multiple_simulations(
         num_runs=num_runs,
         num_teams=num_teams,
         num_weeks=num_weeks
    )

    print("\n=== Weekly Averages Over 100 Runs (Tier-based) ===")
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

    # 3) Plot aggregator results
    plot_aggregated_stats(avg_avg_diff, avg_max_diff,
                          avg_rise, avg_fall,
                          avg_avg_diff25, avg_max_diff25,
                          num_runs)

if __name__ == "__main__":
    main()
