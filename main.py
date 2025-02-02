import csv
import os
import re
import time
import random
import subprocess
from datetime import datetime, timedelta
from playwright.sync_api import Playwright, sync_playwright
from playwright.async_api import async_playwright
from playwright.sync_api import expect
from faker import Faker
import asyncio
from undetected_playwright import stealth_sync

def escape_latex(text):
    """Escape LaTeX special characters."""
    return text.replace("#", "\\#")

def generate_random_receipt():
    """Generate random receipt details."""
    tc_number = escape_latex(f"TC# {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}")
    st_number = escape_latex(f"ST# {random.randint(1000, 9999)} OP# {random.randint(1000, 9999)} TE# {random.randint(1, 20)} TR# {random.randint(1000, 9999)}")
    random_date = (datetime.now() - timedelta(days=random.randint(0, 15))).strftime("%m/%d/%y %H:%M:%S")
    amex_number = escape_latex(f"{random.randint(1000, 9999)}")

    # Item names and numbers
    items_dict = {
        "OILSPRAY": "002639599991 F",
        "PLSBY ELF": "001800011925 F",
        "BEEF RIBEYE": "026039400000 F",
        "CHILL 12PK": "004900055539 F",
        "CAKE": "007432309524 F",
        "B J ICECRM": "007684040007 F",
        "GV HF HF": "060538818715 F",
        "GV CK MJ 8Z": "007874203972 F"
    }

    # Fixed MMZ Lemonade
    # Make a matrix for sporte packages (6-packs, 2-liters)
    fixed_item = ("MMZ LEMONADE", "002500012052 F", random.uniform(2.50,4.50))

    # Randomly select 4 items excluding MMZ Lemonade
    selected_items = random.sample(list(items_dict.items()), 4)

    # Generate random prices for selected items
    items_with_prices = [(name, number, round(random.uniform(10.0, 30.0), 2)) for name, number in selected_items]
    
    # changing variable for spacing when subtotal is over 99.99 
    # Combine fixed MMZ Lemonade with the random items 
    # Take sporte out of items and add underneath to fix 3 decimal spacing
    items = items_with_prices[:2] + [fixed_item] + items_with_prices[2:]

    subtotal = round(sum(price for _, _, price in items), 2)
    tax1 = round(0.07 * subtotal, 2)
    total = round(subtotal + tax1, 2)

    return tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total

def create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, logo_path, barcode_path):
    """Create LaTeX receipt."""
    items_tabbed = r"""
    \begin{tabbing}
        \hspace{2.5cm} \= \hspace{3.7cm} \= \kill
"""
    for name, number, price in items:
        items_tabbed += f"        \\textbf{{{name}}} \\> \\textbf{{{number}}} \\> \\textbf{{{price:.2f}}}\\\\\n"
    items_tabbed += r"    \end{tabbing}"

    receipt_template = r"""
\documentclass{article}
\usepackage{geometry}
\geometry{paperwidth=100mm, paperheight=150mm, left=5mm, top=5mm, right=5mm, bottom=5mm}
\usepackage{courier}
\renewcommand{\familydefault}{\ttdefault}
\usepackage{array}
\usepackage{graphicx}
\usepackage{multicol}
\usepackage{xcolor}
\pagecolor{white}
\usepackage{adjustbox}

\begin{document}
\pagestyle{empty}

\newcommand{\receiptfontsize}{\fontsize{10}{9}\selectfont}
\receiptfontsize

\begin{center}
    \includegraphics[width=\linewidth]{""" + logo_path + r"""} % Walmart logo
    \textbf{WAL*MART}\\
    \textbf{33062990 Mgr. MIRANDA}\\
    \textbf{905 SINGLETARY DR}\\
    \textbf{STREETSBORO, OH}\\
    \textbf{""" + st_number + r"""}\\
    
    \vspace{1mm}
""" + items_tabbed + r"""
    \vspace{-9mm}
    \hspace{2.5cm}\begin{tabbing}
        \hspace{2cm} \= \hspace{2.4cm} \= \kill
        \textbf{\hspace{4cm}SUBTOTAL} \> \textbf{\hspace{4.3cm} """ + str(subtotal) + r"""} \\
        \textbf{\hspace{2.5cm}TAX} \hspace{-0.25mm} \textbf{1} \> \textbf{\hspace{2.5cm}7\%} \> \textbf{\hspace{1.90cm} """ + str(tax1) + r"""} \\
        \textbf{\hspace{2.5cm}TAX 12} \> \textbf{\hspace{2.5cm}0\%} \> \textbf{\hspace{2.1cm}0.00} \\
        \textbf{\hspace{4.75cm}TOTAL} \> \textbf{\hspace{4.3cm} """ + str(total) + r"""} \\
        \textbf{\hspace{2.45cm}AMEX CREDIT TEND} \> \textbf{\hspace{4.3cm} """ + str(total) + r"""} \\
        \textbf{\hspace{2.7cm}AMEX} \textbf{**** **** **** """ + amex_number + r"""} \\
        \textbf{\hspace{3.7cm}CHANGE DUE} \> \textbf{\hspace{4.7cm}0.00} \\
    \end{tabbing}
    
    \vspace{-2mm}

    \textbf{\huge{\# ITEMS SOLD 5}}\\
    \vspace{0.5cm}
    \textbf{""" + tc_number + r"""}\\
    \includegraphics[width=\linewidth]{""" + barcode_path + r"""} % Barcode
    \vspace{0.5cm}
    \textbf{""" + random_date + r"""}
\end{center}  
\end{document}
"""
    with open("receipt.tex", "w") as f:
        f.write(receipt_template)

