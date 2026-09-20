FILES = 'abcdefgh'
PROMOTIONS = 'qrbn'
KNIGHT_STEPS = ((1,2),(2,1),(2,-1),(1,-2),(-1,-2),(-2,-1),(-2,1),(-1,2))
BISHOP_DIRS = ((1,1),(1,-1),(-1,1),(-1,-1))
ROOK_DIRS = ((1,0),(-1,0),(0,1),(0,-1))


def _sq(file, rank):
    return rank * 8 + file


def _file(square):
    return square & 7


def _rank(square):
    return square >> 3


def _inside(file, rank):
    return 0 <= file < 8 and 0 <= rank < 8


def _other(color):
    return 'b' if color == 'w' else 'w'


def _color(piece):
    if not piece:
        return None
    return 'w' if piece.isupper() else 'b'


def _type(piece):
    if not piece:
        return None
    return piece.lower()


def _name(square):
    return '%s%d' % (FILES[_file(square)], _rank(square) + 1)


def initial_state():
    board = [None] * 64
    back = 'rnbqkbnr'

    for file in range(8):
        board[_sq(file, 0)] = back[file].upper()
        board[_sq(file, 1)] = 'P'
        board[_sq(file, 6)] = 'p'
        board[_sq(file, 7)] = back[file]

    return {
        'board': board,
        'turn': 'w',
        'castling': set('KQkq'),
        'ep': None,
    }


def _copy(state):
    return {
        'board': state['board'].copy(),
        'turn': state['turn'],
        'castling': state['castling'].copy(),
        'ep': state['ep'],
    }


def _attacked(state, target, color):
    board = state['board']
    target_file = _file(target)
    target_rank = _rank(target)
    pawn_rank = target_rank + (-1 if color == 'w' else 1)

    for df in (-1, 1):
        file = target_file + df
        if _inside(file, pawn_rank):
            piece = board[_sq(file, pawn_rank)]
            if piece and _color(piece) == color and _type(piece) == 'p':
                return True

    for df, dr in KNIGHT_STEPS:
        file = target_file + df
        rank = target_rank + dr
        if _inside(file, rank):
            piece = board[_sq(file, rank)]
            if piece and _color(piece) == color and _type(piece) == 'n':
                return True

    for dirs, pieces in ((BISHOP_DIRS, 'bq'), (ROOK_DIRS, 'rq')):
        for df, dr in dirs:
            file = target_file + df
            rank = target_rank + dr
            while _inside(file, rank):
                piece = board[_sq(file, rank)]
                if piece:
                    if _color(piece) == color and _type(piece) in pieces:
                        return True
                    break
                file += df
                rank += dr

    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if not (df or dr):
                continue
            file = target_file + df
            rank = target_rank + dr
            if _inside(file, rank):
                piece = board[_sq(file, rank)]
                if piece and _color(piece) == color and _type(piece) == 'k':
                    return True

    return False


def _in_check(state, color):
    king = 'K' if color == 'w' else 'k'
    try:
        square = state['board'].index(king)
    except ValueError:
        return True
    return _attacked(state, square, _other(color))


def _castling_moves(state, start, add):
    board = state['board']
    turn = state['turn']
    rank = 0 if turn == 'w' else 7

    if start != _sq(4, rank) or _in_check(state, turn):
        return

    enemy = _other(turn)
    rook = 'R' if turn == 'w' else 'r'
    king_side = 'K' if turn == 'w' else 'k'
    queen_side = 'Q' if turn == 'w' else 'q'

    if king_side in state['castling'] and board[_sq(7, rank)] == rook:
        if not board[_sq(5, rank)] and not board[_sq(6, rank)]:
            safe = not _attacked(state, _sq(5, rank), enemy)
            safe = safe and not _attacked(state, _sq(6, rank), enemy)
            if safe:
                add(start, _sq(6, rank))

    if queen_side in state['castling'] and board[_sq(0, rank)] == rook:
        clear = not board[_sq(1, rank)]
        clear = clear and not board[_sq(2, rank)]
        clear = clear and not board[_sq(3, rank)]
        if clear:
            safe = not _attacked(state, _sq(3, rank), enemy)
            safe = safe and not _attacked(state, _sq(2, rank), enemy)
            if safe:
                add(start, _sq(2, rank))


