# Auto-install missing dependencies
import sys
import subprocess

def ensure_package(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        print(f"Missing dependency '{pkg}', installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# Ensure required packages
ensure_package("requests")
ensure_package("bs4", "bs4")
ensure_package("colorama")
# Add tqdm for progress bar
ensure_package("tqdm")

import requests
import time
import logging
import argparse
import csv
import os
import random
import signal
import sys
import re
from bs4 import BeautifulSoup
from datetime import datetime
import json
from colorama import init, Fore, Style
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Initialize colorama for terminal color support
init(autoreset=True)

# Output filenames
CSV_FILE = "scan_results.csv"
MD_FILE = "scan_results.md"
HTML_FILE = "scan_results.html"

DEFAULT_DELAY_MIN = 60
DEFAULT_DELAY_MAX = 180

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def signal_handler(sig, frame):
    print(Fore.RED + "\nScan interrupted by user.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def is_valid_domain(domain):
    # Improved regex for domain validation: allows subdomains and sub.sub.domains
    pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
    return re.match(pattern, domain) is not None

def read_domains(file_path):
    try:
        with open(file_path, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read input file '{file_path}': {e}")
        print(Fore.RED + f"Error reading input file '{file_path}': {e}")
        sys.exit(1)
    valid_domains = []
    for d in domains:
        if is_valid_domain(d):
            valid_domains.append(d)
        else:
            logging.warning(f"Invalid domain skipped: {d}")
            print(Fore.YELLOW + f"Skipping invalid domain: {d}")
    return valid_domains

def load_hosting_patterns(json_path=None):
    default_patterns = {
        "iq": [
            "Error 404 / Błąd 404",
            "https://www.iq.pl/pomoc/29/233",
            "jest utrzymywana na serwerach IQ PL",
            "wildinfo.iq.pl/main.css"
        ],
        "ovh": [
            "Hosted by OVH",
            "Welcome to OVH",
            "This domain name has been registered with Gandi.net",
            "ovh.com"
        ],
        "homepl": [
            "Strona utrzymywana na serwerach home.pl",
            "home.pl",
            "Błąd 404",
            "Serwis nie istnieje lub wygasł"
        ],
        "nazwa": [
            "Strona utrzymywana na serwerach nazwa.pl",
            "nazwa.pl",
            "Domena jest utrzymywana na serwerach nazwa.pl",
            "Domena została zarejestrowana w nazwa.pl"
        ],
        "gandi": [
            "This domain name has been registered with Gandi.net",
            "Gandi.net"
        ],
        "hetzner": [
            "Hetzner Online GmbH",
            "This domain is reserved",
            "Hetzner"
        ],
        "godaddy": [
            "This domain is parked",
            "GoDaddy.com, LLC",
            "GoDaddy",
            "Visit GoDaddy.com"
        ],
        "cloudflare": [
            "This domain is using Cloudflare",
            "cloudflare.com",
            "Error 1001 Ray ID"
        ],
        "google": [
            "Google Domains",
            "This domain has been registered at Google Domains",
            "domains.google"
        ],
        "microsoft": [
            "This domain is registered with Microsoft",
            "Azure App Service",
            "azurewebsites.net"
        ],
        "dreamhost": [
            "DreamHost",
            "Site Not Found",
            "The DreamHost customer who owns"
        ],
        "bluehost": [
            "Bluehost",
            "This domain is parked",
            "parked by Bluehost"
        ],
        "hostgator": [
            "HostGator",
            "This domain is parked",
            "parked by HostGator"
        ],
        "namecheap": [
            "This domain is registered at Namecheap",
            "Namecheap"
        ],
        "ionos": [
            "IONOS",
            "This domain has been registered with IONOS"
        ],
        "aws": [
            "Amazon Web Services",
            "aws.amazon.com",
            "NoSuchBucket"
        ],
        # Add more as needed...
    }
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(Fore.YELLOW + f"Warning: Failed to load hosting patterns from {json_path}: {e}")
    return default_patterns

def advanced_error_detection(content):
    # Placeholder for advanced heuristics (regex, HTML structure, ML, etc.)
    # Return a string category or None if not detected
    return None

def categorize_response(content, hosting_patterns):
    # Check for each hosting provider's error/parked page
    for provider, keywords in hosting_patterns.items():
        for keyword in keywords:
            if keyword in content:
                return f"{provider}_error"
    # Advanced heuristics
    adv = advanced_error_detection(content)
    if adv:
        return adv
    # If no hosting-specific error/parked page detected, check for generic error codes in content
    if "404" in content:
        return "custom_404"
    if "500" in content:
        return "custom_500"
    if "403" in content:
        return "custom_403"
    if "502" in content:
        return "custom_502"
    if "503" in content:
        return "custom_503"
    return "custom"

def scan_domain(domain, hosting_patterns, dry_run=False, retries=2, timeout=5):
    domain = domain.strip()
    urls_to_check = [f"https://{domain}", f"http://{domain}"] if not domain.startswith("http") else [domain]

    for url in urls_to_check:
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        if dry_run:
            logging.info(f"[DRY RUN] Would scan {url}")
            print(Fore.CYAN + f"[DRY RUN] {url}")
            return {"domain": domain, "status_code": None, "category": "dry_run"}

        attempt = 0
        while attempt <= retries:
            try:
                logging.info(f"Scanning {url} (attempt {attempt+1})")
                response = requests.get(url, timeout=timeout, headers=headers)
                content = response.text
                status_code = response.status_code

                logging.debug(f"Received status {status_code} for {url}")

                if 400 <= status_code < 600:
                    category = categorize_response(content, hosting_patterns)
                    logging.info(f"{domain} returned error {status_code} categorized as {category}")
                else:
                    category = "no_error"
                    logging.info(f"{domain} returned status {status_code} (no error)")

                color = Fore.RED if status_code >= 500 else Fore.YELLOW if status_code >= 400 else Fore.GREEN
                print(color + f"{domain}: {status_code} [{category}]")
                return {"domain": domain, "status_code": status_code, "category": category}

            except requests.RequestException as e:
                logging.warning(f"Request to {url} failed: {e}")
                if attempt < retries:
                    sleep_time = 2 ** attempt
                    print(Fore.MAGENTA + f"{domain}: Error ({e}), retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                attempt += 1
        print(Fore.MAGENTA + f"{domain}: Unreachable after {retries+1} attempts")
        logging.error(f"{domain} unreachable after {retries+1} attempts")
    return {"domain": domain, "status_code": None, "category": "unreachable"}

def write_csv(results, csv_file):
    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["domain", "status_code", "category"])
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Results written to CSV: {csv_file}")
    except Exception as e:
        logging.error(f"Failed to write CSV file '{csv_file}': {e}")
        print(Fore.RED + f"Error writing CSV file '{csv_file}': {e}")

def write_md(results, md_file):
    try:
        with open(md_file, 'w') as f:
            f.write("| Domain | Status Code | Category |\n")
            f.write("|--------|-------------|----------|\n")
            for r in results:
                f.write(f"| {r['domain']} | {r['status_code']} | {r['category']} |\n")
        logging.info(f"Results written to Markdown: {md_file}")
    except Exception as e:
        logging.error(f"Failed to write Markdown file '{md_file}': {e}")
        print(Fore.RED + f"Error writing Markdown file '{md_file}': {e}")

def write_html(results, html_file):
    try:
        with open(html_file, 'w') as f:
            f.write("<html><head><title>Scan Results</title></head><body><table border='1'>")
            f.write("<tr><th>Domain</th><th>Status Code</th><th>Category</th></tr>")
            for r in results:
                f.write(f"<tr><td>{r['domain']}</td><td>{r['status_code']}</td><td>{r['category']}</td></tr>")
            f.write("</table></body></html>")
        logging.info(f"Results written to HTML: {html_file}")
    except Exception as e:
        logging.error(f"Failed to write HTML file '{html_file}': {e}")
        print(Fore.RED + f"Error writing HTML file '{html_file}': {e}")

def write_json(results, json_file):
    try:
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Results written to JSON: {json_file}")
    except Exception as e:
        logging.error(f"Failed to write JSON file '{json_file}': {e}")
        print(Fore.RED + f"Error writing JSON file '{json_file}': {e}")

def summarize_results(results, summary_file=None):
    summary = Counter(r['category'] for r in results)
    print(Style.BRIGHT + "\nSummary:")
    lines = []
    for category, count in summary.items():
        color = {
            "no_error": Fore.GREEN,
            "iq_error": Fore.YELLOW,
            "iq_parked": Fore.BLUE,
            "custom": Fore.CYAN,
            "custom_404": Fore.YELLOW,
            "custom_500": Fore.RED,
            "custom_403": Fore.MAGENTA,
            "custom_502": Fore.MAGENTA,
            "custom_503": Fore.MAGENTA,
            "unreachable": Fore.MAGENTA,
            "dry_run": Fore.CYAN
        }.get(category, Fore.WHITE)
        line = f"{category}: {count}"
        print(color + line)
        logging.info(f"Summary: {line}")
        lines.append(line)
    if summary_file:
        try:
            with open(summary_file, "w") as f:
                f.write("\n".join(lines))
        except Exception as e:
            logging.error(f"Failed to write summary file: {e}")

def save_progress(progress_file, results):
    try:
        with open(progress_file, 'w') as f:
            json.dump(results, f)
    except Exception as e:
        logging.error(f"Failed to save progress: {e}")

def load_progress(progress_file):
    try:
        with open(progress_file, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def format_seconds(seconds):
    # Helper to format seconds as H:M:S
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def main():
    parser = argparse.ArgumentParser(description="Scan domains for 4xx/5xx errors and detect error/parked pages for many hostings.")
    parser.add_argument('--dry-run', action='store_true', help='Simulate run without making any HTTP requests')
    parser.add_argument('--input', default='domains.txt', help='Input file with list of domains')
    parser.add_argument('--csv', default=CSV_FILE, help='Output CSV file path')
    parser.add_argument('--md', default=MD_FILE, help='Output Markdown file path')
    parser.add_argument('--html', default=HTML_FILE, help='Output HTML file path')
    parser.add_argument('--delay-min', type=int, default=DEFAULT_DELAY_MIN, help='Minimum delay between requests (seconds)')
    parser.add_argument('--delay-max', type=int, default=DEFAULT_DELAY_MAX, help='Maximum delay between requests (seconds)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set log level')
    parser.add_argument('--patterns', default=None, help='Path to JSON file with hosting error/parked page patterns')
    parser.add_argument('--log-console', action='store_true', help='Also log to console')
    parser.add_argument('--threads', type=int, default=1, help='Number of parallel threads (default: 1)')
    parser.add_argument('--no-delay', action='store_true', help='Skip delay between requests')
    parser.add_argument('--only-unscanned', action='store_true', help='Only scan domains not present in previous results')
    parser.add_argument('--errors-only', action='store_true', help='Only output domains with errors (not no_error)')
    parser.add_argument('--max-domains', type=int, default=None, help='Limit the number of domains to scan')
    parser.add_argument('--json', default=None, help='Output JSON file path')
    parser.add_argument('--timeout', type=int, default=5, help='Timeout for HTTP requests (seconds)')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for failed requests')
    args = parser.parse_args()

    # Load hosting patterns
    hosting_patterns = load_hosting_patterns(args.patterns)

    # Create a timestamped results directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = f"scan_results_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    # Update output file paths to be inside the results directory
    csv_path = os.path.join(results_dir, os.path.basename(args.csv))
    md_path = os.path.join(results_dir, os.path.basename(args.md))
    html_path = os.path.join(results_dir, os.path.basename(args.html))
    progress_file = os.path.join(results_dir, "progress.json")
    summary_path = os.path.join(results_dir, "summary.txt")

    # Update log file to be inside the results directory
    log_filename = os.path.join(results_dir, f"scan_log_{timestamp}.log")
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(filename=log_filename, level=getattr(logging, args.log_level),
                        format='%(asctime)s - %(levelname)s - %(message)s')
    if args.log_console:
        console = logging.StreamHandler()
        console.setLevel(getattr(logging, args.log_level))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

    domains = read_domains(args.input)

    # Resume logic
    results = []
    already_scanned = set()
    if os.path.exists(progress_file):
        print(Fore.YELLOW + f"Found progress file: {progress_file}")
        choice = input("Resume previous scan? (y/n): ").strip().lower()
        if choice == "y":
            results = load_progress(progress_file)
            already_scanned = set(r['domain'] for r in results)
            print(Fore.YELLOW + f"Resuming scan. {len(already_scanned)} domains already scanned.")
        else:
            print(Fore.YELLOW + "Starting a new scan. Previous progress will be overwritten.")

    # --- Only scan unscanned domains if requested ---
    if args.only_unscanned:
        domains_to_scan = [d for d in domains if d not in already_scanned]
    else:
        domains_to_scan = domains

    # --- Limit max domains if requested ---
    if args.max_domains is not None:
        domains_to_scan = domains_to_scan[:args.max_domains]

    num_domains = len(domains_to_scan)
    avg_delay = (args.delay_min + args.delay_max) / 2
    threads = max(1, args.threads)
    # Only apply delay if not dry-run and not --no-delay
    if not args.dry_run and not args.no_delay:
        estimated_total_seconds = (num_domains * avg_delay) / threads
        print(Fore.CYAN + f"Estimated scan time for {num_domains} domains with {threads} thread(s): {format_seconds(estimated_total_seconds)}")
    else:
        print(Fore.CYAN + f"Estimated scan time: <1s (dry-run or no-delay mode)")

    interrupted = False

    def handle_interrupt(sig, frame):
        nonlocal interrupted
        interrupted = True
        print(Fore.RED + "\nScan interrupted by user. Saving progress...")
        save_progress(progress_file, results)
        print(Fore.YELLOW + f"Progress saved to {progress_file}. You can resume later.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    def scan_and_save(domain):
        if domain in already_scanned:
            return None
        result = scan_domain(domain, hosting_patterns, dry_run=args.dry_run, retries=args.retries, timeout=args.timeout)
        save_progress(progress_file, results + [result])
        return result

    # --- Progress bar setup ---
    progress_iter = tqdm(domains_to_scan, desc="Scanning", unit="domain")

    try:
        if args.threads > 1:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                future_to_domain = {executor.submit(scan_and_save, domain): domain for domain in domains_to_scan if domain not in already_scanned}
                for future in tqdm(as_completed(future_to_domain), total=len(future_to_domain), desc="Scanning", unit="domain"):
                    result = future.result()
                    if result:
                        results.append(result)
        else:
            for domain in progress_iter:
                if domain in already_scanned:
                    continue
                result = scan_domain(domain, hosting_patterns, dry_run=args.dry_run, retries=args.retries, timeout=args.timeout)
                results.append(result)
                save_progress(progress_file, results)
                if not args.dry_run and not args.no_delay:
                    delay = random.randint(args.delay_min, args.delay_max)
                    print(Fore.WHITE + f"Sleeping for {delay} seconds before next request...")
                    logging.debug(f"Sleeping for {delay} seconds before next request")
                    time.sleep(delay)
    except KeyboardInterrupt:
        handle_interrupt(None, None)

    # --- Filter errors only if requested ---
    output_results = results
    if args.errors_only:
        output_results = [r for r in results if r['category'] != "no_error"]

    write_csv(output_results, csv_path)
    write_md(output_results, md_path)
    write_html(output_results, html_path)
    if args.json:
        write_json(output_results, os.path.join(results_dir, os.path.basename(args.json)))
    summarize_results(output_results, summary_file=summary_path)

    # Remove progress file after successful completion
    if os.path.exists(progress_file):
        os.remove(progress_file)

    logging.info("Scan completed. Results saved in CSV, Markdown, and HTML formats.")

if __name__ == '__main__':
    main()
