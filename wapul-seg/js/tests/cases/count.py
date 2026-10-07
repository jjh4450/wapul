import sys
from collections import Counter

input = sys.stdin.readline


def solve(words):
    counts = Counter(words)
    best = max(counts.values())
    return [w for w, c in counts.items() if c == best]


n = int(input())
words = []
for _ in range(n):
    words.append(input().strip())
answer = solve(words)
if len(answer) == 1:
    print(answer[0])
else:
    print(len(answer))
    for w in sorted(answer):
        print(w)
