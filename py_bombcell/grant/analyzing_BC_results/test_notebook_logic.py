#!/usr/bin/env python3
"""
Simple test to validate the classification reason logic without running the full notebook.
This simulates the core logic of the notebook.
"""
import numpy as np
import pandas as pd

def test_classification_reason_logic():
    """Test the get_main_reason function logic"""
    
    # Simulate some test data
    n_units = 5
    
    # Create mock labels
    labels_np = np.array(['NOISE', 'MUA', 'NON-SOMA', 'GOOD', 'MUA'])
    
    # Create mock fail dictionaries
    noise_fail_np = {
        'nPeaks>maxNPeaks': np.array([True, False, False, False, False]),
        'scndPeakToTroughRatio>max': np.array([False, False, False, False, False]),
    }
    
    mua_fail_np = {
        'fractionRPVs>max': np.array([False, True, False, False, True]),
        'presenceRatio<min': np.array([False, False, False, False, False]),
    }
    
    nonsoma_fail_np = {
        'mainPeakToTroughRatio>max': np.array([False, False, True, False, False]),
    }
    
    # Define get_main_reason function (from notebook)
    def get_main_reason(i: int) -> str:
        label = labels_np[i]
        
        noise_hits = [k for k, v in noise_fail_np.items() if bool(v[i])]
        mua_hits = [k for k, v in mua_fail_np.items() if bool(v[i])]
        nonsoma_hits = [k for k, v in nonsoma_fail_np.items() if bool(v[i])]
        
        if label == 'NOISE':
            if noise_hits:
                return f'NOISE: {noise_hits[0]}'
            return 'NOISE'
        
        elif label in ('MUA', 'NON-SOMA MUA'):
            if mua_hits:
                return f'MUA: {mua_hits[0]}'
            return 'MUA'
        
        elif label in ('NON-SOMA', 'NON-SOMA GOOD'):
            if nonsoma_hits:
                return f'NON-SOMA: {nonsoma_hits[0]}'
            return 'NON-SOMA'
        
        elif label == 'GOOD':
            return 'GOOD: passed all thresholds'
        
        else:
            return f'{label}'
    
    # Test each unit
    print("Testing classification reason logic:")
    print("=" * 60)
    
    expected_results = [
        (0, 'NOISE', 'NOISE: nPeaks>maxNPeaks'),
        (1, 'MUA', 'MUA: fractionRPVs>max'),
        (2, 'NON-SOMA', 'NON-SOMA: mainPeakToTroughRatio>max'),
        (3, 'GOOD', 'GOOD: passed all thresholds'),
        (4, 'MUA', 'MUA: fractionRPVs>max'),
    ]
    
    all_passed = True
    for i, expected_label, expected_reason in expected_results:
        actual_reason = get_main_reason(i)
        passed = actual_reason == expected_reason
        all_passed = all_passed and passed
        
        status = "✓" if passed else "✗"
        print(f"{status} Unit {i} ({expected_label}): {actual_reason}")
        if not passed:
            print(f"  Expected: {expected_reason}")
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(test_classification_reason_logic())
