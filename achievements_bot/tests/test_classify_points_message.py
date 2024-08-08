from achievements_bot.services import points_rate
from achievements_bot.services.cls import Color

positive = [
    "Лови 100 очков",
    "+555",
    "+100 очков",
    "+ 101 очков",
    "даю 101",
    "даю 101 очков",
    "получай 100 очков",
    "получай обратно свои 100 очков",
    "лови обратно свои 10 очков",
    "50 очков этому господину",
    "50 очков этому товарищу",
    "21 очков этому товарищу",
    "на 10",
    "на 10 очков",
    "держи 10",
    "держи 10 очков",
    "вот тебе 10 ",
    "вот тебе 10 очков",
    "плюс 10 очков",
    "увеличить социальный рейтинг на 100",
    "увеличиваем социальный рейтинг на 100",
]
negative = [
    "- 100 очков",
    "-555",
    "-5",
    "-101 очков",
    "-123 очка",
    "минус 123 очка",
    "отобрать 100 очков",
    "отнять 100 ",
    "отнять 100 очков",
    "минус 5 очков",
    "минус 3 очка",
    "минус 21 очко",
    "уменьшаем социальный рейтинг на 100",
    "уменьшить социальный рейтинг на 100",
]
error = [
    "я бы не от дал бы за это и 100 рублей",
    "+- за 100 рублей я бы взял",
    "получай по морде",
    "ловите наркомана",
    "иди в очко",
    "ну и очко",
    "100 раз уже такое видел",
]


def test():
    for message in positive:
        command_type, points = points_rate.classify_message(message)
        if command_type == 'positive':
            print(
                f"'{message}' => {Color.GREEN}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")
        else:
            print(
                f"'{message}' => {Color.RED}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")

    for message in negative:
        command_type, points = points_rate.classify_message(message)
        if command_type == 'negative':
            print(
                f"'{message}' => {Color.GREEN}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")
        else:
            print(
                f"'{message}' => {Color.RED}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")

    for message in error:
        command_type, points = points_rate.classify_message(message)
        if command_type == 'error':
            print(
                f"'{message}' => {Color.GREEN}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")
        else:
            print(
                f"'{message}' => {Color.RED}{command_type}{Color.END} => {Color.BLUE}{points}{Color.END}")


if __name__ == "__main__":
    test()