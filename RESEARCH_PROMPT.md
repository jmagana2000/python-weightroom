# Research Prompt: Python Skill-Reinforcement Exercise App

Research and design a local, browser-based application that trains a single
user's Python skills through leveled coding exercises (novice → advanced),
similar in spirit to LeetCode/HackerRank but self-hosted and adaptive to the
user's current level.

Answer these questions:

1. **Execution model** — how should user-submitted Python code run against
   test cases? Compare a server-side subprocess/sandbox approach vs.
   in-browser execution (e.g., Pyodide/WASM). Which is safer and simpler for
   a single-user local app?
2. **Content model** — what's the minimal data format for an exercise
   (prompt, starter code, hidden test cases, difficulty, topic tags) that's
   easy to author and extend?
3. **Leveling system** — how does the app track a user's level and progress
   them from novice to advanced? What signal (pass rate, streak, topic
   coverage) triggers a level change, and how is it stored?
4. **Stack** — what's the smallest stack (ideally stdlib + one well-known
   library) that serves a local web UI, runs code, and grades it, without a
   database server or account system?
5. **Content sourcing** — hand-author exercises vs. pull from an existing
   open-source problem bank; tradeoffs on volume, quality, and license.
6. **MVP scope** — what's the smallest version that is actually useful today
   (run it, solve a problem, get pass/fail, level up), deferring anything
   speculative?

Output: a concrete architecture + MVP plan, not a survey of every option.
