import json
import random
import Levenshtein

W = json.load(open('data/words.json'))
L = json.load(open('data/lines.json'))
C = json.load(open('data/channels.json'))
B = json.load(open('data/bots.json'))


def pretty(items, formatting='%s', final='and'):
    """Prettify a list of strings.

    items:      list of strings to be displayed
    formatting: formatting string to apply to each string, must contain "%s"
    final:      linking word of two last strings, typically "and" or "or", should be localized"""
    if not items:
        return ''
    elif len(items) == 1:
        return formatting % items[0]
    else:
        formatted = [formatting % item for item in items]
        return f'%s {final} %s' % (', '.join(formatted[:-1]), formatted[-1])


def human_duration(seconds):
    if seconds < 1:
        seconds = 1
    words = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400, 'week': 604800, 'month': 2635200, 'year': 31536000}
    word = 'second'
    for w, duration in words.items():
        if seconds >= duration:
            word = w
    n = seconds // words.get(word)
    if n >= 2:
        word += 's'
    return '%d %s' % (n, word)


def lev_close(w1, w2, perms=True):
    if Levenshtein.distance(w1.lower(), w2.lower()) <= (len(w1) + len(w2)) // 6:
        return True
    if not perms:
        return False
    for i in range(len(w2)-1):
        if lev_close(w1, w2[:i] + w2[i+1] + w2[i] + w2[i+2:], perms=False):
            return True
    return False


def random_subs(text):
    a = len(text)
    while a >= 0:
        try:
            a = text.rindex('{', 0, a)
            b = text.index('}', a)
        except ValueError:
            return text
        if '|' in text[a:b]:
            text = text[:a] + random.choice(text[a+1:b].split('|')) + text[b+1:]
    return text


def get_line(key, src=L):
    value = src.get(key)
    line = None
    if isinstance(value, dict):
        value = value.get('desc')
    if value is None:
        line = ''
    elif isinstance(value, str):
        line = value
    elif isinstance(value, list):
        pool = []
        for line in value:
            pool.extend([line['s']] * line['w'])
        line = random.choice(pool)
    line = random_subs(line)
    line = ' '.join(line.split())
    return line.replace('<br>', '\n')


def format_line(key, message=None, src=L, **kwargs):
    line = get_line(key, src=src)
    if message is None:
        return line.format(**kwargs)
    else:
        return line.format(user=message.author.display_name, user_mention=message.author.mention,
                           channel=message.channel.name, channel_mention=message.channel.mention,
                           server=message.server.name)


def contains_list(line, w_list):
    if isinstance(w_list, str):
        w_list = W.get(w_list, set())
    count = 0
    for word in w_list:
        if in_line(line, word):
            count += 1
    return count


def in_line(line, word):
    spaces = word.count(' ')
    words = line.split()
    for i in range(len(words)-spaces):
        comp = ' '.join(words[i:i+1+spaces])
        if lev_close(comp, word):
            return True
    return False
