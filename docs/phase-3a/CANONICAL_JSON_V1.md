# canonical-json-v1

## Encoding contract

Canonical bytes are produced with:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

The output has no BOM and no trailing newline.

## Normalization

- Enum values become their stable string tokens.
- Frozen dataclasses become ordinary JSON objects.
- `Path`/`PurePath` becomes a portable `/` string.
- Tuple/list becomes a JSON array.
- Mapping keys must be strings.
- `None`, string, integer, and Boolean are accepted.
- All floats are rejected, including finite floats, NaN, and positive/negative Infinity.
- Unsupported runtime objects are rejected rather than stringified.

Rejecting every float avoids platform- and producer-specific float spellings. Time is integer tick;
frame rate is a numerator/denominator pair.

## Golden vector

```text
Input semantic object: {"b": 1, "a": "中"}
Canonical UTF-8 text:  {"a":"中","b":1}
SHA-256:               d8158d9a7acf211407d1309876015fc6e69f13b7dd8126a571e429ddce565911
```

The golden vector, Unicode bytes, absence of BOM/newline, key-order independence, tuple/enum/path
normalization, and float rejection are covered by unit tests.
