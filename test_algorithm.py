#!/usr/bin/env python3
"""
Test the actual auto balance algorithm
"""

def test_auto_balance():
    # Simulate your exact scenario
    groups = {
        'Group A': {
            'total_skill': 56, 
            'players': [
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 6, 'gender': 'F'}
            ]
        },
        'Group F': {
            'total_skill': 53, 
            'players': [
                {'skill_level': 5, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 5, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 5, 'gender': 'M'},
                {'skill_level': 6, 'gender': 'F'},
                {'skill_level': 5, 'gender': 'M'},
                {'skill_level': 5, 'gender': 'F'},
                {'skill_level': 6, 'gender': 'M'},
                {'skill_level': 6, 'gender': 'F'}
            ]
        }
    }
    
    print("Before balancing:")
    print(f"Group A: {groups['Group A']['total_skill']} points")
    print(f"Group F: {groups['Group F']['total_skill']} points")
    print(f"Difference: {groups['Group A']['total_skill'] - groups['Group F']['total_skill']}")
    
    # Simple balancing: find a player in Group A to swap with Group F
    # that reduces the difference
    group_keys = ['Group A', 'Group F']
    
    for attempt in range(100):
        current_skills = [groups[key]['total_skill'] for key in group_keys]
        max_skill = max(current_skills)
        min_skill = min(current_skills)
        
        if max_skill - min_skill <= 1:
            print("\\n✅ Balanced!")
            break
            
        max_idx = current_skills.index(max_skill)
        min_idx = current_skills.index(min_skill)
        
        max_group = groups[group_keys[max_idx]]
        min_group = groups[group_keys[min_idx]]
        
        best_swap = None
        best_new_diff = max_skill - min_skill
        
        for i, max_player in enumerate(max_group['players']):
            for j, min_player in enumerate(min_group['players']):
                if max_player['gender'] == min_player['gender']:
                    new_max_skill = max_skill - max_player['skill_level'] + min_player['skill_level']
                    new_min_skill = min_skill - min_player['skill_level'] + max_player['skill_level']
                    new_diff = abs(new_max_skill - new_min_skill)
                    
                    if new_diff < best_new_diff:
                        best_new_diff = new_diff
                        best_swap = (i, j, max_player, min_player, new_max_skill, new_min_skill)
        
        if best_swap:
            i, j, max_player, min_player, new_max_skill, new_min_skill = best_swap
            print(f"\\nSwapping {max_player['skill_level']}{max_player['gender']} with {min_player['skill_level']}{min_player['gender']}")
            
            max_group['players'][i] = min_player
            min_group['players'][j] = max_player
            max_group['total_skill'] = new_max_skill
            min_group['total_skill'] = new_min_skill
            
            print(f"Group A: {groups['Group A']['total_skill']} points")
            print(f"Group F: {groups['Group F']['total_skill']} points")
            print(f"Difference: {abs(groups['Group A']['total_skill'] - groups['Group F']['total_skill'])}")
        else:
            print("\\n❌ No beneficial swap found!")
            break
    
    print("\\nFinal state:")
    print(f"Group A: {groups['Group A']['total_skill']} points")
    print(f"Group F: {groups['Group F']['total_skill']} points")
    print(f"Difference: {abs(groups['Group A']['total_skill'] - groups['Group F']['total_skill'])}")

if __name__ == "__main__":
    test_auto_balance()