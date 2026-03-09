#!/usr/bin/env python3
"""
Simple test to verify the auto balance algorithm logic
"""

def simple_balance_test():
    # Simulate the problem you reported
    groups = {
        'Group A': {'total_skill': 56, 'players': []},
        'Group B': {'total_skill': 56, 'players': []},
        'Group C': {'total_skill': 55, 'players': []},
        'Group D': {'total_skill': 54, 'players': []},
        'Group E': {'total_skill': 54, 'players': []},
        'Group F': {'total_skill': 53, 'players': []}
    }
    
    # Add some dummy players for testing
    for group_name in groups:
        groups[group_name]['players'] = [
            {'skill_level': 5, 'gender': 'M'},
            {'skill_level': 6, 'gender': 'F'},
            {'skill_level': 4, 'gender': 'M'},
            {'skill_level': 7, 'gender': 'F'},
            {'skill_level': 3, 'gender': 'M'},
            {'skill_level': 8, 'gender': 'F'},
            {'skill_level': 5, 'gender': 'M'},
            {'skill_level': 6, 'gender': 'F'},
            {'skill_level': 4, 'gender': 'M'},
            {'skill_level': 2, 'gender': 'F'}
        ]
    
    print("Initial state:")
    for name, group in groups.items():
        print(f"{name}: {group['total_skill']} points")
    
    # Calculate what the ideal distribution should be
    total_points = sum(group['total_skill'] for group in groups.values())
    base_points = total_points // 6
    extra_points = total_points % 6
    
    print(f"\\nTotal points: {total_points}")
    print(f"Base points per group: {base_points}")
    print(f"Extra points to distribute: {extra_points}")
    print(f"Ideal distribution: {6-extra_points} groups get {base_points}, {extra_points} groups get {base_points+1}")
    print(f"Max difference should be: {base_points+1} - {base_points} = 1")
    
    # Show current vs ideal
    current_skills = [group['total_skill'] for group in groups.values()]
    current_max = max(current_skills)
    current_min = min(current_skills)
    print(f"\\nCurrent difference: {current_max} - {current_min} = {current_max - current_min}")
    
    if current_max - current_min <= 1:
        print("✅ Already balanced!")
    else:
        print("❌ Needs balancing")

if __name__ == "__main__":
    simple_balance_test()