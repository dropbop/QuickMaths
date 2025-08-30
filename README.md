QuickMaths — Mental Math Game

Run a fast, flexible CLI game focused on quick mental math across multiple modes: arithmetic, unit conversions, and timezones. Scoring balances accuracy and speed — simple problems demand tighter precision and reward speed more; harder ones allow more tolerance and weigh speed less.

How to run

- Prerequisite: Python 3.8+ installed
- CLI: `python quickmaths.py`
- GUI: `python quickmaths_gui.py`

GUI mode

- Choose mode, difficulty (for arithmetic/mixed), and number of questions.
- Answer directly in the input box; press Enter or click Submit.
- The timer runs per question; scoring balances accuracy and speed.
- A summary view appears at the end with your total score.

Game modes

- Arithmetic: Mixed +, −, ×, ÷ with integers and decimals (by chosen difficulty).
- Unit Conversion: Length, mass, temperature, and volume conversions.
- Timezones: Convert local times between common world timezones (ignores DST).
- Mixed: Randomly selects from the above.

Scoring (summary)

- Accuracy tolerance grows with difficulty and answer magnitude; simple integer arithmetic typically needs ±1 to be considered accurate.
- Speed impact scales with difficulty: speed matters more on easy questions than hard ones.
- Final score combines accuracy and speed; detailed breakdown shown per question.

Notes

- Timezone questions ignore daylight saving transitions and day changes; answer in 24h `HH:MM`.
- No external dependencies; fully offline.
