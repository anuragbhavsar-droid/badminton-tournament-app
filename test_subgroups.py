#!/usr/bin/env python3

import json
import pandas as pd
from collections import defaultdict

def test_subgroups_balance():
    """Test the Skill-Level Subgroups balance algorithm with real tournament data"""
    
    # Load tournament data
    with open('tournament_players.json', 'r') as f:
        players = json.load(f)
    
    df = pd.DataFrame(players)
    print(f"Loaded {len(df)} players")
    print(f"Skill level distribution: {sorted(df['skill_level'].value_counts().items())}")
    
    # Test parameters based on actual skill distribution
    # Skill distribution: [(2, 2), (3, 8), (4, 13), (5, 13), (6, 5), (7, 6), (8, 7), (9, 5), (10, 1)]
    subgroup1_min = 7  # High skill players (7-10): 19 players available
    subgroup1_max = 10
    subgroup2_min = 2  # Lower skill players (2-6): 41 players available  
    subgroup2_max = 6
    subgroup1_count = 3  # 3 high-skill players per group (need 18 total - OK)
    subgroup2_count = 6  # 6 lower-skill players per group (need 36 total - OK)
    num_groups = 6
    
    print(f"\nTesting Subgroup Balance:")
    print(f"Subgroup 1 (High): skill {subgroup1_min}-{subgroup1_max}, {subgroup1_count} per group")
    print(f"Subgroup 2 (Lower): skill {subgroup2_min}-{subgroup2_max}, {subgroup2_count} per group")
    
    # Filter players for each subgroup
    subgroup1_players = df[(df['skill_level'] >= subgroup1_min) & (df['skill_level'] <= subgroup1_max)]
    subgroup2_players = df[(df['skill_level'] >= subgroup2_min) & (df['skill_level'] <= subgroup2_max)]
    
    print(f"\nAvailable players:")
    print(f"Subgroup 1: {len(subgroup1_players)} players (need {subgroup1_count * num_groups})")
    print(f"Subgroup 2: {len(subgroup2_players)} players (need {subgroup2_count * num_groups})")
    
    # Check if we have enough players
    needed_sg1 = subgroup1_count * num_groups
    needed_sg2 = subgroup2_count * num_groups
    
    if len(subgroup1_players) < needed_sg1:
        print(f"❌ Not enough players for Subgroup 1. Need {needed_sg1}, have {len(subgroup1_players)}")
        return False
    if len(subgroup2_players) < needed_sg2:
        print(f"❌ Not enough players for Subgroup 2. Need {needed_sg2}, have {len(subgroup2_players)}")
        return False
    
    # Select best players from each subgroup
    subgroup1_selected = subgroup1_players.nlargest(needed_sg1, 'skill_level').reset_index(drop=True)
    subgroup2_selected = subgroup2_players.nlargest(needed_sg2, 'skill_level').reset_index(drop=True)
    
    print(f"\nSelected players:")
    print(f"Subgroup 1: {len(subgroup1_selected)} players, skills: {sorted(subgroup1_selected['skill_level'].tolist(), reverse=True)}")
    print(f"Subgroup 2: {len(subgroup2_selected)} players, skills: {sorted(subgroup2_selected['skill_level'].tolist(), reverse=True)}")
    
    # Initialize groups structure
    groups = {}
    group_keys = []
    for i in range(num_groups):
        group_name = f"Group {chr(65+i)}"
        groups[group_name] = {
            'subgroup1': {'players': [], 'total_skill': 0},
            'subgroup2': {'players': [], 'total_skill': 0}
        }
        group_keys.append(group_name)
    
    # Simple distribution algorithm for subgroups
    def distribute_subgroup_players(players_df, subgroup_type, target_count_per_group):
        """Distribute players across groups with simple skill balancing"""
        player_records = players_df.sort_values('skill_level', ascending=False).to_dict('records')
        
        # Initial distribution - round robin style
        for i, player in enumerate(player_records):
            group_idx = i % num_groups
            group_name = group_keys[group_idx]
            groups[group_name][subgroup_type]['players'].append(player)
            groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
        
        # Apply balance algorithm
        balance_subgroup(subgroup_type)
    
    def balance_subgroup(subgroup_type):
        """Balance a specific subgroup using the proven algorithm"""
        print(f"\nBalancing {subgroup_type}...")
        
        # Show initial state
        initial_totals = [groups[key][subgroup_type]['total_skill'] for key in group_keys]
        print(f"  Initial totals: {initial_totals}")
        print(f"  Initial range: {min(initial_totals)}-{max(initial_totals)} (diff: {max(initial_totals) - min(initial_totals)})")
        
        for iteration in range(100):
            # Get current group totals
            totals = [groups[key][subgroup_type]['total_skill'] for key in group_keys]
            max_total = max(totals)
            min_total = min(totals)
            
            # If balanced within 1 point, we're done
            if max_total - min_total <= 1:
                print(f"  ✅ {subgroup_type} balanced in {iteration + 1} iterations!")
                break
            
            # Find highest and lowest groups
            max_idx = totals.index(max_total)
            min_idx = totals.index(min_total)
            
            max_group = groups[group_keys[max_idx]][subgroup_type]
            min_group = groups[group_keys[min_idx]][subgroup_type]
            
            # Find best player swap
            best_swap = None
            best_improvement = 0
            
            for i, max_player in enumerate(max_group['players']):
                for j, min_player in enumerate(min_group['players']):
                    # Only swap same gender
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Calculate skill difference
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    
                    # Only swap if it reduces the gap
                    if skill_diff <= 0:
                        continue
                    
                    # Calculate new totals after swap
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    # If this improves balance, consider it
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = (i, j, max_player, min_player, skill_diff)
            
            # Make the best swap
            if best_swap:
                i, j, max_player, min_player, skill_diff = best_swap
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                print(f"  ❌ No beneficial swap found for {subgroup_type} - stopping")
                break
        
        # Show final state
        final_totals = [groups[key][subgroup_type]['total_skill'] for key in group_keys]
        print(f"  Final totals: {final_totals}")
        print(f"  Final range: {min(final_totals)}-{max(final_totals)} (diff: {max(final_totals) - min(final_totals)})")
        
        return max(final_totals) - min(final_totals) <= 1
    
    # Distribute both subgroups
    distribute_subgroup_players(subgroup1_selected, 'subgroup1', subgroup1_count)
    distribute_subgroup_players(subgroup2_selected, 'subgroup2', subgroup2_count)
    
    # Analyze final results
    print(f"\n=== FINAL SUBGROUP ANALYSIS ===")
    
    sg1_balanced = True
    sg2_balanced = True
    overall_balanced = True
    
    for group_name in group_keys:
        sg1_total = groups[group_name]['subgroup1']['total_skill']
        sg2_total = groups[group_name]['subgroup2']['total_skill']
        overall_total = sg1_total + sg2_total
        
        sg1_count = len(groups[group_name]['subgroup1']['players'])
        sg2_count = len(groups[group_name]['subgroup2']['players'])
        
        print(f"{group_name}: SG1={sg1_total}pts ({sg1_count}p), SG2={sg2_total}pts ({sg2_count}p), Total={overall_total}pts")
    
    # Check subgroup 1 balance
    sg1_totals = [groups[key]['subgroup1']['total_skill'] for key in group_keys]
    sg1_diff = max(sg1_totals) - min(sg1_totals)
    sg1_balanced = sg1_diff <= 1
    print(f"\nSubgroup 1 balance: {min(sg1_totals)}-{max(sg1_totals)} (diff: {sg1_diff}) {'✅' if sg1_balanced else '❌'}")
    
    # Check subgroup 2 balance
    sg2_totals = [groups[key]['subgroup2']['total_skill'] for key in group_keys]
    sg2_diff = max(sg2_totals) - min(sg2_totals)
    sg2_balanced = sg2_diff <= 1
    print(f"Subgroup 2 balance: {min(sg2_totals)}-{max(sg2_totals)} (diff: {sg2_diff}) {'✅' if sg2_balanced else '❌'}")
    
    # Check overall balance
    overall_totals = [sg1_totals[i] + sg2_totals[i] for i in range(num_groups)]
    overall_diff = max(overall_totals) - min(overall_totals)
    overall_balanced = overall_diff <= 1
    print(f"Overall balance: {min(overall_totals)}-{max(overall_totals)} (diff: {overall_diff}) {'✅' if overall_balanced else '❌'}")
    
    print(f"\n=== TEST SUMMARY ===")
    all_balanced = sg1_balanced and sg2_balanced and overall_balanced
    print(f"All balances achieved: {'✅ PASSED' if all_balanced else '❌ FAILED'}")
    
    return all_balanced

if __name__ == "__main__":
    success = test_subgroups_balance()
    print(f"\nSubgroups balance test: {'✅ SUCCESS' if success else '❌ FAILURE'}")