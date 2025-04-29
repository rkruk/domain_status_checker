# Domain Status Checker

A script to scan a list of domains for HTTP errors (4xx/5xx), with detection for hosting providers' error/parked pages, as well as generic error codes.

## Features

- Scans domains for HTTP status codes.
- Detects error/parked pages for IQ.PL, OVH, home.pl, nazwa.pl, Gandi, Hetzner, GoDaddy, Cloudflare, Google Domains, Microsoft, DreamHost, Bluehost, HostGator, Namecheap, IONOS, AWS, and more.
- Detects generic error codes (404, 500, 403, 502, 503) even if not matched to a known provider.
- Supports dry-run mode (no HTTP requests).
- Randomizes User-Agent for each request.
- Retries failed requests with exponential backoff.
- Outputs results in CSV, Markdown, and HTML formats.
- Prints a colorized summary to the terminal and writes it to a summary file.
- Handles Ctrl+C gracefully and supports resuming scans.
- Handles exceptions when reading/writing files.
- Skips and warns about invalid domains.
- Allows output file paths as arguments.
- Adjustable logging level for more detailed output.
- **Automatically checks for and installs missing dependencies** (`requests`, `beautifulsoup4`, `colorama`).
- **Resume support:** If interrupted (Ctrl+C), the script saves progress and allows you to resume or start over on the next run.
- **Each scan is saved in a timestamped results folder** to avoid overwriting previous results.
- **Parallelization:** Use multiple threads for faster scanning (`--threads`).
- **Externalized hosting patterns:** Use `--patterns` to provide a JSON file with custom error/parked page patterns.
- **Logging to console:** Use `--log-console` to also log to the console.
- **Unit tests:** Provided for core functions.

## Usage

```bash
python domain_status_checker.py --input domains.txt [--dry-run] [--delay-min N] [--delay-max N] [--csv FILE] [--md FILE] [--html FILE] [--log-level LEVEL] [--threads N] [--patterns FILE] [--log-console]
```

### Arguments

- `--input`: Path to the input file containing domains (default: `domains.txt`).
- `--dry-run`: Simulate the scan without making HTTP requests.
- `--delay-min`: Minimum delay between requests in seconds (default: 60).
- `--delay-max`: Maximum delay between requests in seconds (default: 180).
- `--csv`: Output CSV file path (default: `scan_results.csv`).
- `--md`: Output Markdown file path (default: `scan_results.md`).
- `--html`: Output HTML file path (default: `scan_results.html`).
- `--log-level`: Set log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`; default: `INFO`).
- `--threads`: Number of parallel threads for scanning (default: 1).
- `--patterns`: Path to a JSON file with custom hosting error/parked page patterns.
- `--log-console`: Also log to the console.

## Output

- All results and logs are saved in a new folder named `scan_results_<timestamp>` for each scan.
- CSV file with scan results (default: `scan_results.csv`).
- Markdown table with scan results (default: `scan_results.md`).
- HTML table with scan results (default: `scan_results.html`).
- Log file: `scan_log_<timestamp>.log`.
- Progress file: `progress.json` (used for resuming scans; deleted after successful completion).
- Summary file: `summary.txt` (with a summary of categories and counts).

## Resume Functionality

- If the scan is interrupted (e.g., by pressing Ctrl+C), progress is saved automatically.
- On the next run, if a progress file is found, you will be prompted to resume the previous scan or start over.
- Already scanned domains are skipped when resuming.

## Parallelization

- Use the `--threads N` argument to scan domains in parallel (e.g., `--threads 4`).
- Be careful with rate-limiting and server bans when using multiple threads.

## Example

```
| Domain         | Status Code | Category      |
|----------------|-------------|--------------|
| example.com    | 200         | no_error      |
| test.com       | 404         | iq_error      |
| parked.com     | 404         | iq_parked     |
| custom.com     | 404         | custom_404    |
| another.com    | 503         | custom_503    |
| godaddy.com    | 404         | godaddy_error |
| bad-domain.com | None        | unreachable   |
```

## Categories

- `no_error`: No HTTP error detected.
- `<provider>_error`: Error/parked page detected for a known hosting provider (e.g., `iq_error`, `ovh_error`, `godaddy_error`, etc.).
- `custom_404`, `custom_500`, `custom_403`, `custom_502`, `custom_503`: Generic error code detected in the page content, not matching a known provider.
- `custom`: Custom error page detected (no known provider or error code matched).
- `unreachable`: Domain could not be reached.
- `dry_run`: Dry run mode (no request made).

### What does `503 [custom]` mean?

- `503` is the HTTP status code ("Service Unavailable").
- `[custom]` means the error page did not match any known provider's pattern or generic error code in the content.
- This usually indicates a generic or custom error page, not a standard hosting provider's branded error/parked page.

## Domain Validation

Domains in the input file are validated using a regular expression that allows subdomains and multi-level domains. Invalid domains are skipped with a warning.

## Requirements

- Python 3.x

**No manual installation of dependencies is required.**  
The script will automatically check for and install `requests`, `beautifulsoup4`, and `colorama` if they are missing.

## Unit Tests

Basic unit tests for domain validation and error categorization are provided in `test_error_checker.py`:

```bash
python -m unittest test_error_checker.py
```

## License

Apache 2 License
