# Turn-Based Sandbox Grand Strategy War Simulator  
### with Procedural Events, NPC Enemies & Ebee Engine (EE)

---

## 🎮 Track
Game Development (Mini IT Project)

---

## 🧠 Language & Tech Stack
- Python  
- Pygame + Pygame-GUI  
- Pydantic-AI  
- JSON / SQLite3 (data persistence & optimization)  
- OpenAI API (LLM integration)  
- LangGraph (agent workflows / orchestration)  

---

## 🌍 Project Overview
This project is a **Google Maps-style, 2D turn-based grand strategy war simulator** where players command a nation and shape global history through conquest, diplomacy, economic growth, and procedural world events.

A core innovation is the **dNPC™ system**, where non-player nations are controlled by Large Language Models (LLMs), enabling strategic, personality-driven diplomacy and decision-making.

The simulation is powered at its core by the **Ebee Engine (EE)**, a custom-built map, movement, and pathfinding engine.

---

# ⚙️ Ebee Engine (EE) — Core Simulation System

The **Ebee Engine** is the backbone of the entire game. It handles map rendering, province interaction, movement logic, and turn-based simulation execution.

It transforms SVG-based maps into interactive strategic worlds with pathfinding, camera control, and gameplay-ready province metadata.

---

## 🧩 Core Engine Systems (engine.py)

### 🗺️ Map Loading & Processing
- **load_svg_stuff**  
  Loads SVG maps and converts paths into polygons for rendering and hit detection.

- **path_to_poly_parts**  
  Converts SVG path data into polygon segments for rendering and collision handling.

- **load_country_data**  
  Loads structured JSON data for countries and states.

- **group_subs_by_state**  
  Groups provinces under their parent states.

---

### 📐 Geometry & Rendering System
- **get_map_box**  
  Computes bounding box of the full map.

- **to_screen_points / to_screen_rect**  
  Converts world coordinates into screen coordinates.

- **get_center_of_shape**  
  Calculates centroid of a province shape.

- **parse_color_value**  
  Normalizes color formats for map indexing.

---

### 🎮 Camera & Navigation
- **get_min_zoom_fit_height**  
  Calculates minimum zoom level to fit map vertically.

- **clamp_cam_y**  
  Restricts vertical camera movement.

- **wrap_cam_x**  
  Enables horizontal wrapping for infinite scrolling effect.

---

### 🧠 Province & Gameplay Data Layer
- **prepare_province_meta**  
  Injects gameplay data into provinces (terrain, troops, modifiers).

- **get_parent_state_id**  
  Retrieves parent state from subdivision ID.

- **rects_touch_or_overlap**  
  Detects overlap between regions.

- **is_inside_poly**  
  Detects mouse interaction inside province polygons (click/hover detection).

---

### 🧭 Pathfinding & Movement System
- **build_province_graph**  
  Builds adjacency graph for provinces for AI and player movement.

- **get_move_cost**  
  Calculates movement cost based on terrain and conditions.

- **find_province_path**  
  Implements **A\*** pathfinding for optimal troop movement routes.

- **process_movement_orders**  
  Executes all movement orders each turn.

---

### ⏳ Game Loop & Execution
- **draw_loading**  
  Displays loading screen with progress updates.

- **main**  
  Core game loop:
  - Rendering system  
  - Input handling  
  - Game state updates  
  - Turn execution logic  

---

## 🌍 Project Overview (continued)

The world is driven by:
- Province-based global map simulation  
- Turn-based economic and military systems  
- AI-driven diplomacy (LLM + rule-based fallback)  
- Procedural world events and narratives  

Players interact with hundreds to thousands of provinces while shaping geopolitical outcomes.

---

## 💰 National Economy System
- Turn-based “pulse” system
- Includes:
  - Tax collection  
  - Population growth  
  - Recruitment  
  - Infrastructure development  
- Designed for scalability and optimization

---

## 🧠 LLM-Driven Diplomacy (dNPC™)
- AI-controlled leaders powered by LLM APIs (OpenAI / optional Ollama)
- Context-aware diplomacy based on:
  - World tension  
  - Reputation  
  - Ideology  
- Hybrid system:
  - LLM reasoning layer  
  - Algorithmic validation layer  

---

## ⚔️ Command & Combat System
- Province-based troop recruitment
- Frontline war simulation
- Terrain-based modifiers:
  - Mountains, rivers, urban, plains  
- Pathfinding + attrition modeling via Ebee Engine

---

## 🌍 Procedural Event System
- Generates dynamic world events
- LLM-generated news reports & political developments
- Reacts to player behavior and global state

---

## 🤝 Diplomatic State System
Tracks relationships between nations:
- Alliances  
- Non-aggression pacts  
- Puppetry  
- Embargoes  

Hybrid evaluation system:
- Algorithmic logic  
- Optional LLM contextual reasoning  

---

## 💾 Save & Scenario System
- JSON-based save/load system
- Supports custom timelines:
  - Historical starts  
  - Fictional eras  
- Fully extensible data model

---

## ✨ Optional / Future Features
- End-game world order system  
- Fog of war  
- Intelligence & espionage systems  

---

## 👥 Work Division

### 🧑‍💻 M. Ryan Haiqal bin Mohd Hafiz (Lead Developer)
- Engine core & performance optimization  
- Province selection system (Ebee Engine integration)  
- LLM integration (OpenAI / Ollama + Pydantic validation)  
- Debugging & mentoring  

---

### 🎮 Benedict Chin Jun Eu (Game Logic & UI)
- UI systems (menus, sidebars, diplomacy windows)  
- Combat mathematics system  
- Save/load implementation  

---

### 📖 Adam Syahmi (Content & Narrative Systems)
- Country/province database setup  
- LLM prompt engineering for leader personalities  
- NPC behavior logic design  

---

## 🧠 System Philosophy
- Strictly **turn-based simulation**
- Modular architecture for scalability
- Offline-first design with optional AI enhancements
- Designed for incremental prototype-to-full-scale expansion

---

## 🧩 Footnote: LLM Integration Strategy
The game supports multiple AI modes:
1. **Online API Mode (OpenAI)**  
2. **Local Model Mode (Ollama / offline LLMs)**  
3. **Offline Mode (rule-based fallback system)**  

All systems are validated through structured outputs (Pydantic) to ensure reliability and prevent hallucinated game actions.

---
