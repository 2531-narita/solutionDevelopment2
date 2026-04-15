import random

def get_random_greeting():
    greetings = [
        "こんにちは！良い一日を！",
        "おはようございます！今日も頑張りましょう！",
        "こんばんは。お疲れ様でした！",
        "やあ！調子はどう？",
        "ごきげんよう！",
        "Hello! How are you doing today?",
        "おっす！",
        "まいど！"
    ]
    return random.choice(greetings)

if __name__ == "__main__":
    print(get_random_greeting())
