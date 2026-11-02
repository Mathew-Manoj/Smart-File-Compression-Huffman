import unittest

from huffman_compressor import compress_bytes, decompress_bytes


class HuffmanRoundTripTests(unittest.TestCase):
    def assert_round_trip(self, original):
        archive, _tree, _codes, _steps = compress_bytes(original)
        self.assertEqual(decompress_bytes(archive), original)

    def test_banana(self):
        self.assert_round_trip(b"BANANA")

    def test_single_symbol(self):
        self.assert_round_trip(b"AAAAAA")

    def test_two_symbols(self):
        self.assert_round_trip(b"AB")

    def test_empty_input(self):
        self.assert_round_trip(b"")

    def test_all_byte_values(self):
        self.assert_round_trip(bytes(range(256)))

    def test_whitespace_and_newlines(self):
        self.assert_round_trip(b"line one\nline two\twith spaces  ")

    def test_repeated_binary_data(self):
        self.assert_round_trip(bytes([0, 255, 0, 128, 255, 0]) * 50)

    def test_invalid_archive_header(self):
        with self.assertRaises(ValueError):
            decompress_bytes(b"NOTHUF")


if __name__ == "__main__":
    unittest.main()
