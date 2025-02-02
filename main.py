import csv
import os
import re
import time
import random
import subprocess
from datetime import datetime, timedelta
from playwright.sync_api import Playwright, sync_playwright
from playwright.sync_api import expect
from undetected_playwright import stealth_sync
from faker import Faker

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

def login_and_upload_receipt(playwright, account, receipt_path):
    """Modified login and upload receipt function."""
    email = account["email"]
    proxy_config = None
    
    if account['proxy']:  # Parse proxy string from CSV
        proxy_parts = account['proxy'].split('@')
        if len(proxy_parts) == 2:
            auth, server = proxy_parts
            username, password = auth.split(':')
            host, port = server.split(':')
            proxy_config = {
                "server": f"http://{host}:{port}",
                "username": username,
                "password": password
            }
    
    # Modified browser launch configuration
    browser = playwright.chromium.launch(
        headless=False,
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
        ],
        proxy=proxy_config if proxy_config else None
    )
    
    # Create a new context with additional options
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        ignore_https_errors=True,  # Add this if you have SSL issues
        java_script_enabled=True
    )
    
    try:
        page = context.new_page()
        stealth_sync(page)
        page.goto("https://www.cavsrewards.com/auth")
        time.sleep(0.7)
        page.get_by_role("button", name="Continue to Cavs Rewards").click()
        time.sleep(0.7)
        page.get_by_label("Email address").fill(account["email"])
        time.sleep(0.7)
        page.get_by_label("Password").fill(account["password"])
        time.sleep(0.7)
        page.get_by_role("button", name="Continue", exact=True).click()
        time.sleep(0.7)
        page.goto("https://www.cavsrewards.com/earn/coca-cola-products")
        time.sleep(2)
        # Use file chooser to upload the receipt
        with page.expect_file_chooser() as fc_info:
            page.get_by_text("Click to upload").click()
        file_chooser = fc_info.value
        file_chooser.set_files(receipt_path)
        time.sleep(2)
        
        # Click submit button
        page.get_by_role("button", name="Submit").click()
        time.sleep(2)
        page.goto("https://www.cavsrewards.com/profile")
        time.sleep(2)
        # Check if the text "Lifetime:" exists in the body
        body_text = page.locator("body").text_content()
        assert "Lifetime:" in page.locator("body").text_content(), "Text 'Lifetime:' not found on the page"
        # Retrieve the text content of the <body>
        # Extract points
        points = None
        if "Lifetime:" in body_text:
            matches = re.findall(r"Lifetime:\s*([\d,]+)", body_text)
            if matches:
                points = int(matches[0].replace(",", ""))
                print(f"Account points for {email}: {points}")

        # After getting points
        if points is not None:
            update_account_csv(email, points=points)
            print(f"Updated points for {email}: {points}")
        
        # Add receipt upload functionality after successful login
        print("[INFO] Uploading receipt...")
        page.get_by_role("button", name="Upload Receipt").click()
        time.sleep(1)
        
        # Use file chooser to upload the receipt
        with page.expect_file_chooser() as fc_info:
            page.get_by_text("Click to upload").click()
        file_chooser = fc_info.value
        file_chooser.set_files(receipt_path)
        time.sleep(2)
        
        # Click submit button
        page.get_by_role("button", name="Submit").click()
        time.sleep(2)

    except Exception as e:
        print(f"Error processing account {email}: {e}")
        update_account_csv(email, flagged=True)
    finally:
        context.close()
        browser.close()

def main():
    """Modified main function to process oldest account every 30 minutes."""
    while True:
        accounts = load_accounts_from_csv()
        
        if not accounts:
            print("[INFO] No accounts found in CSV. Please add accounts manually.")
            return

        # Sort accounts by last_login time, None/empty values first
        accounts.sort(key=lambda x: datetime.strptime(x['last_login'], "%Y-%m-%d %H:%M:%S") if x['last_login'] else datetime.min)
        
        # Get the oldest non-flagged account
        account = next((acc for acc in accounts if not acc['flagged']), None)
        
        if not account:
            print("[INFO] No valid accounts available. All accounts are flagged.")
            return

        print(f"[INFO] Processing oldest account {account['email']}...")
        
        with sync_playwright() as playwright:
            # Generate and upload receipt
            tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total = generate_random_receipt()
            create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, "Header.png", "barcode.png")

            if compile_latex_to_png():
                receipt_path = "receipt.png"
                login_and_upload_receipt(playwright, account, receipt_path)
            else:
                print(f"[ERROR] Failed to generate receipt for {account['email']}. Skipping.")

        print("[INFO] Waiting 30 minutes before next account processing...")
        time.sleep(1800)  # Wait 30 minutes

if __name__ == "__main__":
    main()