def _pseudo_moves(state):
    moves = []
    board = state['board']
    turn = state['turn']

    def add(start, end, promotion=''):
        moves.append((start, end, promotion))

    for start, piece in enumerate(board):
        if not piece or _color(piece) != turn:
            continue

        kind = _type(piece)
        file = _file(start)
        rank = _rank(start)

        if kind == 'p':
            step = 1 if turn == 'w' else -1
            home = 1 if turn == 'w' else 6
            promo = 7 if turn == 'w' else 0
            one = rank + step

            if _inside(file, one) and not board[_sq(file, one)]:
                end = _sq(file, one)
                if one == promo:
                    for promotion in PROMOTIONS:
                        add(start, end, promotion)
                else:
                    add(start, end)

                two = rank + (2 * step)
                if rank == home and not board[_sq(file, two)]:
                    add(start, _sq(file, two))

            for df in (-1, 1):
                capture_file = file + df
                capture_rank = rank + step
                if not _inside(capture_file, capture_rank):
                    continue

                end = _sq(capture_file, capture_rank)
                target = board[end]
                capture = target and _color(target) != turn
                if capture or state['ep'] == end:
                    if capture_rank == promo:
                        for promotion in PROMOTIONS:
                            add(start, end, promotion)
                    else:
                        add(start, end)
            continue

        if kind == 'n':
            for df, dr in KNIGHT_STEPS:
                next_file = file + df
                next_rank = rank + dr
                if not _inside(next_file, next_rank):
                    continue
                end = _sq(next_file, next_rank)
                if not board[end] or _color(board[end]) != turn:
                    add(start, end)
            continue

        if kind in 'brq':
            if kind == 'b':
                dirs = BISHOP_DIRS
            elif kind == 'r':
                dirs = ROOK_DIRS
            else:
                dirs = BISHOP_DIRS + ROOK_DIRS

            for df, dr in dirs:
                next_file = file + df
                next_rank = rank + dr
                while _inside(next_file, next_rank):
                    end = _sq(next_file, next_rank)
                    if not board[end]:
                        add(start, end)
                    else:
                        if _color(board[end]) != turn:
                            add(start, end)
                        break
                    next_file += df
                    next_rank += dr
            continue

        if kind == 'k':
            for df in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if not (df or dr):
                        continue
                    next_file = file + df
                    next_rank = rank + dr
                    if _inside(next_file, next_rank):
                        end = _sq(next_file, next_rank)
                        if not board[end] or _color(board[end]) != turn:
                            add(start, end)
            _castling_moves(state, start, add)

    return moves


def _apply(state, move):
    start, end, promotion = move
    new_state = _copy(state)
    board = new_state['board']
    piece = board[start]
    color = _color(piece)
    kind = _type(piece)
    captured = board[end]
    start_name = _name(start)
    end_name = _name(end)

    board[start] = None

    if kind == 'p' and state['ep'] == end and not captured:
        if _file(start) != _file(end):
            offset = -8 if color == 'w' else 8
            board[end + offset] = None

    if promotion:
        piece = promotion.upper() if color == 'w' else promotion

    board[end] = piece

    if kind == 'k' and abs(_file(end) - _file(start)) == 2:
        rank = _rank(start)
        king_side = _file(end) == 6
        rook_from = _sq(7 if king_side else 0, rank)
        rook_to = _sq(5 if king_side else 3, rank)
        board[rook_to] = board[rook_from]
        board[rook_from] = None

    if kind == 'k':
        new_state['castling'].discard('K' if color == 'w' else 'k')
        new_state['castling'].discard('Q' if color == 'w' else 'q')

    rights = (('h1','K'),('a1','Q'),('h8','k'),('a8','q'))
    for square, right in rights:
        if start_name == square or end_name == square:
            new_state['castling'].discard(right)

    new_state['ep'] = None
    if kind == 'p' and abs(_rank(end) - _rank(start)) == 2:
        new_state['ep'] = (start + end) >> 1

    new_state['turn'] = _other(state['turn'])
    return new_state


def _uci(move):
    start, end, promotion = move
    return _name(start) + _name(end) + promotion


def _legal_objects(state):
    color = state['turn']
    moves = []

    for move in _pseudo_moves(state):
        if not _in_check(_apply(state, move), color):
            moves.append(move)

    return moves


def _find_move(state, uci):
    uci = str(uci).strip().lower()
    for move in _legal_objects(state):
        if _uci(move) == uci:
            return move
    raise ValueError('illegal move: %s' % uci)


def legal_moves(state):
    moves = [_uci(move) for move in _legal_objects(state)]
    moves.sort()
    return moves


def _is_capture(state, move):
    start, end, unused = move
    piece = state['board'][start]

    if state['board'][end]:
        return True

    return (
        _type(piece) == 'p'
        and state['ep'] == end
        and _file(start) != _file(end)
    )


def _san_prefix(state, move, legal):
    start, end, unused = move
    board = state['board']
    kind = _type(board[start])

    if kind == 'p':
        return FILES[_file(start)] if _is_capture(state, move) else ''

    prefix = kind.upper()
    others = []
    for candidate in legal:
        if candidate == move or candidate[1] != end:
            continue
        if _type(board[candidate[0]]) == kind:
            others.append(candidate)

    if not others:
        return prefix

    same_file = any(_file(other[0]) == _file(start) for other in others)
    same_rank = any(_rank(other[0]) == _rank(start) for other in others)

    if not same_file:
        return prefix + FILES[_file(start)]
    if not same_rank:
        return prefix + str(_rank(start) + 1)
    return prefix + _name(start)


def san(state, uci):
    legal = _legal_objects(state)
    uci = str(uci).strip().lower()
    move = None

    for candidate in legal:
        if _uci(candidate) == uci:
            move = candidate
            break

    if move is None:
        raise ValueError('illegal move: %s' % uci)

    start, end, promotion = move
    kind = _type(state['board'][start])

    if kind == 'k' and abs(_file(end) - _file(start)) == 2:
        text = 'O-O' if _file(end) == 6 else 'O-O-O'
    else:
        text = _san_prefix(state, move, legal)
        if _is_capture(state, move):
            text += 'x'
        text += _name(end)
        if promotion:
            text += '=' + promotion.upper()

    next_state = _apply(state, move)
    if _in_check(next_state, next_state['turn']):
        text += '#' if not _legal_objects(next_state) else '+'

    return text


def play(state, uci):
    return _apply(state, _find_move(state, uci))


def result(state):
    if _legal_objects(state):
        return None
    if not _in_check(state, state['turn']):
        return '1/2-1/2'
    return '0-1' if state['turn'] == 'w' else '1-0'
