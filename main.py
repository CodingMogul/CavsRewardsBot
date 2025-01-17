import csv
import os
import time
import random
import subprocess
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
from playwright.sync_api import Playwright, sync_playwright

catchall = "gmail.com"

def load_proxies(csv_file):
    """Load proxies from a CSV file."""
    time.sleep(1.5)
    if not os.path.exists(csv_file):
        print(f"Error: The file '{csv_file}' does not exist.")
        return []

    proxies = []
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 4:
                proxies.append({
                    "server": f"http://{row[0]}:{row[1]}",
                    "username": row[2],
                    "password": row[3]
                })
    time.sleep(1.5)
    return proxies

def get_proxy_config(proxies):
    """Get a random proxy configuration if proxies are provided."""
    time.sleep(1.5)
    if proxies:
        proxy = random.choice(proxies)
        return {
            "server": proxy["server"],
            "username": proxy["username"],
            "password": proxy["password"]
        }
    return None

def log_stats_to_excel(account_number, email, password, success, alr_processed):
    """Log or update stats in the account stats Excel file."""
    time.sleep(1.5)
    file_name = "account_stats.xlsx"
    columns = ["Account Number", "Email", "Password", "Success", "Already Processed"]

    # Check if the file exists and has the correct columns
    if os.path.exists(file_name):
        df = pd.read_excel(file_name)
        if not all(col in df.columns for col in columns):
            print(f"Warning: The file '{file_name}' has incorrect or missing columns. Recreating it.")
            df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(columns=columns)

    # Update existing stats or add new ones
    if email in df["Email"].values:
        df.loc[df["Email"] == email, "Success"] += success
        df.loc[df["Email"] == email, "Already Processed"] += alr_processed
    else:
        new_row = {
            "Account Number": account_number,
            "Email": email,
            "Password": password,
            "Success": success,
            "Already Processed": alr_processed,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(file_name, index=False)

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

def create_account(playwright: Playwright, accounts: list, account_number, proxies):
    """Create an account on Cavs Rewards."""
    time.sleep(1.5)
    proxy_config = get_proxy_config(proxies)
    browser = playwright.chromium.launch(headless=False, proxy=proxy_config)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.cavsrewards.com/")
    time.sleep(.5)
    page.get_by_placeholder("Referral Code (optional)").click()
    time.sleep(.5)
    page.get_by_placeholder("Referral Code (optional)").fill("BJjPn")
    time.sleep(.5)
    page.get_by_role("button", name="Continue to Cavs Rewards").click()
    time.sleep(.5)
    page.get_by_role("link", name="Create account now").click()

    email = f"{Faker().last_name()}{random.randint(1000, 9999)}@{catchall}"
    password = f"Pass{random.randint(1000, 9999)}{Faker().word()}!"

    time.sleep(.5)
    page.get_by_label("Email address").click()
    time.sleep(.5)
    page.get_by_label("Email address").fill(email)
    time.sleep(.5)
    page.get_by_label("Password").click()
    time.sleep(.5)
    page.get_by_label("Password").fill(password)
    time.sleep(.5)
    page.get_by_role("button", name="Continue", exact=True).click()
    time.sleep(.5)
    page.get_by_role("button", name="GET STARTED").click()
    time.sleep(.5)
    page.get_by_role("button", name="Continue").click()
    time.sleep(.5)
    page.get_by_role("button", name="Continue").click()
    time.sleep(.5)
    page.get_by_role("button", name="Continue").click()
    time.sleep(.5)
    page.get_by_role("button", name="Continue").click()
    time.sleep(.5)
    page.locator("svg").click()
    time.sleep(.5)
    page.get_by_role("button", name="Done").click()

    # Add success and alr_processed counters to the account details
    account_details = {
        "account_number": account_number,
        "email": email,
        "password": password,
        "success": 0,
        "alr_processed": 0
    }
    accounts.append(account_details)

    log_stats_to_excel(account_number, email, password, 0, 0)

    context.close()
    browser.close()
    print(f"Account created: {email}")

def login_and_upload_receipt(playwright, account, receipt_path, proxies):
    """Log into an account and upload receipt."""
    time.sleep(.5)
    proxy_config = get_proxy_config(proxies)
    browser = playwright.chromium.launch(headless=False, proxy=proxy_config)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.cavsrewards.com/auth")
    page.get_by_placeholder("Referral Code (optional)").click()
    time.sleep(.5)
    page.get_by_placeholder("Referral Code (optional)").fill("BJjPn")
    time.sleep(.5)
    page.get_by_role("button", name="Continue to Cavs Rewards").click()
    time.sleep(.5)
    page.get_by_label("Email address").fill(account["email"])
    time.sleep(.5)
    page.get_by_label("Password").fill(account["password"])
    time.sleep(.5)
    page.get_by_role("button", name="Continue", exact=True).click()
    time.sleep(.5)
    page.get_by_role("img", name="Close").click()
    time.sleep(.5)
    page.get_by_role("link", name="Card Top Coca-Cola Products").click()
    time.sleep(.5)
    page.locator('input[type="file"]').set_input_files(receipt_path)
    time.sleep(.5)
    page.get_by_role("button", name="Check").click()
    time.sleep(5)

    try:
        if page.get_by_role("img", name="Receipt Approved").is_visible():
            account["success"] += 1  # Increment success for this account
        elif page.locator("[id=\"\\31 \"]").text_content() == "This receipt has already been processed. Please upload a different receipt. Try smoothing out the receipt if necessary, and try again.":
            account["alr_processed"] += 1  # Increment alr_processed for this account
        else:
            raise Exception("Unhandled condition encountered.")
    except Exception as e:
        print(f"An exception occurred: {e}")

    context.close()
    browser.close()

def main():
    """Main function to create accounts, generate receipts, and log statistics."""
    accounts = []
    proxies = load_proxies("proxies.csv")

    with sync_playwright() as playwright:
        # Step 1: Create 5 accounts
        for i in range(1, 6):
            create_account(playwright, accounts, i, proxies)

        while True:
            # Step 2: Iterate through accounts
            for account in accounts:
                account_number = account["account_number"]
                email = account["email"]
                password = account["password"]

                # Generate a receipt before each login
                tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total = generate_random_receipt()
                logo_path = "Header.png"
                barcode_path = "barcode.png"
                
                # Create receipt LaTeX file and compile it into PNG
                create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, logo_path, barcode_path)
                if compile_latex_to_png():
                    receipt_path = "receipt.png"
                else:
                    print("Failed to generate receipt. Skipping this account.")
                    continue

                # Log in and upload the generated receipt
                login_and_upload_receipt(playwright, account, receipt_path, proxies)

                print(f"Processing account {email}: Success={account['success']}, Already Processed={account['alr_processed']}")

                # Log stats to Excel
                log_stats_to_excel(
                    account_number, email, password, account["success"], account["alr_processed"]
                )


if __name__ == "__main__":
    main()
