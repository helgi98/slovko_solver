import random

import db_util

db_path = "./data/words.db"


def fetch_words(word_length=5):
    with db_util.create_connection(db_path) as conn:
        return list(map(lambda x: x[0],
                        db_util.execute_query(conn, """select word from words
                                             where length(word) = ?
                                             order by word asc""",
                                              (word_length,))))


WORD_LENGTH = 5
GAME_STEPS = 6


def random_word(dictionary):
    return dictionary[random.randint(0, len(dictionary) - 1)]


dictionary = fetch_words(word_length=WORD_LENGTH)

guess_res_ex = {
    "contains": {"а": (2, [])},
    "contains_precise": {"к": [0]},
    "contains_no": [""]
}


class GuessResult:
    def __init__(self, contains_not_at=None, contains_precise=None, contains_no=None):
        if contains_no is None:
            contains_no = set()
        if contains_precise is None:
            contains_precise = {}
        if contains_not_at is None:
            contains_not_at = {}
        self.contains_not_at = contains_not_at
        self.contains_precise = contains_precise
        self.contains_no = contains_no

    def __str__(self):
        return f"\"contains\": {self.contains_not_at}\n\"contains_precise\": {self.contains_precise}\n" \
               f"\"contains_no\": {self.contains_no}"


class GameOptions:
    def __init__(self, word_length=WORD_LENGTH, max_steps=GAME_STEPS):
        self.word_length = word_length
        self.max_steps = max_steps


class GameResult:
    def __init__(self, guesses, guess_result, steps, go=GameOptions(), err=None):
        self.guesses = guesses
        self.guess_result = guess_result
        self.steps = steps
        self.word = form_word(guess_result, go.word_length)
        self.error = err

    def __str__(self):
        if self.error:
            return f"Couldn't find correct word due to {self.error}.\n" \
                   f"\"Steps used\": {self.steps}\n" \
                   f"\"Words used\": {self.guesses}\n" \
                   f"\"Guess result data\":\n{self.guess_result}"

        return f"\"Guessed word\": {self.word}\n" \
               f"\"Steps used\": {self.steps}\n" \
               f"\"Words used\": {self.guesses}\n" \
               f"\"Guess result data\":\n{self.guess_result}"


def check_guess(selected_word, guess):
    guess_res = GuessResult()
    for (i, c) in enumerate(guess):
        swc = selected_word[i]
        if c == swc:
            if c not in guess_res.contains_precise:
                guess_res.contains_precise[c] = {i}
            else:
                guess_res.contains_precise[c].add(i)
        elif c in selected_word:
            if c not in guess_res.contains_not_at:
                guess_res.contains_not_at[c] = [1, {i}]
            else:
                guess_res.contains_not_at[c][0] += 1
                guess_res.contains_not_at[c][1].add(i)
        else:
            guess_res.contains_no.add(c)

    for (c, k) in guess_res.contains_not_at.items():
        guess_res.contains_not_at[c][0] = max(guess_res.contains_not_at[c][0], selected_word.count(c))
        if c in guess_res.contains_precise:
            guess_res.contains_not_at[c][0] -= len(guess_res.contains_precise[c])

    return guess_res


def make_guess(dictionary, guess_res):
    return random_word(dictionary)


cnt = [0]
imit = ['омськ', 'уклін', 'кичка']


def make_guess_imit(dictionary, guess_res):
    res = imit[cnt[0]]
    cnt[0] += 1
    return res


def filter_possible_words(dictionary, guess_res):
    def check_doesnt_contain(w):
        return all(c not in w for c in guess_res.contains_no)

    def check_contains_precise(w):
        return all((all(w[i] == c for i in idx)) for c, idx in guess_res.contains_precise.items())

    def check_contains(w):
        return all((all(w[i] != c for i in idx)) and
                   cnt <= w.count(c) - len(guess_res.contains_precise.get(c, []))
                   for c, (cnt, idx) in guess_res.contains_not_at.items())

    def check_word(w):
        return check_doesnt_contain(w) and check_contains_precise(w) and check_contains(w)

    return list(filter(check_word, dictionary))


def form_word(guess_res, word_length):
    idx_to_c = dict([(i, c) for c, idx in guess_res.contains_precise.items() for i in idx])

    s = ""
    for i in range(0, word_length):
        if i in idx_to_c:
            s += idx_to_c[i]
        else:
            s += "-"

    return s


def check_found(guess_res, word_length):
    return sum(len(idx) for c, idx in guess_res.contains_precise.items()) == word_length


def aggregate_results(guess_res1, guess_res2):
    contains_no = guess_res1.contains_no.union(guess_res2.contains_no)
    contains_precise = {**guess_res1.contains_precise, **guess_res2.contains_precise}
    contains_not_at = {}
    for (c, (cnt, idx)) in guess_res1.contains_not_at.items():
        contains_not_at[c] = [cnt, idx]
    for (c, (cnt, idx)) in guess_res2.contains_not_at.items():
        if c not in contains_not_at:
            contains_not_at[c] = [cnt, idx]
        else:
            contains_not_at[c][0] = max(contains_not_at[c][0], cnt)
            contains_not_at[c][1].update(idx)

    return GuessResult(contains_not_at, contains_precise, contains_no)


def play_game(dictionary, check_guess, go=GameOptions()):
    guess_res = GuessResult()
    agg_res = GuessResult()
    guesses = []
    for i in range(0, go.max_steps):
        guess = make_guess(dictionary, guess_res)
        guesses.append(guess)

        guess_res = check_guess(guess)
        agg_res = aggregate_results(agg_res, guess_res)

        dictionary = filter_possible_words(dictionary, guess_res)
        if len(dictionary) == 0:
            return GameResult(guesses, agg_res, i + 1, go, err="Not Found In Dictionary")

        if check_found(guess_res, go.word_length):
            return GameResult(guesses, agg_res, i + 1, go)

    return GameResult(guesses, agg_res, go.max_steps)


selected_word = "карат"

gr = play_game(dictionary, lambda w: check_guess(selected_word, w))

print(gr.__str__())
