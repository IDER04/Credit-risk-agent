import risk_model
from agent import Agent
from database import DatabaseError, query

HELP = "Commands: /refresh (rebuild Risque table)  /reset (new conversation)  /quit"


def startup_check():
    try:
        n = query("SELECT COUNT(*) AS n FROM Client")[0]["n"]
        print(f"MySQL OK ({n} clients)")
        return True
    except DatabaseError as e:
        print(f"Erreur : {e}")
        return False

def confirm(description):
    print(f"\n!! {description}")
    return input("Proceed? (yes/no): ").strip().lower() in ("y", "yes", "oui", "o")
def main():
    if not startup_check():
        return
    agent = Agent(on_tool=lambda name, args: print(f"   [tool] {name}({args})"))
    print(HELP)
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/reset":
            agent.reset()
            print("Conversation cleared.")
            continue
        if text == "/refresh":
            try:
                print(f"Risque table rebuilt: {risk_model.refresh_risque_table()} rows.")
            except DatabaseError as e:
                print(f"Erreur : {e}")
            continue
        try:
            print("Agent:", agent.chat(text, confirm))
        except Exception as e:
            print(f"Erreur : {e}")


if __name__ == "__main__":
    main()