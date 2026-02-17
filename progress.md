## 17.02.26

Added ruff and ty and set up discord server with a webhook to receive messages. 

main.py is perhaps a bit rigorous. I haven't dived into the details, but it would make sense though, considering all the issues that might occur. "jobs.py" as a separate script makes perfect sense, I believe, as I can test this internally without considering what git is doing, or risk being locked by an earlier subprocess, etc.

Tasks below are still relevant, but perhaps more importantly:
- How would i set this up for a more appropriate task? Some candidates:
  - Bus delay
  - Traffic build-up on commute
  - Car ad extraction

## 16.02.26
Scaffolding implemented. Planned with opus 4.6 and implemented with sonnet 4.5. Next steps:
  - ⬜ Introduce some sort of novel testing regime?
  - ✅ Simplify logging?
  - ✅ Test if this even works
  - ⬜ Create an interface to communication instead of "send_discord", do "send_message", with some appropriate way of setting the importance level. Why not replicate the design of the logging module?
  - ⬜ Create an agent instruction file
  - ✅ Introduce ruff check and format, and ty check for styling
  - ✅ Most important! Are jobs.py and main.py understandable? These are the main entry points, and if these are poorly designed, everything false apart. Consider using codex 5.3 for review?