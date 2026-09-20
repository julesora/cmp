import contextlib
import io
import json
import os
import unittest

import cmp
from chess_engine import initial_state
from chess_engine import legal_moves as engine_legal_moves
from chess_engine import play


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CMPTests(unittest.TestCase):
    def test_chess_starts_with_20_moves(self):
        moves = cmp.legal_moves()
        self.assertEqual(len(moves), 20)
        self.assertEqual(moves, sorted(moves))

    def test_normalize(self):
        self.assertEqual(
            cmp.normalize('  CMP1   E2E4   E7E5  '),
            'cmp1 e2e4 e7e5',
        )

    def test_check_returns_boolean(self):
        self.assertTrue(cmp.check('cmp1 e2e4 e7e5'))
        self.assertFalse(cmp.check('cmp1 e2e5'))
        self.assertFalse(cmp.check('e2e4'))

    def test_parse_returns_canonical_moves(self):
        self.assertEqual(
            cmp.parse_mnemonic('CMP1 E2E4 E7E5'),
            ('e2e4', 'e7e5'),
        )

    def test_invalid_error_contains_move_index(self):
        with self.assertRaisesRegex(cmp.InvalidMnemonic, r'move 2'):
            cmp.parse_mnemonic('cmp1 e2e4 d2d4')

    def test_convert_uci(self):
        line = 'cmp1 e2e4 e7e5 g1f3 b8c6 f1b5'
        self.assertEqual(
            cmp.convert_mnemonic(line, 'uci'),
            'e2e4 e7e5 g1f3 b8c6 f1b5',
        )

    def test_convert_san(self):
        line = 'cmp1 e2e4 e7e5 g1f3 b8c6 f1b5'
        self.assertEqual(
            cmp.convert_mnemonic(line, 'san'),
            '1. e4 e5 2. Nf3 Nc6 3. Bb5',
        )

    def test_convert_pgn(self):
        line = 'cmp1 e2e4 e7e5 g1f3 b8c6 f1b5'
        pgn = cmp.convert_mnemonic(line, 'pgn')
        self.assertIn('[Event "CMP-1"]', pgn)
        self.assertIn('[Result "*"]', pgn)
        self.assertTrue(pgn.endswith('1. e4 e5 2. Nf3 Nc6 3. Bb5 *'))

    def test_checkmate_pgn_result(self):
        line = 'cmp1 e2e4 e7e5 d1h5 b8c6 f1c4 g8f6 h5f7'
        pgn = cmp.convert_mnemonic(line, 'pgn')
        self.assertIn('[Result "1-0"]', pgn)
        self.assertTrue(pgn.endswith('Qxf7# 1-0'))

    def test_san_castling_en_passant_and_promotion(self):
        line = (
            'cmp1 e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 '
            'b5a4 g8f6 e1g1'
        )
        self.assertTrue(cmp.convert_mnemonic(line, 'san').endswith('O-O'))

        line = 'cmp1 e2e4 a7a6 e4e5 d7d5 e5d6'
        self.assertTrue(cmp.convert_mnemonic(line, 'san').endswith('exd6'))

        line = (
            'cmp1 a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 '
            'a6b7 h3g2 b7a8q'
        )
        self.assertTrue(cmp.convert_mnemonic(line, 'san').endswith('bxa8=Q'))

    def test_restart_after_terminal_position(self):
        line = 'cmp1 e2e4 e7e5 d1h5 b8c6 f1c4 g8f6 h5f7 e2e4'
        self.assertTrue(cmp.check(line))
        self.assertEqual(
            cmp.convert_mnemonic(line, 'san'),
            '1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#\n1. e4',
        )
        pgn = cmp.convert_mnemonic(line, 'pgn')
        self.assertEqual(pgn.count('[Event "CMP-1"]'), 2)

    def test_vectors(self):
        path = os.path.join(ROOT, 'vectors.json')
        with open(path, 'r', encoding='utf-8') as handle:
            vectors = json.load(handle)

        self.assertEqual(vectors['protocol'], cmp.VERSION)

        for vector in vectors['valid']:
            with self.subTest(vector=vector['name']):
                self.assertTrue(cmp.check(vector['input']))
                self.assertEqual(
                    cmp.normalize(vector['input']),
                    vector['canonical'],
                )
                self.assertEqual(
                    cmp.convert_mnemonic(vector['input'], 'uci'),
                    vector['uci'],
                )
                self.assertEqual(
                    cmp.convert_mnemonic(vector['input'], 'san'),
                    vector['san'],
                )
                if 'pgn_result' in vector:
                    result = '[Result "%s"]' % vector['pgn_result']
                    self.assertIn(
                        result,
                        cmp.convert_mnemonic(vector['input'], 'pgn'),
                    )

        for vector in vectors['invalid']:
            with self.subTest(vector=vector['name']):
                self.assertFalse(cmp.check(vector['input']))
                with self.assertRaises(cmp.InvalidMnemonic):
                    cmp.parse_mnemonic(vector['input'])

    def test_cli_check_and_convert(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cmp.main(['check', 'cmp1', 'e2e4', 'e7e5'])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), 'valid')

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cmp.main([
                'convert', '--to', 'san', 'cmp1', 'e2e4', 'e7e5'
            ])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), '1. e4 e5')

    def test_cli_invalid_returns_nonzero(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = cmp.main(['check', 'cmp1', 'e2e5'])
        self.assertEqual(code, 1)
        self.assertIn('invalid:', stderr.getvalue())


class ChessEngineTests(unittest.TestCase):
    def perft(self, state, depth):
        if depth == 0:
            return 1

        total = 0
        for move in engine_legal_moves(state):
            total += self.perft(play(state, move), depth - 1)
        return total

    def test_start_position_perft(self):
        state = initial_state()
        self.assertEqual(self.perft(state, 1), 20)
        self.assertEqual(self.perft(state, 2), 400)
        self.assertEqual(self.perft(state, 3), 8902)


if __name__ == '__main__':
    unittest.main()
