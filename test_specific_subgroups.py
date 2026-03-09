#!/usr/bin/env python3

import json
import pandas as pd

def test_specific_subgroups():
    """Test Skill-Level Subgroups with your exact requirements"""
    
    # Load tournament data
    with open('tournament_players.json', 'r') as f:
        players = json.load(f)
    
    df = pd.DataFrame(players)
    print(f"Loaded {len(df)} players")
    print(f"Gender distribution: {df['gender'].value_counts().to_dict()}")
    print(f"Skill level distribution: {sorted(df['skill_level'].value_counts().items())}")
    
    # Your exact requirements
    subgroup1_min = 1  # Skill range 1-5
    subgroup1_max = 5
    subgroup2_min = 6  # Skill range 6-10
    subgroup2_max = 10
    num_groups = 6
    players_per_group = 10
    females_per_group = 1
    
    print(f"\nYour Requirements:")
    print(f"- {num_groups} groups of {players_per_group} players each")
    print(f"- Subgroup 1: skill {subgroup1_min}-{subgroup1_max}")
    print(f"- Subgroup 2: skill {subgroup2_min}-{subgroup2_max}")
    print(f"- Exactly {females_per_group} female per group")
    
    # Analyze available players
    subgroup1_players = df[(df['skill_level'] >= subgroup1_min) & (df['skill_level'] <= subgroup1_max)]
    subgroup2_players = df[(df['skill_level'] >= subgroup2_min) & (df['skill_level'] <= subgroup2_max)]
    
    sg1_available = len(subgroup1_players)
    sg2_available = len(subgroup2_players)
    total_needed = num_groups * players_per_group
    
    print(f"\nPlayer Availability:")
    print(f"Subgroup 1 (1-5): {sg1_available} available")
    print(f"Subgroup 2 (6-10): {sg2_available} available")
    print(f"Total needed: {total_needed}")
    print(f"Total available: {sg1_available + sg2_available}")
    
    # Calculate subgroup distribution per group
    if sg1_available + sg2_available != total_needed:
        print(f"❌ Player count mismatch!")
        return False
    
    # Determine players per group from each subgroup
    subgroup1_count = sg1_available // num_groups
    subgroup2_count = sg2_available // num_groups
    sg1_remainder = sg1_available % num_groups
    sg2_remainder = sg2_available % num_groups
    
    print(f"\nCalculated Distribution Per Group:")
    print(f"Subgroup 1: {subgroup1_count} players (with {sg1_remainder} groups getting +1)")
    print(f"Subgroup 2: {subgroup2_count} players (with {sg2_remainder} groups getting +1)")
    print(f"Total per group: {subgroup1_count + subgroup2_count} (+{1 if sg1_remainder > 0 or sg2_remainder > 0 else 0} for some groups)")
    
    # Check gender constraints
    total_females = len(df[df['gender'] == 'F'])
    needed_females = num_groups * females_per_group
    
    print(f"\nGender Analysis:")
    print(f"Total females available: {total_females}")
    print(f"Females needed: {needed_females}")
    
    if total_females != needed_females:
        print(f"❌ Gender mismatch! Need exactly {needed_females}, have {total_females}")
        return False
    
    print("✅ All requirements can be met!")
    
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
    
    # Get best players from each subgroup
    subgroup1_selected = subgroup1_players.nlargest(sg1_available, 'skill_level').reset_index(drop=True)
    subgroup2_selected = subgroup2_players.nlargest(sg2_available, 'skill_level').reset_index(drop=True)
    
    print(f"\nSelected Players:")
    print(f"Subgroup 1 skills: {sorted(subgroup1_selected['skill_level'].tolist(), reverse=True)}")
    print(f"Subgroup 2 skills: {sorted(subgroup2_selected['skill_level'].tolist(), reverse=True)}")
    
    # Distribute subgroup 1 players with gender constraints
    def distribute_with_gender_constraint(players_df, subgroup_type, base_count_per_group, extra_count):
        """Distribute players ensuring exactly 1 female per group"""
        
        # Separate by gender
        male_players = players_df[players_df['gender'] == 'M'].sort_values('skill_level', ascending=False).reset_index(drop=True)
        female_players = players_df[players_df['gender'] == 'F'].sort_values('skill_level', ascending=False).reset_index(drop=True)
        
        print(f"\n  Distributing {subgroup_type}:")
        print(f"  Males: {len(male_players)}, Females: {len(female_players)}")
        
        # First distribute females (exactly 1 per group, or 0 if no females in this subgroup)
        female_idx = 0
        female_records = female_players.to_dict('records')
        
        # Distribute females first
        for group_idx in range(num_groups):
            if female_idx < len(female_records):
                group_name = group_keys[group_idx]
                player = female_records[female_idx]
                groups[group_name][subgroup_type]['players'].append(player)
                groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
                female_idx += 1
                print(f"    {group_name}: Added female {player['name']} (skill {player['skill_level']})")
        
        # Then distribute males to fill remaining spots
        male_records = male_players.to_dict('records')
        male_idx = 0
        
        # Calculate how many males each group needs
        for group_idx in range(num_groups):
            group_name = group_keys[group_idx]
            current_count = len(groups[group_name][subgroup_type]['players'])
            
            # Determine target count for this group
            target_count = base_count_per_group
            if group_idx < extra_count:  # First few groups get +1 if there are remainders
                target_count += 1
            
            males_needed = target_count - current_count
            
            # Add males to this group
            for _ in range(males_needed):
                if male_idx < len(male_records):
                    player = male_records[male_idx]
                    groups[group_name][subgroup_type]['players'].append(player)
                    groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
                    male_idx += 1
            
            print(f"    {group_name}: {current_count + males_needed} total players ({males_needed} males + {current_count} females)")
    
    # Distribute both subgroups
    distribute_with_gender_constraint(subgroup1_selected, 'subgroup1', subgroup1_count, sg1_remainder)
    distribute_with_gender_constraint(subgroup2_selected, 'subgroup2', subgroup2_count, sg2_remainder)
    
    # Apply balance algorithm to both subgroups
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
                print(f"    Swapped {max_player['name']} ↔ {min_player['name']} (skill diff: {skill_diff})")
            else:
                print(f"  ❌ No beneficial swap found for {subgroup_type} - stopping")
                break
        
        # Show final state
        final_totals = [groups[key][subgroup_type]['total_skill'] for key in group_keys]
        print(f"  Final totals: {final_totals}")
        print(f"  Final range: {min(final_totals)}-{max(final_totals)} (diff: {max(final_totals) - min(final_totals)})")
        
        return max(final_totals) - min(final_totals) <= 1
    
    # Balance both subgroups
    sg1_balanced = balance_subgroup('subgroup1')
    sg2_balanced = balance_subgroup('subgroup2')
    
    # Add final overall balancing step
    def balance_overall_groups():
        """Balance the combined totals of subgroup1 + subgroup2"""
        print(f"\nBalancing overall group totals...")
        
        for iteration in range(100):
            # Calculate combined totals
            combined_totals = []
            for key in group_keys:
                sg1_total = groups[key]['subgroup1']['total_skill']
                sg2_total = groups[key]['subgroup2']['total_skill']
                combined_totals.append(sg1_total + sg2_total)
            
            max_total = max(combined_totals)
            min_total = min(combined_totals)
            
            print(f"  Iteration {iteration + 1}: Range {min_total}-{max_total} (diff: {max_total - min_total})")
            
            # If balanced within 1 point, we're done
            if max_total - min_total <= 1:
                print(f"  ✅ Overall groups balanced in {iteration + 1} iterations!")
                return True
            
            # Find highest and lowest groups
            max_idx = combined_totals.index(max_total)
            min_idx = combined_totals.index(min_total)
            
            # Try swapping between subgroups of these groups
            best_swap = None
            best_improvement = 0
            
            # Try swaps within subgroup1
            max_sg1 = groups[group_keys[max_idx]]['subgroup1']
            min_sg1 = groups[group_keys[min_idx]]['subgroup1']
            
            for i, max_player in enumerate(max_sg1['players']):
                for j, min_player in enumerate(min_sg1['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup1', i, j, max_player, min_player, skill_diff)
            
            # Try swaps within subgroup2
            max_sg2 = groups[group_keys[max_idx]]['subgroup2']
            min_sg2 = groups[group_keys[min_idx]]['subgroup2']
            
            for i, max_player in enumerate(max_sg2['players']):
                for j, min_player in enumerate(min_sg2['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup2', i, j, max_player, min_player, skill_diff)
            
            # Execute the best swap
            if best_swap:
                subgroup_type, i, j, max_player, min_player, skill_diff = best_swap
                
                max_subgroup = groups[group_keys[max_idx]][subgroup_type]
                min_subgroup = groups[group_keys[min_idx]][subgroup_type]
                
                # Swap players
                max_subgroup['players'][i] = min_player
                min_subgroup['players'][j] = max_player
                # Update totals
                max_subgroup['total_skill'] -= skill_diff
                min_subgroup['total_skill'] += skill_diff
                
                print(f"    Swapped {max_player['name']} ↔ {min_player['name']} in {subgroup_type} (skill diff: {skill_diff})")
            else:
                print(f"  ❌ No beneficial swap found for overall balance - stopping")
                break
        
        # Check final state
        final_combined_totals = []
        for key in group_keys:
            sg1_total = groups[key]['subgroup1']['total_skill']
            sg2_total = groups[key]['subgroup2']['total_skill']
            final_combined_totals.append(sg1_total + sg2_total)
        
        final_diff = max(final_combined_totals) - min(final_combined_totals)
        print(f"  Final combined range: {min(final_combined_totals)}-{max(final_combined_totals)} (diff: {final_diff})")
        
        return final_diff <= 1
    
    # Apply final overall balancing
    overall_balanced = balance_overall_groups()
    
    # Final analysis
    print(f"\n=== FINAL ANALYSIS ===")
    
    overall_totals = []
    for group_name in group_keys:
        sg1_total = groups[group_name]['subgroup1']['total_skill']
        sg2_total = groups[group_name]['subgroup2']['total_skill']
        overall_total = sg1_total + sg2_total
        overall_totals.append(overall_total)
        
        sg1_count = len(groups[group_name]['subgroup1']['players'])
        sg2_count = len(groups[group_name]['subgroup2']['players'])
        total_count = sg1_count + sg2_count
        
        # Count genders
        all_players = groups[group_name]['subgroup1']['players'] + groups[group_name]['subgroup2']['players']
        female_count = len([p for p in all_players if p['gender'] == 'F'])
        male_count = len([p for p in all_players if p['gender'] == 'M'])
        
        print(f"{group_name}: SG1={sg1_total}pts({sg1_count}p) + SG2={sg2_total}pts({sg2_count}p) = {overall_total}pts({total_count}p) [{male_count}M,{female_count}F]")
    
    # Check all balance requirements
    sg1_totals = [groups[key]['subgroup1']['total_skill'] for key in group_keys]
    sg2_totals = [groups[key]['subgroup2']['total_skill'] for key in group_keys]
    
    sg1_diff = max(sg1_totals) - min(sg1_totals)
    sg2_diff = max(sg2_totals) - min(sg2_totals)
    overall_diff = max(overall_totals) - min(overall_totals)
    
    sg1_ok = sg1_diff <= 1
    sg2_ok = sg2_diff <= 1
    overall_ok = overall_diff <= 1
    
    print(f"\nBalance Results:")
    print(f"Subgroup 1 (1-5): {min(sg1_totals)}-{max(sg1_totals)} (diff: {sg1_diff}) {'✅' if sg1_ok else '❌'}")
    print(f"Subgroup 2 (6-10): {min(sg2_totals)}-{max(sg2_totals)} (diff: {sg2_diff}) {'✅' if sg2_ok else '❌'}")
    print(f"Overall groups: {min(overall_totals)}-{max(overall_totals)} (diff: {overall_diff}) {'✅' if overall_ok else '❌'}")
    
    # Check gender constraint
    gender_ok = True
    for group_name in group_keys:
        all_players = groups[group_name]['subgroup1']['players'] + groups[group_name]['subgroup2']['players']
        female_count = len([p for p in all_players if p['gender'] == 'F'])
        if female_count != females_per_group:
            gender_ok = False
            break
    
    print(f"Gender constraint (1F/group): {'✅' if gender_ok else '❌'}")
    
    print(f"\n=== TEST SUMMARY ===")
    all_success = sg1_ok and sg2_ok and overall_balanced and gender_ok
    print(f"All requirements met: {'✅ PASSED' if all_success else '❌ FAILED'}")
    
    return all_success

if __name__ == "__main__":
    success = test_specific_subgroups()
    print(f"\nSpecific subgroups test: {'✅ SUCCESS' if success else '❌ FAILURE'}")