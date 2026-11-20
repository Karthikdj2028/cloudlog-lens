# CloudLog Lens Desktop

Reserved for the Tauri v2 desktop host and Python API sidecar integration.

The Rust toolchain and Tauri dependencies are intentionally deferred to the desktop milestone.
The desktop shell must reuse the shared frontend and keep the local API bound to loopback with
an ephemeral authentication token.
