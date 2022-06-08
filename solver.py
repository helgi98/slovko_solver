import copy
import random

import db_util

WORD_LENGTH = 5
GAME_STEPS = 6

DB_PATH = "./data/words.db"


def fetch_words(word_length=5):
    with db_util.create_connection(DB_PATH) as conn:
        query = """select word from words
                 where length(word) = ?
                 order by word asc"""
        return db_util.execute_query(conn, query, (word_length,), lambda x: x[0])


def random_word(dictionary):
    return dictionary[random.randint(0, len(dictionary) - 1)]


class GuessResult:
    def __init__(self, contains=None, contains_exact=None, contains_no=None):
        if contains_no is None:
            contains_no = set()
        if contains_exact is None:
            contains_exact = {}
        if contains is None:
            contains = {}
        self.contains = contains
        self.contains_exact = contains_exact
        self.contains_no = contains_no

    def __str__(self):
        return f"\"contains\": {self.contains}\n\"contains_exact\": {self.contains_exact}\n" \
               f"\"contains_no\": {self.contains_no}"

    def not_at(self, i, c):
        if c not in self.contains:
            self.contains[c] = [1, {i}]
        else:
            if i not in self.contains[c][1]:
                self.contains[c][0] += 1
                self.contains[c][1].add(i)

    def at(self, i, c):
        if c not in self.contains_exact:
            self.contains_exact[c] = {i}
        else:
            self.contains_exact[c].add(i)

    def nr_of_exact(self, c):
        return len(self.contains_exact.get(c, []))

    def nr_of(self, c):
        return self.contains.get(c, [0, None])[0] + self.nr_of_exact(c)

    def no(self, c):
        self.contains_no.add(c)

    def merge(self, other):
        contains_no = self.contains_no.union(other.contains_no)
        contains_exact = copy.deepcopy(self.contains_exact)
        for (c, idx) in other.contains_exact.items():
            if c not in contains_exact:
                contains_exact[c] = copy.copy(idx)
            else:
                contains_exact[c].update(idx)

        def merge_contains(merged_exact, merged, gr):
            for (c, (cnt, idx)) in gr.contains.items():
                # count new exact occurrences
                cnt_new_exact_occ = max(len(merged_exact.get(c, set())) - gr.nr_of_exact(c), 0)
                cnt -= cnt_new_exact_occ
                if c not in merged:
                    merged[c] = [cnt, set(idx)]
                else:
                    merged[c][0] = max(merged[c][0], cnt)
                    merged[c][1].update(idx)

        contains = {}
        merge_contains(contains_exact, contains, self)
        merge_contains(contains_exact, contains, other)

        return GuessResult(contains, contains_exact, contains_no)


class GameOptions:
    def __init__(self, word_length=WORD_LENGTH, max_steps=GAME_STEPS):
        self.word_length = word_length
        self.max_steps = max_steps


class GameResult:
    def __init__(self, guesses, guess_result, steps, go=GameOptions(), err=None):
        self.guesses = list(map(lambda x: x[0], guesses))
        self.guess_results = list(map(lambda x: x[1], guesses))
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


def str_to_dict(str):
    res = {}
    for (i, c) in enumerate(str):
        if c not in res:
            res[c] = {i}
        else:
            res[c].add(i)

    return res


def check_guess(selected_word, guess):
    guess_res = GuessResult()
    selected_dict = str_to_dict(selected_word)

    for (i, c) in enumerate(guess):
        if c not in selected_dict:
            guess_res.no(c)
        else:
            indices = selected_dict[c]
            if i in indices:
                guess_res.at(i, c)
            else:
                guess_res.not_at(i, c)

    for (c, (cnt, idx)) in guess_res.contains.items():
        # number of occurrences in selected word
        cnt_selected = len(selected_dict[c])
        # number of exact occurrences in guess
        cnt_exact = guess_res.nr_of_exact(c)
        # number of occurrences in guess
        cnt_occ = len(idx)
        # number of confirmed occurrences
        guess_res.contains[c][0] = min(cnt_occ, cnt_selected - cnt_exact)

    return guess_res


def make_guess(dictionary, guess_res):
    # TODO use information theory to improve guess
    return random_word(dictionary)


# cnt = [0]
# imit = ['сагач', 'бадам', 'ратай', 'тарах', 'карат']
#
# def make_guess_imit(dictionary, guess_res):
#     res = imit[cnt[0]]
#     cnt[0] += 1
#     return res


def filter_possible_words(dictionary, guess_res):
    def check_doesnt_contain(w):
        return all(c not in w for c in guess_res.contains_no)

    def check_contains_exact(w):
        return all((all(w[i] == c for i in idx)) for c, idx in guess_res.contains_exact.items())

    def check_contains(w):
        return all(all(w[i] != c for i in idx) and
                   guess_res.nr_of(c) <= w.count(c)
                   for c, (cnt, idx) in guess_res.contains.items())

    def check_word(w):
        return check_doesnt_contain(w) and check_contains_exact(w) and check_contains(w)

    return list(filter(check_word, dictionary))


def form_word(guess_res, word_length):
    idx_to_c = dict([(i, c) for c, idx in guess_res.contains_exact.items() for i in idx])

    s = ""
    for i in range(0, word_length):
        if i in idx_to_c:
            s += idx_to_c[i]
        else:
            s += "-"

    return s


def check_found(guess_res, word_length):
    return sum(len(idx) for c, idx in guess_res.contains_exact.items()) == word_length


def play_game(dictionary, check_guess, go=GameOptions()):
    agg_res = GuessResult()
    guesses = []
    for i in range(0, go.max_steps):
        guess = make_guess(dictionary, agg_res)
        guess_res = check_guess(guess)

        guesses.append((guess, guess_res))
        agg_res = agg_res.merge(guess_res)

        dictionary = filter_possible_words(dictionary, guess_res)
        if len(dictionary) == 0:
            return GameResult(guesses, agg_res, i + 1, go, err="Not Found In Dictionary")

        if check_found(guess_res, go.word_length):
            return GameResult(guesses, agg_res, i + 1, go)

    return GameResult(guesses, agg_res, go.max_steps)


dictionary = fetch_words(word_length=WORD_LENGTH)
selected_word = random_word(dictionary)
res = play_game(dictionary, lambda w: check_guess(selected_word, w))
print(res)
