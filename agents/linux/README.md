# Future Linux adapter

No Linux collector is implemented. Future work must define safe file selection,
symlink handling, file identity checks, permissions and locking before reusing
`agents.core` hashing and transport. Windows acquisition policies must not be
assumed portable. The existing Windows CLI remains the only collector.
