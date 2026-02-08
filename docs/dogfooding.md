## Dogfooding

CocoSearch uses CocoSearch to index its own codebase. This demonstrates real-world usage and lets you explore the implementation.

### Indexing the Codebase

Index the CocoSearch source code:

```bash
uvx cocosearch index . --name self
```

### Verifying Indexing

Check the index stats to confirm everything was indexed:

```bash
uvx cocosearch stats self --pretty
```

### Example Searches

**Find embedding implementation:**

```bash
uvx cocosearch search "how does embedding work" --index self --pretty
```

**Search for database operations:**

```bash
uvx cocosearch search "database connection handling" --index self --pretty
```

**Find Docker setup (filtered by language):**

```bash
uvx cocosearch search "docker setup" --index self --lang bash --pretty
```

**Explore configuration system:**

```bash
uvx cocosearch search "config file discovery" --index self --pretty
```
