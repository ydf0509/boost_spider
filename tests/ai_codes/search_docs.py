
import re

file_path = r"d:\codes\boost_spider\funboost_all_docs_and_codes.md"
search_terms = ["funboost.workflow", "fabric_deploy", "process_num", "process_count"]

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for term in search_terms:
    print(f"--- Searching for '{term}' ---")
    for i, line in enumerate(lines):
        if term in line:
            print(f"Line {i+1}: {line.strip()}")
            # Print context for workflow
            if "workflow" in term:
                print("Context:")
                start = max(0, i - 5)
                end = min(len(lines), i + 20)
                for j in range(start, end):
                    print(f"{j+1}: {lines[j].rstrip()}")
