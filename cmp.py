import argparse
import re
import sys

from chess_engine import initial_state
from chess_engine import legal_moves as chess_moves
from chess_engine import play
from chess_engine import result as chess_result
from chess_engine import san as chess_san

VERSION = 'cmp1'
PROTOCOL_VERSION = VERSION
__version__ = '0.1.1'

UCI_RE = re.compile(r'^[a-h][1-8][a-h][1-8][qrbn]?$')


class CMPError(ValueError):
    pass


class InvalidMnemonic(CMPError):
    pass


def _split(mnemonic):
    words = str(mnemonic).strip().lower().split()
    if not words or words[0] != VERSION:
        raise InvalidMnemonic('mnemonic must start with %s' % VERSION)
    if len(words) == 1:
        raise InvalidMnemonic('mnemonic has no moves')
    return words[1:]


def _check_move(move, number):
    if not UCI_RE.match(move):
        raise InvalidMnemonic(
            'move %d is not canonical UCI: %s' % (number, move)
        )


def _next(state, move, number):
    _check_move(move, number)

    if not chess_moves(state):
        state = initial_state()

    try:
        return play(state, move)
    except ValueError:
        raise InvalidMnemonic('illegal move %d (%s)' % (number, move))


def _play_moves(moves):
    state = initial_state()
    for number, move in enumerate(moves, 1):
        state = _next(state, move, number)
    return state


def parse_mnemonic(mnemonic):
    moves = _split(mnemonic)
    _play_moves(moves)
    return tuple(moves)


def normalize(mnemonic):
    return VERSION + ' ' + ' '.join(parse_mnemonic(mnemonic))


def check(mnemonic):
    try:
        parse_mnemonic(mnemonic)
        return True
    except (TypeError, ValueError):
        return False


def _moves(value):
    if isinstance(value, str):
        words = value.strip().lower().split()
        if words and words[0] == VERSION:
            return list(parse_mnemonic(value))
        return words
    return [str(move).strip().lower() for move in value]


def legal_moves(moves=()):
    moves = _moves(moves)
    state = initial_state()

    for number, move in enumerate(moves, 1):
        state = _next(state, move, number)

    return chess_moves(state)


def _san_games(moves):
    games = []
    game = []
    state = initial_state()

    for move in moves:
        if not chess_moves(state):
            games.append((game, chess_result(state)))
            game = []
            state = initial_state()

        game.append(chess_san(state, move))
        state = play(state, move)

    games.append((game, chess_result(state)))
    return games


def _san_text(moves):
    words = []

    for number, move in enumerate(moves):
        if number % 2 == 0:
            words.append('%d. %s' % ((number // 2) + 1, move))
        else:
            words.append(move)

    return ' '.join(words)


def _pgn(game, result, number):
    result = result or '*'
    headers = [
        '[Event "CMP-1"]',
        '[Site "?"]',
        '[Date "????.??.??"]',
        '[Round "%d"]' % number,
        '[White "?"]',
        '[Black "?"]',
        '[Result "%s"]' % result,
    ]

    moves = _san_text(game)
    if moves:
        moves += ' '
    moves += result

    return '\n'.join(headers) + '\n\n' + moves


def convert_mnemonic(mnemonic, format='pgn'):
    moves = parse_mnemonic(mnemonic)
    format = str(format).strip().lower()

    if format == 'uci':
        return ' '.join(moves)

    games = _san_games(moves)

    if format == 'san':
        return '\n'.join(_san_text(game) for game, result in games)

    if format == 'pgn':
        blocks = []
        for number, item in enumerate(games, 1):
            game, result = item
            blocks.append(_pgn(game, result, number))
        return '\n\n'.join(blocks)

    raise ValueError('format must be uci, san, or pgn')


def _parser():
    parser = argparse.ArgumentParser(prog='cmp')
    parser.add_argument(
        '--version',
        action='version',
        version='cmp %s (protocol %s)' % (__version__, VERSION),
    )

    commands = parser.add_subparsers(dest='command', required=True)

    command = commands.add_parser('check', help='validate a mnemonic')
    command.add_argument('mnemonic', nargs='+')

    command = commands.add_parser('normalize', help='normalize a mnemonic')
    command.add_argument('mnemonic', nargs='+')

    command = commands.add_parser('convert', help='convert chess notation')
    command.add_argument('--to', choices=('uci', 'san', 'pgn'), default='pgn')
    command.add_argument('mnemonic', nargs='+')

    command = commands.add_parser('legal', help='list legal moves')
    command.add_argument('moves', nargs='*')

    return parser


def _text(words):
    return ' '.join(words)


def main(argv=None):
    args = _parser().parse_args(argv)

    if args.command == 'check':
        try:
            parse_mnemonic(_text(args.mnemonic))
        except InvalidMnemonic as error:
            print('invalid: %s' % error, file=sys.stderr)
            return 1
        print('valid')
        return 0

    if args.command == 'normalize':
        print(normalize(_text(args.mnemonic)))
        return 0

    if args.command == 'convert':
        print(convert_mnemonic(_text(args.mnemonic), args.to))
        return 0

    if args.command == 'legal':
        print(' '.join(legal_moves(args.moves)))
        return 0

    return 2


__all__ = [
    'CMPError',
    'InvalidMnemonic',
    'PROTOCOL_VERSION',
    'VERSION',
    '__version__',
    'check',
    'convert_mnemonic',
    'legal_moves',
    'main',
    'normalize',
    'parse_mnemonic',
]


if __name__ == '__main__':
    raise SystemExit(main())
