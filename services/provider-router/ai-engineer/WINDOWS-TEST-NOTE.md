# Windows test exception

Upstream file:

```text
server/src/__tests__/db/hardening.test.ts
```

contains two assertions that inspect POSIX permission mode bits after `chmod`.
Windows NTFS uses Access Control Lists (ACLs), and Node.js does not expose those
ACLs through the Unix `mode & 0o077` assertion used by this test.

For the Windows installation:

- Production source is unchanged.
- The upstream test file is unchanged.
- All other server tests are executed.
- Windows ACLs for `.env` and the persistent data directory are captured in
  `ai-engineer/windows-validation.json`.
- ACL hardening, if required, must be performed as a separate explicit step
  because changing access control can lock a user out of files.