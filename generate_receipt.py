import random
from datetime import datetime, timedelta
import os
import subprocess
import json
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
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Error during compilation: {e}"
        print(error_msg)
        log_receipt_failed("Receipt Generator", error_msg)
        return False

def main():
    tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total = generate_random_receipt()
    logo_path = "Header.png"
    barcode_path = "barcode.png"

    # Check if required files exist
    if not os.path.exists(logo_path):
        error_msg = f"Error: '{logo_path}' is missing!"
        print(error_msg)
        log_receipt_failed("Receipt Generator", error_msg)
        return
    if not os.path.exists(barcode_path):
        error_msg = f"Error: '{barcode_path}' is missing!"
        print(error_msg)
        log_receipt_failed("Receipt Generator", error_msg)
        return

    log_receipt_submission("Receipt Generator")
    create_receipt_latex(tc_number, st_number, random_date, amex_number, items, subtotal, tax1, total, logo_path, barcode_path)
    
    if compile_latex_to_png():
        for ext in ["aux", "log", "pdf", "tex"]:
            if os.path.exists(f"receipt.{ext}"):
                os.remove(f"receipt.{ext}")
        print("Receipt generated: receipt.png")
        log_receipt_accepted("Receipt Generator")
    else:
        print("Failed to generate receipt.")
        log_receipt_failed("Receipt Generator", "Failed to compile receipt")

if __name__ == "__main__":
    main()
