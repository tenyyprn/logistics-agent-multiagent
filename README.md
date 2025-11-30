# 🚢 International Logistics Quote Agent

**A Multi-Agent System for instant international shipping quotes**

Capstone Project for Google's 5-Day AI Agents Intensive Course

---

## 📋 Overview

This project is an AI-powered **Multi-Agent System** that provides comprehensive international shipping quotes instantly. Built with Google's Agent Development Kit (ADK) and Gemini 2.0 Flash, it demonstrates advanced agentic AI patterns including orchestrator coordination, agent transfer, and persistent memory.

### Key Features

- ✅ **Multi-Agent Architecture**: 1 Orchestrator + 4 Specialist Sub-Agents
- ✅ **15 Custom Tools**: Route search, cost calculation, document guidance, quote management
- ✅ **Sessions & Memory**: Customer data and quote history persistence
- ✅ **Observability**: Comprehensive logging for all agent activities
- ✅ **Agent Transfer**: Automatic delegation based on query type
- ✅ **Gemini 2.0 Flash**: Google's latest model optimized for agentic AI

---

## 🏗️ Architecture

### System Overview

```
+------------------------------------------+
|      LOGISTICS COORDINATOR AGENT         |
|            (Orchestrator)                |
|          Gemini 2.0 Flash                |
+--------------------+---------------------+
                     |
     +---------------+---------------+---------------+
     |               |               |               |
     v               v               v               v
+-----------+  +-----------+  +-----------+  +-----------+
|   ROUTE   |  |   COST    |  |    DOC    |  |   QUOTE   |
|  PLANNER  |  |  ANALYST  |  | SPECIALIST|  |  MANAGER  |
| (3 tools) |  | (4 tools) |  | (4 tools) |  | (4 tools) |
+-----------+  +-----------+  +-----------+  +-----------+
                     |
                     v
          +-------------------+
          |    DUMMY DATA     |
          |      LAYER        |
          +-------------------+
```

### Sub-Agents Detail

| Agent | Role | Tools |
|-------|------|-------|
| 🗺️ **Route Planner** | Find shipping routes | `search_sea_routes`, `search_air_routes`, `recommend_transport_mode` |
| 💰 **Cost Analyst** | Calculate costs | `calculate_sea_freight_cost`, `calculate_air_freight_cost`, `calculate_total_landed_cost`, `compare_shipping_options` |
| 📄 **Doc Specialist** | Document guidance | `get_required_documents`, `check_customs_regulations`, `get_hs_code_info`, `generate_shipping_checklist` |
| 💾 **Quote Manager** | Save/retrieve quotes | `save_quote`, `get_quote_history`, `save_customer_info`, `get_customer_info` |

### Agent Delegation

| Query Type | Delegated To | Example |
|------------|--------------|---------|
| Route search | `route_planner` | "Find routes from Japan to China" |
| Cost calculation | `cost_analyst` | "How much for 500kg to Shanghai?" |
| Documentation | `document_specialist` | "What documents do I need?" |
| Quote management | `quote_manager` | "Save this quote" |

---

## 🛠️ Tools Summary (15 Total)

### Route Planner Tools (3)
| Tool | Description |
|------|-------------|
| `search_sea_routes` | Find ocean freight routes |
| `search_air_routes` | Find air freight routes |
| `recommend_transport_mode` | Suggest optimal transport mode |

### Cost Analyst Tools (4)
| Tool | Description |
|------|-------------|
| `calculate_sea_freight_cost` | Calculate ocean freight with surcharges |
| `calculate_air_freight_cost` | Calculate air freight with fuel/security |
| `calculate_total_landed_cost` | Full cost including duties, VAT, customs |
| `compare_shipping_options` | Side-by-side comparison |

### Document Specialist Tools (4)
| Tool | Description |
|------|-------------|
| `get_required_documents` | List required shipping documents |
| `check_customs_regulations` | Import rules and restrictions |
| `get_hs_code_info` | HS code classification and duties |
| `generate_shipping_checklist` | Complete preparation checklist |

### Quote Manager Tools (4)
| Tool | Description |
|------|-------------|
| `save_quote` | Save quote with reference number |
| `get_quote_history` | Retrieve past quotes |
| `save_customer_info` | Store customer preferences |
| `get_customer_info` | Retrieve customer data |

---

## 📦 Data Coverage

### Routes
- **Sea Freight**: Japan ↔ China, Thailand, USA, Europe (5 routes)
- **Air Freight**: Japan ↔ China, Thailand, USA (3 routes)

### Rates
- FCL (20ft, 40ft containers)
- LCL (per CBM)
- Air freight tiers (weight-based)
- All surcharges (BAF, CAF, THC, etc.)

