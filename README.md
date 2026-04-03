
# Turn-Based Sandbox Grand Strategy War Simulator

### Powered by the Ebee Engine (EE)

A **Google Maps-style, 2D turn-based grand strategy war simulator** where players command nations and shape global history through conquest, diplomacy, and economic growth. Featuring the innovative **dNPC™ system**—non-player nations controlled by LLMs for dynamic, personality-driven geopolitics.
> **Note:** This project was developed as a Mini IT Project. It focuses on modular architecture and the integration of modern AI agents within a classic strategy game loop.
-----

## 🚀 Quick Start

### Prerequisites

  * **Python:** 3.9, 3.11, or 3.12 (Note: 3.14 is currently unsupported).
  * **API Key:** An OpenAI API key is required for dNPC™ functionality (or a local Ollama instance).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/your-repo-name.git
    cd your-repo-name
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the simulation:**
    ```bash
    python main.py
    ```

-----

## Tech Stack

  * **Engine:** Ebee Engine (Custom Python Map/Physics Engine)
  * **Graphics/UI:** Pygame, Pygame-GUI
  * **AI Orchestration:** Pydantic-AI, LangGraph, OpenAI API
  * **Data Management:** SQLite3, JSON (for persistence and SVG metadata)

-----

## Ebee Engine (EE) | Self-Developed Engine

The **Ebee Engine** is the project's main engine, converting static SVG data into an interactive, gameplay-ready strategic render.

### Map & Geometry

  * **SVG Processing:** Converts path data into renderable polygons and hitboxes.
  * **Interactive Projection:** Maps world coordinates to screen points with horizontal "infinite scroll" wrapping.
  * **Centroid Calculation:** Automatically determines label and unit placement for provinces (To be fixed).

### Pathfinding & Movement

  * **Adjacency Graph:** Built dynamically to allow AI and players to navigate provinces.
  * \**A* Pathfinding:\*\* Implements optimal routing with terrain-based cost modifiers (Mountains, Urban, Plains).

-----

## Key Features

### 1\. dNPC™ (LLM-Driven Diplomacy)

Non-player nations aren't just scripts; they are agents.

  * **Personality-Driven:** Leaders react based on ideology, reputation, and world tension.
  * **Hybrid Intelligence:** Combines LLM reasoning with a rigid algorithmic validation layer to prevent "AI hallucinations" in game logic.

### 2\. National Economy System

  * **The "Pulse":** A turn-based system handling tax collection, population growth, and infrastructure scaling.
  * **Resource Management:** Balance recruitment costs against economic stability.

### 3\. Procedural World Events

  * Generates dynamic news reports and political shifts based on player actions.
  * Utilizes LLMs to write immersive narrative descriptions of in-game developments.

-----

## Development Team

| Member | Role | Primary Contributions |
| :--- | :--- | :--- |
| **M. Ryan Haiqal** | Lead Developer | Engine Core, Performance, LLM Integration (Pydantic), Optimization. |
| **Benedict Chin** | Game Logic & UI | UI/UX Design, Combat Math, Save/Load Systems. |
| **Adam Syahmi** | Narrative Systems | Database setup, Prompt Engineering, NPC Personality Logic. |

-----

## AI Integration 

To ensure the game remains playable in all environments, we utilize a three-tier AI fallback strategy:

1.  **Online Mode:** Premium reasoning via OpenAI APIs.
2.  **Local Mode:** Offline LLM support via Ollama.
3.  **Offline Mode:** A robust rule-based heuristic system for zero-latency/offline play.
