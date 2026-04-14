import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "agent_name": "bold magenta",
    "thought": "italic white",
    "action": "bold green",
})

console = Console(theme=custom_theme)

def setup_logger():
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
    return logging.getLogger("AgentVerse")

def print_agent_step(agent_name: str, thought: str, action: str):
    console.print(f"\n[agent_name]Agent: {agent_name}[/agent_name]")
    console.print(f"[thought]Thinking:[/thought] {thought}")
    console.print(f"[action]Action:[/action] {action}")

def print_banner():
    console.print("""
    [bold blue]
    AgentVerse: Multi-Agent Universe
    ==================================
    [/bold blue]
    """, justify="center")