### Regulations
- China, Thailand, USA import rules
- Restricted/prohibited items
- HS codes with duty rates
- Trade agreements (RCEP, JTEPA)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10+
python --version

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install google-adk python-dotenv
```

### Setup

1. Create `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

2. Run the agent:
```bash
# Demo mode (preset queries)
python logistics_agent_multiagent.py

# Interactive mode
python logistics_agent_multiagent.py --interactive
```

---

## 💬 Usage Examples

### Interactive Session

```
👤 Enter customer ID: 001

✅ Session started for: 001

👤 You: What is the sea freight cost from Tokyo to Shanghai for 500kg, 2CBM?

🤖 Agent: The sea freight cost from Tokyo to Shanghai for 500kg, 2CBM is $488.
          Breakdown: BAF $13.50, CAF $4.50, THC $330, Base freight $90...
          This quote is valid for 30 days.

👤 You: Please save this quote.

🤖 Agent: OK. I have saved the quote with quote ID Q20251130143148,
          which is valid until 2025-12-30.

👤 You: quit

👋 Thank you for using our service!
```

### Sample Queries

- "What routes are available from Japan to China?"
- "Compare sea and air freight for 500kg machinery to Shanghai"
- "What documents do I need for shipping to Thailand?"
- "Calculate total landed cost including duties to USA"
- "Save this quote"
- "Show my quote history"

---

## 📁 Project Structure

```
logistics_agent/
├── logistics_agent_multiagent.py   # Main agent (local version)
├── README.md                        # This file
├── .env                             # API key (create this)
└── data/                            # (Optional) External data files
    ├── routes.json
    ├── rates.json
    └── regulations.json
```

---

## 🎓 Course Concepts Demonstrated

| Day | Concept | Implementation |
|-----|---------|----------------|
| Day 1 | Agent Basics | Coordinator agent with Gemini 2.0 Flash |
| Day 2 | Custom Tools | 15 specialized tools with proper docstrings |
| Day 3 | Sessions & Memory | InMemorySessionService + customer memory |
| Day 4A | Observability | Python logging with timestamps |
| Day 5 | Multi-Agent | Orchestrator + 4 sub-agents with transfer |

---

## 📊 Technical Specifications

| Component | Details |
|-----------|---------|
| Framework | Google Agent Development Kit (ADK) |
| Model | Gemini 2.0 Flash |
| Language | Python 3.10+ |
| Agents | 5 (1 Orchestrator + 4 Specialists) |
| Tools | 15 custom functions |
| Memory | In-memory (customer_memory dict, quote_history list) |

---

## 📊 Data Layer

### Current Implementation (Demo)

This project uses **embedded dummy data** for demonstration purposes. The data is defined directly in the Python code for simplicity and portability.

| Data Type | Contents |
|-----------|----------|
| **Routes** | 5 sea routes, 3 air routes (Japan ↔ China/Thailand/USA/Europe) |
| **Rates** | FCL, LCL, Air freight pricing with surcharges |
| **Regulations** | Import rules, HS codes, trade agreements |

### Production Enhancement

In a production environment, the dummy data layer would be replaced with:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Database** | PostgreSQL / MongoDB | Store routes, rates, customer data |
| **Carrier APIs** | Maersk, COSCO, ONE, FedEx | Real-time rates and tracking |
| **Customs APIs** | Government databases | Live regulations and HS codes |
| **Exchange Rates** | Forex API | Currency conversion |
| **Caching** | Redis | Performance optimization |

```
Current:  Agent → Dummy Data (in-memory dict)
Future:   Agent → API Gateway → Database / External APIs
```

---

## 🔮 Future Enhancements

- [ ] Real carrier API integration (Maersk, COSCO, etc.)
- [ ] Track & Trace functionality
- [ ] PDF quote generation
- [ ] Multi-language support (Japanese, Chinese, Thai)
- [ ] A2A Protocol for agent-to-agent communication
- [ ] MCP integration for external tools

---

## 👤 Author

**Orihara**  
DX Promotion Department, International Logistics Company

- 15+ years in international logistics
- Overseas experience: Suzhou (China), Bangkok (Thailand)
- Focus: AI-driven business development

---

## 📄 License

This project is released under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- Google AI and Kaggle for the 5-Day AI Agents Intensive Course
- Google ADK Team for the excellent framework
- Course instructors and community members

---

## 🔗 Links

- [5-Day AI Agents Intensive Course](https://www.kaggle.com/learn-guide/5-day-agents)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Kaggle Competition](https://www.kaggle.com/competitions/agents-intensive-capstone-project)