def compile_latex_to_png():
    """Compile LaTeX to PDF and convert to PNG."""
    try:
        subprocess.run(["pdflatex", "receipt.tex"], check=True)
        subprocess.run(["convert", "-density", "200", "receipt.pdf", "-quality", "100", "receipt.png"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}")
        return False
    return True

def load_accounts_from_csv():
    """Load accounts from CSV file."""
    csv_file = "accounts.csv"
    accounts = []
    
    if not os.path.exists(csv_file):
        # Create file with headers if it doesn't exist
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['email', 'password', 'points', 'last_login', 'flagged', 'proxy'])
        return accounts

    with open(csv_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append({
                'email': row['email'],
                'password': row['password'],
                'points': int(row['points']) if row['points'] else 0,
                'last_login': row['last_login'],
                'flagged': row['flagged'].lower() == 'true',
                'proxy': row['proxy']
            })
    return accounts

def update_account_csv(email, points=None, flagged=None):
    """Update account details in CSV file."""
    accounts = []
    csv_file = "accounts.csv"
    
    # Read existing accounts
    with open(csv_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        accounts = list(reader)
    
    # Update the specific account
    for account in accounts:
        if account['email'] == email:
            if points is not None:
                current_points = int(account['points']) if account['points'] else 0
                if current_points == points:  # Points didn't increase
                    account['flagged'] = 'True'
                account['points'] = str(points)
            if flagged is not None:
                account['flagged'] = str(flagged)
            account['last_login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Write back to CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'password', 'points', 'last_login', 'flagged', 'proxy'])
        writer.writeheader()
        writer.writerows(accounts)

async def stealth_async(page):
    """Enhanced async stealth implementation"""
    await page.evaluate("""
        () => {
            // Overwrite the navigator properties
            Object.defineProperties(navigator, {
                webdriver: {
                    get: () => false,
                    enumerable: true
                },
                hardwareConcurrency: {
                    get: () => 8,
                    enumerable: true
                },
                deviceMemory: {
                    get: () => 8,
                    enumerable: true
                },
                platform: {
                    get: () => "Win32",
                    enumerable: true
                }
            });

            // Add language preferences
            Object.defineProperty(navigator, 'languages', {
                get: () => ["en-US", "en"],
                enumerable: true
            });

            // Mock Chrome runtime
            window.chrome = {
                runtime: {},
                webstore: {},
                app: {
                    InstallState: {
                        DISABLED: 'DISABLED',
                        INSTALLED: 'INSTALLED',
                        NOT_INSTALLED: 'NOT_INSTALLED'
                    },
                    RunningState: {
                        CANNOT_RUN: 'CANNOT_RUN',
                        READY_TO_RUN: 'READY_TO_RUN',
                        RUNNING: 'RUNNING'
                    },
                    isInstalled: false,
                },
                csi: function(){},
                loadTimes: function(){}
            };

            // Add plugins
            const pluginArray = [{
                description: "Portable Document Format",
                filename: "internal-pdf-viewer",
                name: "Chrome PDF Plugin",
                mimeTypes: [{
                    description: "Portable Document Format",
                    suffixes: "pdf",
                    type: "application/x-google-chrome-pdf"
                }]
            }];

            Object.defineProperty(navigator, 'plugins', {
                get: () => pluginArray,
                enumerable: true
            });

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );

            // Add WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.'
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100'
                }
                return getParameter(parameter);
            };
        }
    """)

    # Add additional headers to appear more like a real browser
    await page.set_extra_http_headers({
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Upgrade-Insecure-Requests': '1',
        'Connection': 'keep-alive'
    })

    # Modify webdriver flags
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {value: false});
        Object.defineProperty(navigator, 'automationControlled', {value: false});
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """)

async def login_and_upload_receipt(playwright, account, receipt_path):
    """Modified login and upload receipt function using async/await."""
    email = account["email"]
    proxy_config = None
    
    if account['proxy'] and account['proxy'].strip():  # Check if proxy exists and isn't empty
        try:
            proxy_parts = account['proxy'].split(':')
            if len(proxy_parts) == 4:  # Format: host:port:username:password
                host, port, username, password = proxy_parts
                proxy_config = {
                    "server": f"http://{host}:{port}",
                    "username": username,
                    "password": password
                }
                print(f"[INFO] Using proxy for {email}: {host}:{port}")
            elif len(proxy_parts) == 2:  # Format: host:port
                host, port = proxy_parts
                proxy_config = {
                    "server": f"http://{host}:{port}"
                }
                print(f"[INFO] Using proxy without auth for {email}: {host}:{port}")
            else:
                print(f"[WARNING] Invalid proxy format for {email}. Expected host:port:username:password or host:port")
        except Exception as e:
            print(f"[WARNING] Invalid proxy format for {email}: {e}")

    browser = await playwright.chromium.launch(
        headless=False,  # Changed to True for stability
        proxy=proxy_config if proxy_config else None,
        args=[
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--disable-application-cache',
            '--disable-offline-load-stale-cache',
            '--disk-cache-size=0'
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        ignore_https_errors=True,  # Add this if you have SSL issues
        java_script_enabled=True
    )
    
    try:
        page = await context.new_page()
        await stealth_async(page)
        
        await page.goto("https://www.cavsrewards.com/auth")
        await page.wait_for_load_state("networkidle")
        
        continue_button = page.get_by_role("button", name="Continue to Cavs Rewards")
        await continue_button.wait_for(state="visible", timeout=30000)
        await continue_button.click()
        
        email_input = page.get_by_label("Email address")
        await email_input.wait_for(state="visible", timeout=30000)
        await email_input.fill(account["email"])
        
        password_input = page.get_by_label("Password")
        await password_input.wait_for(state="visible", timeout=30000)
        await password_input.fill(account["password"])
        
        continue_btn = page.get_by_role("button", name="Continue", exact=True)
        await continue_btn.wait_for(state="visible", timeout=30000)
        await continue_btn.click()
        
        await page.goto("https://www.cavsrewards.com/earn/coca-cola-products")
        await page.wait_for_load_state("networkidle")
        
        upload_btn = page.get_by_role("button", name="Upload Receipt")
        await upload_btn.wait_for(state="visible", timeout=30000)
        
        async with page.expect_file_chooser() as fc_info:
            await upload_btn.dblclick()
        file_chooser = await fc_info.value
        await file_chooser.set_files(receipt_path)
        
        submit_btn = page.get_by_role("button", name="Check")
        await submit_btn.wait_for(state="visible", timeout=30000)
        await submit_btn.click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3000) 
        
        await page.goto("https://www.cavsrewards.com/profile")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3000) 
        await page.wait_for_function('document.body.textContent.includes("Lifetime:")', timeout=30000)
        body_text = await page.locator("body").text_content()
        
        points = None
        if "Lifetime:" in body_text:
            matches = re.findall(r"Lifetime:\s*([\d,]+)", body_text)
            if matches:
                points = int(matches[0].replace(",", ""))
                print(f"Account points for {email}: {points}")
                update_account_csv(email, points=points)
                print(f"Updated points for {email}: {points}")

    except Exception as e:
        print(f"Error processing account {email}: {e}")
        update_account_csv(email, flagged=True)
    finally:
        await context.close()
        await browser.close()

async def main():
    """Modified main function to handle async operations."""
    while True:
        accounts = load_accounts_from_csv()
        
        if not accounts:
            print("[INFO] No accounts found in CSV. Please add accounts manually.")
            return

        accounts.sort(key=lambda x: datetime.strptime(x['last_login'], "%Y-%m-%d %H:%M:%S") if x['last_login'] else datetime.min)
        account = next((acc for acc in accounts if not acc['flagged']), None)
        
        if not account:
            print("[INFO] No valid accounts available. All accounts are flagged.")
            return

        print(f"[INFO] Processing oldest account {account['email']}...")
        
        async with async_playwright() as playwright:
            # Generate and upload receipt
            tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total = generate_random_receipt()
            create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, "Header.png", "barcode.png")

            if compile_latex_to_png():
                receipt_path = "receipt.png"
                await login_and_upload_receipt(playwright, account, receipt_path)
            else:
                print(f"[ERROR] Failed to generate receipt for {account['email']}. Skipping.")

        print("[INFO] Waiting 30 minutes before next account processing...")
        await asyncio.sleep(1800)  # Wait 30 minutes

if __name__ == "__main__":
    asyncio.run(main())
