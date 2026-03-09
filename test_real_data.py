#!/usr/bin/env python3

import json
import pandas as pd
from collections import defaultdict

def load_tournament_data():
    """Load the actual tournament player data"""
    with open('tournament_players.json', 'r') as f:
        players = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(players)
    print(f"Loaded {len(df)} players")
    print(f"Gender distribution: {df['gender'].value_counts().to_dict()}")
    print(f"Skill level range: {df['skill_level'].min()} - {df['skill_level'].max()}")
    
    return df

def analyze_current_groups(df):
    """Analyze current group balance"""
    print("\n=== CURRENT GROUP BALANCE ===")
    
    group_stats = []
    for group in sorted(df['group'].unique()):
        group_players = df[df['group'] == group]
        total_skill = group_players['skill_level'].sum()
        female_count = len(group_players[group_players['gender'] == 'F'])
        male_count = len(group_players[group_players['gender'] == 'M'])
        
        group_stats.append({
            'group': group,
            'total_skill': total_skill,
            'players': len(group_players),
            'females': female_count,
            'males': male_count
        })
        
        print(f"{group}: {total_skill} pts ({len(group_players)} players: {male_count}M, {female_count}F)")
    
    # Calculate balance metrics
    skills = [g['total_skill'] for g in group_stats]
    max_skill = max(skills)
    min_skill = min(skills)
    skill_diff = max_skill - min_skill
    
    print(f"\nBalance Analysis:")
    print(f"Max skill: {max_skill}, Min skill: {min_skill}")
    print(f"Skill difference: {skill_diff} points")
    print(f"Is balanced (≤1 pt): {'✅' if skill_diff <= 1 else '❌'}")
    
    return group_stats

def test_balance_algorithm(df):
    """Test the balance algorithm from badminton.py"""
    
    # Create initial groups structure (convert current assignments to the format expected)
    groups = {}
    group_keys = []
    
    for group_name in sorted(df['group'].unique()):
        group_players = df[df['group'] == group_name]
        players_list = []
        
        for _, player in group_players.iterrows():
            players_list.append({
                'name': player['name'],
                'gender': player['gender'],
                'email': player['email'],
                'skill_level': player['skill_level']
            })
        
        groups[group_name] = {
            'players': players_list,
            'total_skill': group_players['skill_level'].sum()
        }
        group_keys.append(group_name)
    
    print(f"\n=== TESTING BALANCE ALGORITHM ===")
    print(f"Groups before balance:")
    for key in group_keys:
        print(f"  {key}: {groups[key]['total_skill']} pts ({len(groups[key]['players'])} players)")
    
    # Apply the simple balance algorithm (copied from the fixed code)
    def redistribute_for_perfect_balance():
        """Simple algorithm to achieve exactly 1-point max difference"""
        for iteration in range(100):  # Limit iterations
            # Get current group totals
            totals = [groups[key]['total_skill'] for key in group_keys]
            max_total = max(totals)
            min_total = min(totals)
            
            print(f"  Iteration {iteration + 1}: Range {min_total}-{max_total} (diff: {max_total - min_total})")
            
            # If balanced within 1 point, we're done
            if max_total - min_total <= 1:
                print(f"  ✅ Balanced achieved in {iteration + 1} iterations!")
                break
            
            # Find highest and lowest groups
            max_idx = totals.index(max_total)
            min_idx = totals.index(min_total)
            
            max_group = groups[group_keys[max_idx]]
            min_group = groups[group_keys[min_idx]]
            
            print(f"  Trying to balance {group_keys[max_idx]} ({max_total}) → {group_keys[min_idx]} ({min_total})")
            
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
                print(f"    Swapping {max_player['name']} (skill {max_player['skill_level']}) ↔ {min_player['name']} (skill {min_player['skill_level']})")
                
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                print(f"  ❌ No beneficial swap found - stopping")
                break
    
    # Run the balance algorithm
    redistribute_for_perfect_balance()
    
    print(f"\n=== FINAL RESULTS ===")
    final_totals = []
    for key in group_keys:
        total = groups[key]['total_skill']
        final_totals.append(total)
        females = len([p for p in groups[key]['players'] if p['gender'] == 'F'])
        males = len([p for p in groups[key]['players'] if p['gender'] == 'M'])
        print(f"{key}: {total} pts ({len(groups[key]['players'])} players: {males}M, {females}F)")
    
    # Final balance analysis
    max_final = max(final_totals)
    min_final = min(final_totals)
    final_diff = max_final - min_final
    
    print(f"\nFinal Balance Analysis:")
    print(f"Max skill: {max_final}, Min skill: {min_final}")
    print(f"Skill difference: {final_diff} points")
    print(f"Is balanced (≤1 pt): {'✅' if final_diff <= 1 else '❌'}")
    
    return final_diff <= 1

if __name__ == "__main__":
    # Load and analyze current data
    df = load_tournament_data()
    current_stats = analyze_current_groups(df)
    
    # Test balance algorithm
    success = test_balance_algorithm(df)
    
    print(f"\n=== TEST SUMMARY ===")
    print(f"Balance algorithm test: {'✅ PASSED' if success else '❌ FAILED'}")