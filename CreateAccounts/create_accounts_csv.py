import asyncio
import csv
from datetime import datetime
import os
import random
import string
import sys
from typing import List, Tuple, Optional
from patchright.async_api import Playwright, async_playwright, expect
import aiohttp  # Add this import at the top with other imports

class AccountCreationError(Exception):
    """Custom exception for account creation errors"""
    pass

def generate_password() -> str:
    try:
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Generate password with at least one of each required type
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special),
        ]
        
        # Add additional random characters to reach desired length (12-16 characters)
        length = random.randint(12, 16)
        all_chars = lowercase + uppercase + digits + special
        password.extend(random.choice(all_chars) for _ in range(length - 4))
        
        # Shuffle the password characters
        random.shuffle(password)
        return ''.join(password)
    except Exception as e:
        print(f"Error generating password: {str(e)}")
        raise AccountCreationError("Failed to generate password") from e

def read_emails(filename: str) -> List[str]:
    try:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Email file not found: {filename}")
            
        with open(filename, 'r') as f:
            emails = [line.strip() for line in f if line.strip()]
            
        if not emails:
            raise ValueError("Email file is empty")
            
        return emails
    except Exception as e:
        print(f"Error reading emails from {filename}: {str(e)}")
        raise

def read_proxies(filename: str) -> List[str]:
    try:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Proxy file not found: {filename}")
            
        with open(filename, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
            
        if not proxies:
            raise ValueError("Proxy file is empty")
            
        return proxies
    except Exception as e:
        print(f"Error reading proxies from {filename}: {str(e)}")
        raise

def remove_proxy(filename: str, used_proxy: str) -> bool:
    try:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Proxy file not found: {filename}")
            
        with open(filename, 'r') as f:
            proxies = f.readlines()
            
        with open(filename, 'w') as f:
            removed = False
            for proxy in proxies:
                if proxy.strip() != used_proxy:
                    f.write(proxy)
                else:
                    removed = True
                    
        return removed
    except Exception as e:
        print(f"Error removing proxy {used_proxy} from {filename}: {str(e)}")
        return False

async def create_account(playwright: Playwright, email: str, proxy: str) -> Tuple[bool, Optional[str]]:
    browser = None
    context = None
    try:
        # Validate proxy format
        proxy_parts = proxy.split(':')
        if len(proxy_parts) != 4:
            raise ValueError(f"Invalid proxy format: {proxy}")
        
        browser = await playwright.chromium.launch(
            headless=False,
            proxy={
                "server": f"{proxy_parts[0]}:{proxy_parts[1]}",
                "username": proxy_parts[2],
                "password": proxy_parts[3]
            }
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Generate random password for each account
        password = generate_password()
        
        # Set timeout for navigation
        page.set_default_timeout(30000)  # 30 seconds timeout
        
        try:
            await page.goto("https://www.cavsrewards.com/")
            await asyncio.sleep(1)  # Wait 10 seconds
            
            await page.goto("https://www.cavsrewards.com/auth")
            await asyncio.sleep(1)
            
            await page.get_by_role("button", name="Continue to Cavs Rewards").click()
            await asyncio.sleep(2)
            
            await page.get_by_role("link", name="Create account now").click()
            await asyncio.sleep(2)
            
            await page.get_by_label("Email address").click()
            await asyncio.sleep(1)
            
            await page.get_by_label("Email address").fill(email)
            await asyncio.sleep(1)
            
            await page.get_by_label("Password").click()
            await asyncio.sleep(1)
            
            await page.get_by_label("Password").fill(password)
            await asyncio.sleep(1)
            
            await page.locator("form").filter(has_text="Continue Email address Email address* Password Password* Show password Hide pass").get_by_role("button", name="Continue").click()
            await asyncio.sleep(2)
            
            await page.get_by_role("button", name="GET STARTED").click()
            await asyncio.sleep(2)
            
            await page.get_by_role("button", name="Continue").click()
            await asyncio.sleep(1)
            
            await page.get_by_role("button", name="Continue").click()
            await asyncio.sleep(1)
            
            await page.get_by_role("button", name="Continue").click()
            await asyncio.sleep(1)
            
            await page.get_by_role("button", name="Continue").click()
            await asyncio.sleep(1)
            
            await page.locator("path").click()
            await asyncio.sleep(1)
            
            await page.get_by_role("button", name="Done").click()
            await asyncio.sleep(1)
            
            return True, password
            
        except Exception as e:
            print(f"Error during account creation flow for {email}: {str(e)}")
            return False, None
            
    except Exception as e:
        print(f"Error setting up browser for {email}: {str(e)}")
        return False, None
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()

async def send_discord_webhook(webhook_url: str, email: str, password: str, proxy: str, success: bool) -> None:
    """Send detailed notification to Discord webhook when account creation succeeds or fails"""
    try:
        status_emoji = "✅" if success else "❌"
        status_text = "Created" if success else "Failed"
        
        message = {
            "embeds": [{
                "title": f"{status_emoji} Account {status_text}",
                "fields": [
                    {
                        "name": "Email",
                        "value": f"`{email}`",
                        "inline": True
                    },
                    {
                        "name": "Password",
                        "value": f"`{password if success else 'N/A'}`",
                        "inline": True
                    },
                    {
                        "name": "Proxy Status",
                        "value": f"`{'Used' if success else 'Unused'}: {proxy}`",
                        "inline": False
                    }
                ],
                "color": 65280 if success else 16711680,  # Green for success, Red for failure
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status != 204:
                    print(f"Failed to send webhook notification: {response.status}")
    except Exception as e:
        print(f"Error sending webhook notification: {str(e)}")

async def main():
    try:
        # Add webhook URL near the start of main
        webhook_url = "https://discord.com/api/webhooks/1342235677152252016/EcVcFoN2q-KqXtBG7kH0vI6dRcFYZNYIVuRRxfbkqN357VJrrDlz8vU2Hf2Tb4ei8sqP"  # Replace with your webhook URL
        
        # Create directory for CSV if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file = os.path.join(script_dir, 'new_accounts.csv')
        
        print(f"CSV will be created/updated at: {csv_file}")
        
        # Read emails and proxies
        emails = read_emails('CreateAccounts/emails.txt')
        proxies = read_proxies('CreateAccounts/proxies.txt')
        
        if len(proxies) < len(emails):
            raise ValueError(f"Not enough proxies ({len(proxies)}) for all emails ({len(emails)})")
        
        # Store successful accounts data
        accounts_data = []
        used_proxies = []
        
        async with async_playwright() as playwright:
            for email, proxy in zip(emails, proxies):
                try:
                    print(f"Creating account for {email}...")
                    success, password = await create_account(playwright, email, proxy)
                    
                    if success and password:
                        accounts_data.append([email, password, '0', '', 'false', proxy])
                        used_proxies.append(proxy)
                        print(f"Successfully created account for {email}")
                        await send_discord_webhook(webhook_url, email, password, proxy, True)
                    else:
                        print(f"Failed to create account for {email}")
                        await send_discord_webhook(webhook_url, email, "", proxy, False)
                        
                except Exception as e:
                    print(f"Error processing email {email}: {str(e)}")
                    continue
        
        # After all accounts are created, write to CSV
        if accounts_data:
            try:
                # Check if file exists and handle accordingly
                mode = 'a' if os.path.exists(csv_file) else 'w'
                with open(csv_file, mode, newline='') as f:
                    writer = csv.writer(f)
                    # Write headers only if it's a new file
                    if mode == 'w':
                        writer.writerow(['email', 'password', 'points', 'next_submission', 'flagged', 'proxy'])
                        print("Created new CSV file with headers")
                    writer.writerows(accounts_data)
                    print(f"Successfully wrote {len(accounts_data)} accounts to CSV")
                
                # Verify the file was created and has content
                if os.path.exists(csv_file):
                    file_size = os.path.getsize(csv_file)
                    print(f"CSV file created successfully. Size: {file_size} bytes")
                else:
                    raise FileNotFoundError("CSV file was not created successfully")
                
                # Remove used proxies after successful CSV write
                for proxy in used_proxies:
                    if remove_proxy('CreateAccounts/proxies.txt', proxy):
                        print(f"Removed used proxy: {proxy}")
                    else:
                        print(f"Failed to remove proxy: {proxy}")
            
            except PermissionError:
                print(f"Error: No permission to write to {csv_file}")
                sys.exit(1)
            except IOError as e:
                print(f"Error writing to CSV file: {str(e)}")
                sys.exit(1)
        else:
            print("No accounts were successfully created")
            
    except Exception as e:
        print(f"Fatal error in main: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
