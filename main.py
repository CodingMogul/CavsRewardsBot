import csv
import os
import re
import time
import random
import subprocess
from datetime import datetime, timedelta
from patchright.async_api import async_playwright
from faker import Faker
import asyncio
import requests
from typing import Optional

# Discord webhook URL - replace with your actual webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1342235677152252016/EcVcFoN2q-KqXtBG7kH0vI6dRcFYZNYIVuRRxfbkqN357VJrrDlz8vU2Hf2Tb4ei8sqP"

def send_webhook_message(content: str, color: Optional[int] = None) -> None:
    """Send a message to Discord webhook."""
    if not DISCORD_WEBHOOK_URL.startswith("http"):
        return  # Skip if webhook URL is not set
        
    embed = {
        "description": content,
        "color": color or 0x00ff00  # Default to green if no color specified
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, 
                     json={"embeds": [embed]},
                     headers={"Content-Type": "application/json"})
    except Exception as e:
        print(f"Failed to send webhook message: {e}")

def log_idle_no_accounts():
    send_webhook_message("⚠️ No accounts ready for submission", 0xffa500)  # Orange

def log_account_login(account: str):
    send_webhook_message(f"🔑 Logging into account: {account}", 0x00ff00)  # Green

def log_login_failed(account: str, error: str):
    send_webhook_message(f"❌ Login failed for account {account}: {error}", 0xff0000)  # Red

def log_receipt_submission(account: str):
    send_webhook_message(f"📝 Submitting receipt for account: {account}", 0x00ff00)

def log_receipt_failed(account: str, error: str):
    send_webhook_message(f"❌ Receipt submission failed for {account}: {error}", 0xff0000)

def log_receipt_accepted(account: str):
    send_webhook_message(f"✅ Receipt accepted for account: {account}", 0x00ff00)

