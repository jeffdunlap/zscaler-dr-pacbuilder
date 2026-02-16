# zscaler-dr-pacbuilder

A Python tool that generates [proxy auto-config (PAC)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Proxy_servers_and_tunneling/Proxy_Auto-Configuration_PAC_file) files for **Zscaler ZIA Disaster Recovery mode**.

During a Zscaler ZIA outage, traffic is handled by the DR PAC file instead of the Zscaler cloud. This tool lets you maintain a simple text-based allow list of domains and automatically generates a valid `proxy.pac` file that:

- Grants **DIRECT** internet access to domains on your allow list (and all their subdomains)
- **Blocks** everything else by routing it to `PROXY 127.0.0.1:1`
- Works alongside Zscaler's built-in Pre-Selected Destinations list

## How It Works

```
allow-list.txt ──► pacbuilder.py ──► proxy.pac
                       │
                       ├── Reads domains from allow-list.txt
                       ├── Fetches Zscaler's pre-selected destinations (drdb.txt)
                       ├── Removes duplicates already covered by Zscaler
                       ├── Renders the Jinja2 template (templates/proxy.pac.j2)
                       ├── Validates the output PAC file for syntax errors
                       └── Writes the final proxy.pac
```

The generated `proxy.pac` file contains a standard `FindProxyForURL()` function. When a browser or OS is configured to use this PAC file, every URL request is evaluated:

1. The requested hostname is checked against the `allowed` array
2. If the domain (or any parent domain) matches, traffic goes **DIRECT** to the internet
3. If there is no match, traffic is sent to `PROXY 127.0.0.1:1`, which effectively blocks it

## Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Node.js** (optional, for enhanced PAC file JavaScript syntax validation)

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/jeffdunlap/zscaler-dr-pacbuilder.git
   cd zscaler-dr-pacbuilder
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   This installs [Jinja2](https://jinja.palletsprojects.com/), the only external dependency.

3. **Verify the setup:**

   ```bash
   python3 pacbuilder.py --skip-dedup
   ```

   You should see output like:

   ```
   Loaded 1 domain(s) from allow-list.txt
   PAC file passed Node.js syntax validation
   Generated proxy.pac with 1 domain(s)
   ```

## Adding Domains to the Allow List

The allow list lives in `allow-list.txt`. To allow a new domain through the PAC file:

1. **Open `allow-list.txt`** in any text editor:

   ```bash
   nano allow-list.txt
   ```

2. **Add one domain per line.** Use apex (root) domains only — subdomain matching is automatic. For example, adding `example.com` will also allow `www.example.com`, `api.example.com`, etc.

   ```
   # Existing entries
   whatismyip.com

   # Add new domains below
   example.com
   myapp.internal.io
   ```

   **Rules for the allow list:**
   - One domain per line
   - Lines starting with `#` are treated as comments
   - Blank lines are ignored
   - Apex domains only (no `www.` prefix needed)
   - No protocol prefixes (write `example.com`, not `https://example.com`)
   - Invalid entries are warned and skipped automatically

3. **Regenerate the PAC file:**

   ```bash
   python3 pacbuilder.py
   ```

4. **Review the output.** The tool will report:
   - How many domains were loaded
   - Any domains removed because they already exist in Zscaler's pre-selected list
   - Whether the PAC file passed validation
   - The final domain count written to `proxy.pac`

5. **Deploy `proxy.pac`** to your web server or PAC file hosting location.

## Usage

### Basic usage (recommended)

```bash
python3 pacbuilder.py
```

This runs the full pipeline: parse the allow list, deduplicate against Zscaler's pre-selected destinations, render the template, validate, and write `proxy.pac`.

### Skip Zscaler deduplication

If the Zscaler drdb.txt URL is unreachable from your network, or you want to skip the check:

```bash
python3 pacbuilder.py --skip-dedup
```

### Skip PAC validation

```bash
python3 pacbuilder.py --skip-validation
```

### Custom file paths

```bash
python3 pacbuilder.py --allow-list /path/to/my-domains.txt --output /var/www/proxy.pac
```

### All options

```
usage: pacbuilder.py [-h] [--allow-list ALLOW_LIST] [--output OUTPUT]
                     [--template-dir TEMPLATE_DIR] [--skip-dedup]
                     [--skip-validation]

Generate proxy.pac for Zscaler ZIA Disaster Recovery mode.

options:
  -h, --help                 show this help message and exit
  --allow-list ALLOW_LIST    Path to the domain allow list (default: allow-list.txt)
  --output OUTPUT            Output path for the generated PAC file (default: proxy.pac)
  --template-dir TEMPLATE_DIR
                             Directory containing proxy.pac.j2 (default: templates/)
  --skip-dedup               Skip deduplication against Zscaler pre-selected destinations
  --skip-validation          Skip PAC file syntax validation
```

## Zscaler Deduplication

Zscaler maintains a pre-selected destinations list at their CDN that contains domains already allowed during DR mode. By default, `pacbuilder.py` fetches this list and removes any domains from your allow list that are already covered, keeping your PAC file clean and avoiding redundancy.

If a domain you add is removed during deduplication, the tool will tell you:

```
Removed 1 domain(s) already in Zscaler pre-selected list: example.com
```

This means Zscaler already allows that domain during DR — no need to include it in your custom PAC file.

If the Zscaler list cannot be fetched (network issues, firewall, etc.), the tool warns you and continues without deduplication.

## PAC File Validation

The generated PAC file is validated in two ways:

1. **Structural checks** — Confirms the output contains the required `FindProxyForURL` function, a `DIRECT` return, and a `PROXY` return
2. **JavaScript syntax check** — If Node.js is installed, the PAC file is parsed through Node to catch any JavaScript syntax errors

If Node.js is not available, only structural checks are performed. Install Node.js for the most thorough validation.

## Running Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

The test suite covers allow-list parsing, domain validation, Zscaler deduplication, template rendering, and PAC syntax validation.

## Project Structure

```
.
├── README.md              # This file
├── CLAUDE.md              # AI assistant guidance
├── LICENSE                # GNU AGPL v3
├── TODO.md                # Task tracking
├── allow-list.txt         # Domain allow list (you edit this)
├── pacbuilder.py          # Main application
├── proxy.pac              # Generated output (do not edit manually)
├── requirements.txt       # Python dependencies
├── templates/
│   └── proxy.pac.j2       # Jinja2 template for PAC file
└── tests/
    └── test_pacbuilder.py  # Test suite
```

## Example

Given this `allow-list.txt`:

```
# Business-critical applications
whatismyip.com
salesforce.com
office365.com

# Internal tools
mycompany.com
```

Running `python3 pacbuilder.py --skip-dedup` generates a `proxy.pac` containing:

```javascript
function FindProxyForURL(url, host) {
    // Zscaler ZIA Disaster Recovery - Custom PAC File
    // ...
    // Domain count: 4

    host = host.toLowerCase();

    var allowed = [
      "mycompany.com",
      "office365.com",
      "salesforce.com",
      "whatismyip.com"
    ];

    for (var i = 0; i < allowed.length; i++) {
        if (host === allowed[i] || dnsDomainIs(host, "." + allowed[i])) {
            return "DIRECT";
        }
    }

    return "PROXY 127.0.0.1:1";
}
```

With this PAC file active:
- `salesforce.com` and `app.salesforce.com` → **DIRECT** (allowed)
- `gmail.com` → **BLOCKED** (not on the list)

## License

[GNU Affero General Public License v3.0](LICENSE)
