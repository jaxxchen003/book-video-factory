# Portable Path Implementation

## Persistent form

Persistent references contain only:

```json
{"root": "project", "path": "assets/audio/voice.wav"}
```

Physical paths are injected through `RootResolver` and are never serialized or included in the
Request hash.

## Input normalization and rejection

Allowed normalization:

```text
assets\audio\voice.wav -> assets/audio/voice.wav
```

Rejected before resolution:

- POSIX absolute paths;
- Windows drive-qualified paths, including drive-relative forms;
- UNC paths;
- empty path or empty segment;
- `.` and `..` segments;
- NUL;
- undeclared logical root.

Unicode components are preserved exactly in persistent JSON.

## Root resolution

`RootResolver` expands and resolves the physical root, joins portable components, calls
`Path.resolve(strict=False)`, and then requires `resolved.relative_to(root)` to succeed. It does not
use string-prefix comparison. Existing symlinks/reparse points are therefore resolved before the
containment test. Output resolution additionally rejects unauthorized roots and symlinked output
ancestors.

## Test result

The Windows run covered relative normalization, Unicode, drive, UNC, traversal, empty segments,
NUL, undeclared/read-only roots, existing file resolution, and an actual directory symlink escape.
Symlink creation succeeded in this environment, so the escape test executed and passed rather than
being skipped.
