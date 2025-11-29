# Contributing

Thanks for contributing! A few guidelines to make contributions smooth.

Commit messages
- Use conventional commits where possible: `feat:`, `fix:`, `chore:`, `docs:`.

Code style
- JavaScript/TypeScript: follow existing project conventions (Prettier/ESLint config if present).
- Python: follow PEP8 where reasonable; keep functions small and testable.

Running tests
- Smart contract tests: `npx hardhat test`
- Backend tests (if added): `cd backend && npm test`

Adding changes
- Open a pull request, include a short description, and reference relevant issues.

Security
- Do NOT commit secrets into the repository. Use `.env.example` for variable names only.
