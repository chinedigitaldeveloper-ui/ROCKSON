#!/usr/bin/env python3
import os
import sys
import glob
import time
import subprocess
import shlex
from dataclasses import dataclass, field
from typing import List

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

@dataclass
class TestCase:
    filepath: str
    run_mode: str = "success"  # "success", "compile-fail", "runtime-fail", "module"
    expected_outputs: List[str] = field(default_factory=list)
    expected_errors: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)

def parse_test(filepath: str) -> TestCase:
    test = TestCase(filepath=filepath)
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith("//"):
                continue
            comment = line.lstrip("/").strip()
            if comment.startswith("RUN:"):
                test.run_mode = comment.split("RUN:", 1)[1].strip()
            elif comment.startswith("EXPECT:"):
                test.expected_outputs.append(comment.split("EXPECT:", 1)[1].strip())
            elif comment.startswith("ERROR:"):
                test.expected_errors.append(comment.split("ERROR:", 1)[1].strip())
            elif comment.startswith("ARGS:"):
                test.args = shlex.split(comment.split("ARGS:", 1)[1].strip())
    return test

def run_test(test: TestCase) -> tuple[bool, str]:
    if test.run_mode in ("module", "skip"):
        return True, "skip"

    bin_name = f"./tmp_{os.path.basename(test.filepath)}.bin"

    compile_cmd = ["./myc", test.filepath, "-o", bin_name]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True)

    if test.run_mode == "compile-fail":
        if proc.returncode == 0:
            if os.path.exists(bin_name):
                os.remove(bin_name)
            return False, "Expected compilation to fail, but it succeeded."
        
        output = proc.stdout + proc.stderr
        for err in test.expected_errors:
            if err not in output:
                return False, f"Expected error '{err}' not found in compiler output:\n{output.strip()}"
        return True, ""

    if proc.returncode != 0:
        return False, f"Compilation failed unexpectedly:\n{proc.stdout.strip()}\n{proc.stderr.strip()}"

    try:
        run_proc = subprocess.run([bin_name] + test.args, capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        if os.path.exists(bin_name):
            os.remove(bin_name)
        return False, "Execution timed out (5s limit)."
    finally:
        if os.path.exists(bin_name):
            os.remove(bin_name)

    if test.run_mode == "runtime-fail":
        if run_proc.returncode == 0:
            return False, "Expected binary to crash/fail, but exited 0."
        output = run_proc.stdout + run_proc.stderr
        for err in test.expected_errors:
            if err not in output:
                return False, f"Expected runtime message '{err}' not found in output:\n{output.strip()}"
        return True, ""

    if run_proc.returncode != 0:
        return False, f"Binary exited with code {run_proc.returncode}:\n{run_proc.stderr.strip()}"

    stdout = run_proc.stdout
    stdout_normalized = " ".join(stdout.split())
    for expected in test.expected_outputs:
        if expected not in stdout and " ".join(expected.split()) not in stdout_normalized:
            return False, f"Expected stdout to contain '{expected}', got:\n{stdout.strip()}"

    return True, ""

def main():
    test_files = sorted(glob.glob("*.src"))
    if not test_files:
        print("No .src files found to test.")
        sys.exit(1)

    print(f"{BOLD}Running Compiler Test Suite ({len(test_files)} tests){RESET}\n" + "─" * 50)
    passed = 0
    failed = 0
    skipped = 0
    start_total = time.time()

    for path in test_files:
        test = parse_test(path)
        if test.run_mode in ("module", "skip"):
            skipped += 1
            print(f"  {BLUE}[SKIP]{RESET} {path:<25} (module)")
            continue

        t0 = time.time()
        ok, msg = run_test(test)
        elapsed = (time.time() - t0) * 1000

        if ok:
            passed += 1
            print(f"  {GREEN}[PASS]{RESET} {path:<25} ({elapsed:.1f} ms)")
        else:
            failed += 1
            print(f"  {RED}[FAIL]{RESET} {path:<25} ({elapsed:.1f} ms)")
            print(f"         {RED}↳ {msg}{RESET}")

    total_time = time.time() - start_total
    print("─" * 50)
    if failed == 0:
        print(f"{GREEN}{BOLD}ALL {passed} TESTS PASSED{RESET} ({skipped} modules skipped) in {total_time:.2f}s")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}{failed} FAILED{RESET}, {passed} passed in {total_time:.2f}s")
        sys.exit(1)

if __name__ == "__main__":
    main()
