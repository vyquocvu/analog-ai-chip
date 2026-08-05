import json
import tempfile

from analog_llm.tokenizer import GPT2Tokenizer, _bytes_to_unicode


def _write_tiny(tmp):
    b2u = _bytes_to_unicode()
    vocab = {ch: i for i, ch in enumerate(b2u.values())}
    # add a learned merge token "ab" (byte tokens "a", "b" are literal ASCII)
    vocab["ab"] = 0x100
    with open(tmp + "/vocab.json", "w") as fh:
        json.dump(vocab, fh)
    with open(tmp + "/merges.txt", "w") as fh:
        fh.write("#version 0.2\n`` ``\na b\n")
    return tmp


def test_roundtrip_basic():
    with tempfile.TemporaryDirectory() as tmp:
        _write_tiny(tmp)
        tk = GPT2Tokenizer(tmp + "/vocab.json", tmp + "/merges.txt")
        for text in ["hello", "a line!", "Ø unicode", " x "]:
            assert tk.decode(tk.encode(text)) == text


def test_learned_merge_applied():
    with tempfile.TemporaryDirectory() as tmp:
        _write_tiny(tmp)
        tk = GPT2Tokenizer(tmp + "/vocab.json", tmp + "/merges.txt")
        ids = tk.encode("c ab ab")
        # the "ab" span merges into the single learned token 0x100
        assert 0x100 in ids
