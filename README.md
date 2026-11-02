# Smart File Compression Tool using Huffman Coding

A GUI-based file compression and decompression application built with **Python and Tkinter** for the Design and Analysis of Algorithms (DAA) Assignment 2.

**Student:** Mathew Manoj  
**Roll No.:** 23  
**Algorithm:** Huffman Coding (Greedy Method)

## Overview

Huffman Coding is a lossless compression algorithm. It assigns shorter binary codes to frequently occurring byte values and longer codes to less frequent values. The application builds a Huffman tree using a min-priority queue and uses the tree to encode and decode files.

## Features

- Enter text directly or open a file.
- Calculate byte frequencies.
- Construct and visualize the Huffman binary tree.
- Display generated prefix-free Huffman codes.
- Step through greedy tree construction.
- Compress input into a `.huf` archive.
- Decompress `.huf` archives to restore original bytes.
- Display input size, archive size, and archive size change.

## Project Structure

```text
Mathew_Manoj_Huffman_Compression/
├── huffman_compressor.py   # Main GUI and Huffman algorithm
├── test_huffman.py         # Automated algorithm tests
├── requirements.txt        # External dependencies (none required)
├── README.md               # Project documentation
└── .gitignore              # Files excluded from Git
```

## Requirements

- Python 3.10 or later
- Tkinter (included with most standard Windows Python installations)

No third-party Python packages are required.

## Run the Application

```bash
python huffman_compressor.py
```

## How to Use

1. Type text into the input area or select **Open File**.
2. Select **Compress Text** to build the Huffman tree and inspect the code table.
3. Use **Next Step** and **Previous** to inspect greedy merge operations.
4. Select **Compress File** to save a `.huf` archive.
5. Select **Decompress .huf** to restore a compressed archive.

> Small files may produce a larger archive because the archive stores frequency metadata and header information. This is normal compression overhead.

## Algorithm

1. Count the frequency of each byte in the input.
2. Insert each distinct byte into a min-priority queue as a leaf node.
3. Remove the two nodes with the lowest frequencies.
4. Combine them into a parent node whose frequency is their sum.
5. Insert the parent back into the priority queue.
6. Repeat until one tree remains.
7. Traverse left edges as `0` and right edges as `1` to generate prefix-free codes.
8. Encode the input bytes using the generated codes.

## Complexity Analysis

Let `n` be the number of input bytes and `k` the number of distinct byte values (`k ≤ 256`).

| Operation | Time complexity |
|---|---:|
| Frequency counting | `O(n)` |
| Huffman tree construction | `O(k log k)` |
| Code generation | `O(k)` |
| Encoding | `O(n)` |
| Decoding | `O(n)` |

Overall compression time: **`O(n + k log k)`**.

Auxiliary space: **`O(k)`** for the frequency table, heap, tree, and code table. Including the output buffer, working space is **`O(k + n)`**.

## Run Automated Tests

```bash
python -m unittest -v
```

The tests cover BANANA, single-symbol input, two-symbol input, empty input, all 256 byte values, whitespace/newlines, binary data, and invalid archive headers.

## Limitations

- Huffman coding is compression, not encryption.
- Small inputs may grow because of metadata overhead.
- The algorithm does not guarantee every file will become smaller.

## Academic Use

This project demonstrates the **Greedy Method**, min-priority queues, binary trees, prefix-free codes, lossless encoding/decoding, and asymptotic complexity analysis.
