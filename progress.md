1. Scaffolding implemented. Planned with opus 4.6 and implemented with sonnet 4.5. Next steps:
  - Introduce some sort of novel testing regime?
  - Simplify logging?
  - Test if this even works
  - Create an interface to communication instead of "send_discord", do "send_message", with some appropriate way of setting the importance level. Why not replicate the design of the logging module?
  - Create an agent instruction file
  - Introduce ruff check and format, and ty check for styling
  - Most important! Are jobs.py and main.py understandable? These are the main entry points, and if these are poorly designed, everything false apart. Consider using codex 5.3 for review?