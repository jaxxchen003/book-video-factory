# Next Renderer Gate

Phase 3C permits one bounded new-renderer experiment behind the existing renderer contract. It does
not authorize a production switch.

The experiment must consume the frozen Release Snapshot/RenderRequest, declare capabilities before
execution, write Attempt/Result evidence atomically, produce an independently probed output, and
hand off Post-QC outside the renderer. The Phase 3C fixture and Legacy V4 output remain the semantic
oracle. It must fail closed on unsupported Request fields and must not add Provider, Web, batch, or
audio-finalizer scope.

## Single next recommendation

Create a contract-conformance skeleton for exactly one new renderer and make it pass the existing
frozen-fixture validation before implementing additional visual behavior.