def log_new_submission_date(account: str, next_date: str):
    send_webhook_message(f"📅 New submission date set for {account}: {next_date}", 0x00ffff)  # Cyan

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
            writer.writerow(['email', 'password', 'points', 'next_submission', 'flagged', 'proxy'])
        return accounts

    with open(csv_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append({
                'email': row['email'],
                'password': row['password'],
                'points': int(row['points']) if row['points'] else 0,
                'next_submission': row['next_submission'],
                'flagged': row['flagged'].lower() == 'true',
                'proxy': row['proxy']
            })
    return accounts

def update_account_csv(email, points=None, flagged=None, next_submission=None):
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
            if next_submission is not None:
                account['next_submission'] = next_submission
    
    # Write back to CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'password', 'points', 'next_submission', 'flagged', 'proxy'])
        writer.writeheader()
        writer.writerows(accounts)

def get_next_available_account(accounts):
    """Get the next available account based on submission timing."""
    current_time = datetime.now()
    
    # First, look for accounts with blank next_submission
    blank_submission_account = next(
        (acc for acc in accounts if not acc['flagged'] and not acc['next_submission']), 
        None
    )
    if blank_submission_account:
        return blank_submission_account

    # Then, look for accounts whose next_submission time has passed
    available_account = next(
        (acc for acc in accounts 
         if not acc['flagged'] 
         and acc['next_submission']
         and datetime.strptime(acc['next_submission'], "%Y-%m-%d %H:%M:%S") <= current_time),
        None
    )
    
    if not available_account:
        log_idle_no_accounts()
        
    return available_account

async def login_and_upload_receipt(playwright, account, receipt_path):
    """Modified login and upload receipt function using async/await."""
    email = account["email"]
    proxy_config = None
    
    log_account_login(email)
    
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
            error_msg = f"[WARNING] Invalid proxy format for {email}: {e}"
            print(error_msg)
            log_login_failed(email, error_msg)
            return False

    try:
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
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login process
            await page.goto('https://www.cavsrewards.com/auth')
            await page.click('text=Continue to Cavs Rewards')
            await page.fill('input[type="email"]', email)
            await page.fill('input[type="password"]', account['password'])
            await page.get_by_role("button", name="Continue", exact=True).click()
            
            # Wait for login to complete
            await page.wait_for_timeout(5000)
            
            # Check if login was successful
            if await page.locator('text=Sign In').count() > 0:
                error_msg = "Login failed - Sign In button still present"
                print(f"[ERROR] {error_msg}")
                log_login_failed(email, error_msg)
                return False
                
            log_receipt_submission(email)
            
            # Upload receipt
            await page.goto('https://www.cavsrewards.com/earn/coca-cola-products')
            await page.wait_for_load_state("networkidle")

            # First find and set the hidden file input
            await page.wait_for_selector('input[type="file"]', state='attached')
            await page.set_input_files('input[type="file"]', receipt_path)

            # Then click the Check/Submit button
            await page.get_by_role("button").nth(3).click()

            
            # Wait for upload to complete and check result
            await page.wait_for_timeout(5000)
            
            await page.goto('https://www.cavsrewards.com/rewards')
            await page.wait_for_load_state("networkidle")
            
            # Get current points using the correct selector
            points_text = await page.locator('h1.text-4xl.text-textColorSecondary').text_content()
            new_points = int(points_text)
            
            # Get previous points from the account
            previous_points = int(account['points']) if account['points'] else 0
            
            # Check if points haven't increased
            if new_points <= previous_points:
                error_msg = f"Receipt submission failed: Points didn't increase (Previous: {previous_points}, Current: {new_points})"
                print(f"[ERROR] {error_msg}")
                log_receipt_failed(email, error_msg)
                update_account_csv(email, points=new_points, flagged=True)
                return False
            
            # Points increased successfully
            # Set next submission time (24-48 hours from now)
            next_submission = datetime.now() + timedelta(hours=random.randint(24, 48))
            next_submission_str = next_submission.strftime("%Y-%m-%d %H:%M:%S")
            
            # Update CSV with new points and next submission time
            update_account_csv(email, points=new_points, next_submission=next_submission_str)
            
            log_receipt_accepted(email)
            log_new_submission_date(email, next_submission_str)
            
            return True
            
        except Exception as e:
            error_msg = f"Error during receipt submission: {str(e)}"
            print(f"[ERROR] {error_msg}")
            log_receipt_failed(email, error_msg)
            return False
            
        finally:
            await context.close()
            await browser.close()
            
    except Exception as e:
        error_msg = f"Browser launch failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        log_login_failed(email, error_msg)
        return False

async def main():
    """Modified main function to handle async operations."""
    while True:
        accounts = load_accounts_from_csv()
        
        if not accounts:
            print("[INFO] No accounts found in CSV. Please add accounts manually.")
            return

        account = get_next_available_account(accounts)
        
        if not account:
            print("[INFO] No accounts available for submission. Waiting 5 minutes...")
            await asyncio.sleep(300)  # Wait 5 minutes before checking again
            continue

        print(f"[INFO] Processing account {account['email']}...")
        
        async with async_playwright() as playwright:
            # Generate and upload receipt
            tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total = generate_random_receipt()
            create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, "Header.png", "barcode.png")

            if compile_latex_to_png():
                receipt_path = "receipt.png"
                await login_and_upload_receipt(playwright, account, receipt_path)
                
                # Set next submission time based on whether this was the first submission
                if not account['next_submission']:
                    # For first submission (blank next_submission), set to exactly 50 hours from now
                    next_submission = (datetime.now() + timedelta(hours=50)).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[INFO] First submission for {account['email']}, setting next submission to exactly 50 hours from now: {next_submission}")
                else:
                    # For subsequent submissions, use random 12-36 hour window
                    next_hours = random.uniform(12, 36)
                    next_submission = (datetime.now() + timedelta(hours=next_hours)).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[INFO] Subsequent submission for {account['email']}, setting next submission randomly to {next_submission}")
                
                update_account_csv(account['email'], next_submission=next_submission)
            else:
                print(f"[ERROR] Failed to generate receipt for {account['email']}. Skipping.")

        print("[INFO] Waiting 5 minutes before checking next account...")
        await asyncio.sleep(300)  # Wait 5 minutes before processing next account

if __name__ == "__main__":
    asyncio.run(main())
