#!/usr/bin/env python3
"""
Dedicated robust test runner for RADAR AI-2 Conjunction unit test suite.
Executes all test cases and generates detailed pass/fail reports with timing.
"""

import importlib
import inspect
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

TEST_MODULES = [
    "tests.unit.conjunction.test_coarse_filter",
    "tests.unit.conjunction.test_fine_filter",
    "tests.unit.conjunction.test_tca_refiner",
    "tests.unit.conjunction.test_encounter_frame",
    "tests.unit.conjunction.test_foster_2d",
    "tests.unit.conjunction.test_monte_carlo",
    "tests.unit.conjunction.test_encounter_models",
    "tests.unit.conjunction.test_pc_engine",
    "tests.unit.conjunction.test_pipeline",
]


def run_all():
    total = 0
    passed = 0
    failed = 0
    failures = []
    
    print("=" * 70, flush=True)
    print("🛰️  RADAR SSA System — AI-2 Conjunction & Pc Engine Test Suite", flush=True)
    print("=" * 70, flush=True)
    
    t_start = time.time()
    
    for mod_path in TEST_MODULES:
        print(f"\n📂 Module: {mod_path}", flush=True)
        try:
            mod = importlib.import_module(mod_path)
        except Exception as e:
            print(f"  ❌ Import error in {mod_path}: {e}", flush=True)
            failed += 1
            failures.append((mod_path, "IMPORT_ERROR", str(e)))
            continue
            
        test_fns = [
            (name, fn)
            for name, fn in inspect.getmembers(mod, inspect.isfunction)
            if name.startswith("test_")
        ]
        
        for name, fn in test_fns:
            total += 1
            t0 = time.perf_counter()
            try:
                fn()
                dt_ms = (time.perf_counter() - t0) * 1000.0
                print(f"  ✅ [PASS] {name} ({dt_ms:.2f} ms)", flush=True)
                passed += 1
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                print(f"  ❌ [FAIL] {name} ({dt_ms:.2f} ms): {e}", flush=True)
                failed += 1
                failures.append((mod_path, name, str(e)))
                
    elapsed = time.time() - t_start
    print("\n" + "=" * 70, flush=True)
    print(f"📊 SUMMARY: {passed} passed, {failed} failed out of {total} total tests ({elapsed:.3f}s total)", flush=True)
    print("=" * 70, flush=True)
    
    if failures:
        print("\n❌ Failures:", flush=True)
        for mod_path, name, err in failures:
            print(f"  - {mod_path}::{name} -> {err}", flush=True)
        sys.exit(1)
    else:
        print("🎉 ALL TESTS PASSED WITH 100% SUCCESS RATE!", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    run_all()
