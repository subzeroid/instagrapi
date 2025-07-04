#!/usr/bin/env python3
"""
End-to-end test for instagrapi type improvements.

Tests our new Pydantic models:
- DirectMessage.reactions -> MessageReactions
- DirectMessage.link -> MessageLink  
- DirectThread.last_seen_at -> Dict[str, LastSeenInfo]
- DirectMessage.visual_media -> VisualMedia

Usage:
    export IG_USERNAME="your_username"
    export IG_PASSWORD="your_password" 
    python test_type_improvements.py
    
Features:
- Automatic session management (saves to ig_settings.json)
- Reuses existing sessions to avoid repeated logins
- Interactive 2FA prompts when needed
- Preserves device identity to avoid Instagram suspicion
"""

import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

# Load environment variables from .env file
load_dotenv()

# Import our improved types
from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired, 
    LoginRequired,
    FeedbackRequired,
    PleaseWaitFewMinutes
)
from instagrapi.types import DirectMessage, DirectThread

console = Console()


def setup_client() -> Optional[Client]:
    """Setup and login Instagram client using session management best practices."""
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    session_file = "ig_settings.json"
    
    if not username or not password:
        console.print("[red]Error: Set IG_USERNAME and IG_PASSWORD environment variables[/red]")
        return None
        
    client = Client()
    
    # Step 1: Try to login using existing session
    if _try_session_login(client, username, password, session_file):
        return client
        
    # Step 2: Fall back to credential login with 2FA
    if _try_credential_login(client, username, password, session_file):
        return client
        
    console.print("[red]✗ Could not login with either session or credentials[/red]")
    return None


def _try_session_login(client: Client, username: str, password: str, session_file: str) -> bool:
    """Try to login using saved session."""
    
    if not os.path.exists(session_file):
        console.print("[yellow]No existing session found, will use credentials[/yellow]")
        return False
        
    try:
        console.print("[yellow]Attempting login with saved session...[/yellow]")
        client.load_settings(session_file)
        client.login(username, password)
        
        # Validate session by making a test request
        try:
            client.get_timeline_feed()
            console.print("[green]✓ Session login successful[/green]")
            return True
        except LoginRequired:
            console.print("[yellow]Session expired, need fresh login[/yellow]")
            return _handle_invalid_session(client, username, password, session_file)
            
    except Exception as e:
        console.print(f"[yellow]Session login failed: {e}[/yellow]")
        return False


def _try_credential_login(client: Client, username: str, password: str, session_file: str) -> bool:
    """Try to login using username and password with 2FA support."""
    try:
        console.print(f"[yellow]Attempting credential login for {username}...[/yellow]")
        console.print("[yellow]🔐 2FA verification required[/yellow]")
        
        # Prompt for 2FA code directly (since user has 2FA enabled)
        verification_code = Prompt.ask("[cyan]Enter your 2FA code (6 digits)[/cyan]")
        
        # Simple validation
        if not (len(verification_code) == 6 and verification_code.isdigit()):
            console.print("[red]Invalid 2FA code format. Please enter 6 digits.[/red]")
            return False
        
        console.print("[yellow]Logging in with 2FA code...[/yellow]")
        client.login(username, password, verification_code=verification_code)
        client.dump_settings(session_file)
        console.print("[green]✓ Login successful with 2FA[/green]")
        return True
                
    except Exception as e:
        console.print(f"[red]✗ Credential login failed: {e}[/red]")
        return False


def _handle_invalid_session(client: Client, username: str, password: str, session_file: str) -> bool:
    """Handle invalid session by preserving UUIDs and creating fresh login."""
    console.print("[yellow]Creating fresh session while preserving device identity...[/yellow]")
    
    # Preserve device UUIDs for consistency
    old_session = client.get_settings()
    client.set_settings({})
    
    if old_session and "uuids" in old_session:
        client.set_uuids(old_session["uuids"])
    
    # Try fresh credential login
    return _try_credential_login(client, username, password, session_file)


def test_new_pydantic_models(threads: List[DirectThread]) -> None:
    """Test our new Pydantic models by printing the actual objects."""
    console.print("\n[bold green]🔍 Testing New Pydantic Models[/bold green]")
    
    for thread_index, thread in enumerate(threads):
        console.rule(title=f"Thread {thread_index + 1}: {thread.thread_title or 'Unnamed'}", style="bold blue")
        console.print(thread, end="\n\n")
        
        # Show messages in this thread
        if thread.messages:
            console.print(f"[bold cyan]Messages in this thread ({len(thread.messages)}):[/bold cyan]")
            for msg_index, message in enumerate(thread.messages[:5]):  # Show first 5 messages
                console.print(f"\n[cyan]Message {msg_index + 1}:[/cyan]")
                console.print(message, end="\n")


def run_tests() -> None:
    """Run comprehensive tests of our type improvements."""
    client = setup_client()
    if not client:
        sys.exit(1)
        
    console.print("\n[bold green]🚀 Testing instagrapi Type Safety Improvements[/bold green]")
    console.print("=" * 60)
    
    try:
        # Get some direct threads
        console.print("\n[yellow]Fetching direct message threads...[/yellow]")
        threads: List[DirectThread] = client.direct_threads(amount=20)
        
        if not threads:
            console.print("[red]No threads found. Send yourself a DM first.[/red]")
            return
            
        console.print(f"[green]✓ Found {len(threads)} threads[/green]")
        
        # Test our new Pydantic models by showing the actual objects
        test_new_pydantic_models(threads)
        
        console.print(f"\n[bold green]✓ Type safety testing completed on {len(threads)} threads[/bold green]")
        
    except LoginRequired:
        console.print(f"\n[red]Session expired during testing. Please re-run the script.[/red]")
    except FeedbackRequired as e:
        console.print(f"\n[red]Instagram feedback required: {e}[/red]")
        console.print("[yellow]Try again later or check if account is temporarily restricted.[/yellow]")
    except PleaseWaitFewMinutes as e:
        console.print(f"\n[red]Instagram rate limit: {e}[/red]")
        console.print("[yellow]Please wait a few minutes before running the test again.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Test failed with error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
    
    # Note: We keep ig_settings.json for reuse in subsequent test runs
    # This avoids repeated authentication and reduces Instagram ban risk


if __name__ == "__main__":
    run_tests() 