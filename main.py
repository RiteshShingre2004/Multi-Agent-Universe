import os
from dotenv import load_dotenv
from core.models import AgentConfig
from core.llm_provider import LLMFactory
from core.agent import Agent, Orchestrator
from utils.logger import setup_logger, print_banner, console

# Load environment variables
load_dotenv()

def main():
    setup_logger()
    print_banner()

    # Centralized Configuration
    provider_type = os.getenv("DEFAULT_PROVIDER", "ollama").lower()
    
    config = {}
    if provider_type == "gemini":
        config = {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model_name": os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        }
    elif provider_type == "groq":
        config = {
            "api_key": os.getenv("GROQ_API_KEY"),
            "model_name": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        }
    elif provider_type == "ollama":
        config = {
            "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "model_name": os.getenv("OLLAMA_MODEL", "llama3")
        }

    # Validation
    if provider_type != "ollama" and not config.get("api_key"):
        console.print(f"[bold red]Error: API Key for {provider_type.upper()} not found in .env file.[/bold red]")
        return

    # Initialize Provider
    try:
        provider = LLMFactory.get_provider(provider_type, config)
        console.print(f"[bold green]Connected to {provider_type.upper()} Provider ({config.get('model_name', 'default')})[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error initializing provider: {e}[/bold red]")
        return

    # Initialize Orchestrator
    universe = Orchestrator()

    # Define Agents
    manager_config = AgentConfig(
        name="Sarah",
        role="Chief Project Manager",
        goal="Coordinate complex research and writing projects by delegating to specialists.",
        backstory="A high-level coordinator who knows how to break down big goals into manageable tasks."
    )
    
    researcher_config = AgentConfig(
        name="Dr. Data",
        role="Lead Researcher",
        goal="Provide deep technical insights and factual data on any given topic.",
        backstory="A meticulous researcher with an eye for detail and a knack for finding obscure facts."
    )
    
    writer_config = AgentConfig(
        name="Poet",
        role="Technical Writer",
        goal="Transform technical data and research into engaging, clear, and professional reports.",
        backstory="A master wordsmith who can explain complex concepts to any audience."
    )

    # Register Agents
    universe.register_agent(Agent(manager_config, provider))
    universe.register_agent(Agent(researcher_config, provider))
    universe.register_agent(Agent(writer_config, provider))

    # The Workflow
    goal = "Create a comprehensive technical report on the future of Quantum Computing in 2026."
    
    console.print(f"\n[bold green]Starting Universe with Goal:[/bold green] {goal}\n")
    
    final_output = universe.run_task(goal, initial_role="Chief Project Manager")

    # Save to file
    os.makedirs("outputs", exist_ok=True)
    import datetime
    filename = f"outputs/report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Technical Report\n\n**Goal**: {goal}\n\n**Output**:\n{final_output}")
    
    console.print(f"\n[bold blue]Report saved to: {filename}[/bold blue]")

    console.print("\n" + "="*50)
    console.print("[bold green]FINAL UNIVERSE OUTPUT:[/bold green]")
    console.print("="*50)
    console.print(final_output)
    console.print("="*50)

if __name__ == "__main__":
    main()
