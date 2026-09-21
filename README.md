# ⚖️ Nyaya

### AI-Powered Legal Aid & Access-to-Justice Platform

> **Making legal help understandable, accessible, and actionable for everyone.**

🌐 **Live Platform:** https://nyaya.workwithani.tech/

💻 **GitHub:** https://github.com/anirudh12032008/nyaya

---
<img width="1470" height="832" alt="Screenshot 2026-09-21 at 8 32 13 PM" src="https://github.com/user-attachments/assets/7fae5716-0bc7-46e9-b73f-c37d23d18e93" />


# 🧑‍💻 Team

## Team Kwaii

> **Building technology for a more accessible justice system.**

### 👨‍💻 Team Members

| Name                    |                   
| ------------------------| 
| **[Anirudh Sahu]**      |  
| **[Ayush Kumar]**       |                                             
| **[Harsh Kumar]**       |                                         
| **[Nitish Kumar Singh]**|                                      

### Team Mission

We are a team interested in combining:

* Artificial Intelligence
* Software Engineering
* Legal Technology
* Accessibility
* Social Impact

to build practical technology that can help people navigate difficult systems.

---

# 🏆 Why We Built Nyaya

We believe that a person's ability to understand their rights should not depend entirely on:

* their income,
* their location,
* their technical knowledge,
* or their familiarity with legal language.

A person should be able to say:

> **"This happened to me."**

and get help understanding:

> **"What can I do next?"**

That is the problem Nyaya is trying to solve.

---
![Uploading Screenshot 2026-09-21 at 8.31.37 PM.png…]()

## 🧭 What is Nyaya?

**Nyaya** is an AI-powered legal aid platform designed to help ordinary citizens understand their legal problems and take the next practical step.

For many people, the legal system can feel intimidating because of:

* Complex legal language
* Lack of awareness about rights
* Uncertainty about where to file a complaint
* Difficulty understanding procedures
* Legal documentation requirements
* Filing fees and deadlines
* Limited access to affordable legal assistance
* Language barriers

Nyaya attempts to bridge this gap by allowing a person to simply **describe their problem in Hindi, Hinglish, or English**.

Instead of expecting a citizen to already understand the legal system, Nyaya works backwards:

**Problem → Legal classification → Appropriate forum → Applicable rules → Draft → Verification → Human/legal-aid workflow**

The goal is not to replace lawyers or courts.

The goal is to help a person **understand their situation and reach the appropriate legal-help pathway faster.**

---

# ❤️ The Social Problem

Legal rights are meaningful only when people can understand and exercise them.

A citizen may know that something is wrong but still not know:

> "What should I do now?"

For example:

* A consumer receives a defective product but doesn't know where to complain.
* A tenant faces an unfair situation and doesn't know what legal options exist.
* A person approaches the police but their complaint is not properly registered.
* A citizen doesn't know which authority or forum handles their matter.
* Someone eligible for legal aid doesn't know that they may qualify.
* A person misses an important legal deadline simply because they didn't know it existed.

Nyaya focuses on this **first-mile access-to-justice problem**.

Instead of starting with legal terminology, it starts with the **citizen's story**.

---

# 🎯 Our Mission

## "Make justice easier to understand and easier to reach."

Nyaya is built around three principles:

### 1. Understand

Convert a citizen's problem into understandable legal information.

### 2. Act

Identify the appropriate forum, procedure, documents, deadlines, and next steps.

### 3. Connect

Move the matter into a legal-aid/clinic workflow where human volunteers or legal professionals can assist.

---

# 👥 Who is Nyaya For?

Nyaya is primarily designed for:

* 👨‍👩‍👧 Citizens who need basic legal guidance
* 🧑‍🌾 People from underserved communities
* 🏠 Tenants and landlords
* 🛍️ Consumers facing disputes
* 👮 Citizens dealing with police-related complaints
* 💼 Workers and individuals facing everyday legal problems
* 🧑‍⚖️ Legal-aid volunteers
* ⚖️ Legal clinics
* 🎓 Law students and researchers
* 🤝 Social organizations working on access to justice

---

# ✨ Key Features

## 1. 🗣️ Natural-Language Legal Intake

Users don't need to know legal terminology.

They can simply explain what happened.

Example:

> "Maine online ek phone kharida tha, defective aaya aur company replacement nahi de rahi."

Nyaya processes the description and identifies the likely legal module.

Supported input style:

* English
* Hindi
* Hinglish

---

# 2. 🧠 AI-Powered Problem Classification

Nyaya analyzes the user's description and determines which workflow is relevant.

Current modules include areas such as:

* Consumer complaints
* Police complaints
* Tenant-related matters

The system can also ask for a missing fact when additional information is required before proceeding.

### Example

```text
User Problem
     ↓
AI Classification
     ↓
Consumer / Police / Tenant
     ↓
Specialized Legal Workflow
```

---

# 3. 🏛️ Forum & Filing Guidance

One of the biggest problems for ordinary citizens is knowing:

> "Mujhe complaint kahan karni hai?"

Nyaya calculates the appropriate forum and related filing information using structured legal rules rather than asking the language model to independently calculate everything.

For consumer matters, the system uses structured rule data to determine:

* Appropriate forum
* Applicable fee
* Limitation/deadline information

This is particularly important because deterministic calculations are handled by application code rather than being left entirely to an LLM.

---

# 4. 💰 Fee & Deadline Awareness

Legal procedures can involve:

* Filing fees
* Limitation periods
* Important deadlines

Nyaya surfaces these details as part of the workflow.

The platform intentionally keeps numerical/legal-rule calculations outside the generative model wherever possible.

```text
Legal Rules
     ↓
Structured Data
     ↓
Python Calculation
     ↓
Forum + Fee + Deadline
```

This reduces the risk of an LLM inventing a numerical value.

---

# 5. 📝 AI-Assisted Legal Drafting

After understanding the problem, Nyaya can generate a structured draft.

Depending on the workflow, this can include:

### Consumer

* Consumer complaint
* Filing-oriented draft

### Police

* SHO complaint
* SP complaint/letter
* Relevant police complaint workflow

### Tenant

* Counter-notice
* Clause-related observations

The objective is to transform:

**Citizen's story → structured legal document**

---

# 6. 🔍 AI Verification Layer

Nyaya doesn't simply generate a document and stop.

A second verification stage checks the generated result.

It can look for issues such as:

* Unsupported legal claims
* Incorrect sections
* Missing placeholders
* Incorrect forum information
* Unsupported factual statements
* Other inconsistencies

If verification fails, the system can attempt one controlled redraft and verify again.

### Architecture

```text
User Input
    ↓
AI Drafting
    ↓
Verification Agent
    ↓
   ┌───────────────┐
   │ Passed?       │
   └───────┬───────┘
       Yes │ No
           │
           ↓
       Re-draft
           ↓
       Verify Again
```

---

# 7. 📄 PDF Generation

Once a draft is prepared, Nyaya can render the document into a PDF.

This makes the output easier to:

* Save
* Review
* Share
* Print
* Use as a starting point for filing

The platform also supports QR-based document workflows and read-only sharing in its later stages.

---

# 8. ⚖️ Legal-Aid Eligibility

Nyaya goes beyond generating documents.

When a case enters the clinic workflow, the system can evaluate eligibility under the configured **NALSA Section 12** rules.

This is important from a social-impact perspective.

A person who may need legal assistance shouldn't simply receive an AI answer and be left alone.

The system can move the case toward a human-supported workflow.

---

# 9. 🏥 Legal Clinic Workspace

Nyaya includes a clinic-oriented workflow.

A generated case can be:

```text
Citizen
   ↓
Legal Intake
   ↓
Case Created
   ↓
Eligibility Check
   ↓
Volunteer Assignment
   ↓
Human Review
```

The clinic workspace can contain:

* Case queue
* Case status
* Eligibility result
* Assigned volunteer
* Feedback
* Administrative metrics

The system can automatically assign a case to a lower-load volunteer to help distribute cases across the clinic.

---

# 10. 👩‍⚖️ Human-in-the-Loop Approach

Nyaya is **not designed around the idea that AI should replace lawyers**.

Instead:

```text
AI
 ↓
Understand
 ↓
Structure
 ↓
Draft
 ↓
Verify
 ↓
Human Legal Review
```

This is especially important for sensitive legal matters.

AI can help reduce repetitive work and improve access to information, while human professionals remain important for case-specific legal judgment.

---

# 11. 🎙️ Voice Intake

Nyaya also includes browser-based voice intake using Speech Recognition.

This allows users to speak their problem instead of typing it.

Example:

> "Meri FIR register nahi ho rahi hai..."

The speech is converted into text and enters the normal legal-intake pipeline.

This can be particularly useful for people who are uncomfortable typing long legal descriptions.

The current implementation treats typed input as the primary input path, while voice provides an additional accessibility layer.

---

# 12. ⏰ Deadline Sentinel

Missing a deadline can significantly affect a legal matter.

Nyaya includes a deadline-monitoring workflow that can identify affected cases and generate reminders.

The system can produce Hindi reminders for cases approaching important deadlines.

Conceptually:

```text
Case
 ↓
Deadline
 ↓
Time Remaining
 ↓
Reminder
 ↓
Citizen / Clinic
```

---

# 13. 🔎 Similar Past Cases

Nyaya can search the clinic's existing case information to identify similar cases.

This helps a legal-aid worker answer questions like:

> "Have we handled a similar problem before?"

The current implementation uses case summaries and the clinic database rather than requiring a separate vector database.

---

# 14. 🧑‍⚖️ Multi-Agent Legal Council

Nyaya includes an advanced multi-agent architecture called **Orchestra**.

Multiple specialist agents can analyze a case from different perspectives.

The architecture includes agents focused on areas such as:

* Evidence
* Devil's advocate
* Strategy
* Risk
* Client communication

Their outputs are combined into a counsel-style brief.

### Concept

```text
                    ┌── Evidence Agent
                    │
                    ├── Strategy Agent
Case ───────────────┼── Risk Agent
                    │
                    ├── Devil's Advocate
                    │
                    └── Client Letter Agent
                              ↓
                       Counsel Brief
```

This allows the system to examine a case from multiple perspectives instead of relying on one model response.

---

# 15. 💬 Ask Nyaya

Nyaya also includes an agentic conversational interface.

Instead of only answering questions, the assistant can interact with the application's workspace.

Depending on the available tools, it can:

* List cases
* Open cases
* Search legal information
* Calculate forum/fee information
* Find similar cases
* Run the legal council
* Update case status

This turns Nyaya from a simple chatbot into an **AI interface for the legal-aid workflow**.

---

# 16. 🌐 Public Legal Guides

Nyaya can expose bilingual public guides to help people understand common legal processes.

The goal is to convert complicated procedures into simpler, actionable information.

Example structure:

```text
Problem
 ↓
What does the law mean?
 ↓
What documents are needed?
 ↓
Where should I go?
 ↓
What should I do next?
```

---

# 17. 📱 Shareable Case Links

Generated documents and case information can support read-only sharing.

This can help a citizen or volunteer share relevant information without giving editing access to the underlying case.

---

# 18. 🧾 Filing Autopilot Preview

Nyaya includes a prototype filing-autopilot workflow.

It can preview how information could be mapped into an e-Daakhil-style filing flow.

The actual submission action remains disabled in the current implementation.

This distinction is intentional:

> **Assist → Review → Confirm → File**

rather than blindly submitting AI-generated information.

---

# 🏗️ How Nyaya Works

The complete pipeline can be summarized as:

```text
                    CITIZEN
                       │
                       ▼
             Hindi / Hinglish / English
                       │
                       ▼
               ┌───────────────┐
               │  AI INTAKE    │
               └───────┬───────┘
                       │
                       ▼
              PROBLEM CLASSIFIER
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Consumer       Police       Tenant
          │            │            │
          └────────────┼────────────┘
                       ▼
                LEGAL WORKFLOW
                       │
                       ▼
             FORUM / FEE / DEADLINE
                       │
                       ▼
                 AI DRAFTING
                       │
                       ▼
                VERIFICATION
                       │
                ┌──────┴──────┐
                │             │
              PASS           FAIL
                │             │
                │          REDRAFT
                │             │
                └──────┬──────┘
                       ▼
                    PDF
                       │
                       ▼
               CLINIC CASE QUEUE
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       NALSA ELIGIBILITY    VOLUNTEER ASSIGNMENT
             │                   │
             └─────────┬─────────┘
                       ▼
                  HUMAN REVIEW
                       │
                       ▼
                 BETTER ACCESS
                 TO JUSTICE
```

---

# 🧠 Technical Architecture

Nyaya is built using a modular architecture.

### Core Stack

| Layer       | Technology                    |
| ----------- | ----------------------------- |
| Frontend/UI | Streamlit                     |
| Backend     | Python                        |
| AI          | Anthropic API                 |
| Database    | SQLite                        |
| Documents   | Python PDF rendering          |
| Voice       | Browser SpeechRecognition     |
| Deployment  | Streamlit / Cloudflare Tunnel |
| Testing     | Pytest                        |

The repository describes the application as a Streamlit + Anthropic API + SQLite system.

---

# 📂 Project Structure

```text
nyaya/
│
├── agent/
│   ├── client.py
│   ├── pipeline.py
│   ├── draft.py
│   ├── verify.py
│   ├── eligibility.py
│   ├── forum.py
│   ├── police.py
│   ├── tenant.py
│   ├── orchestra.py
│   ├── chat.py
│   ├── similar.py
│   ├── sentinel.py
│   └── prompts/
│
├── ui/
│   ├── intake.py
│   ├── cases.py
│   ├── admin.py
│   ├── chat.py
│   ├── orchestra.py
│   └── hooks.py
│
├── db/
│   ├── schema.sql
│   └── db.py
│
├── data/
│   ├── statutes
│   ├── rules
│   └── sample cases
│
├── pdf/
│   ├── render.py
│   └── qr.py
│
├── templates/
│
├── public/
│
├── tests/
│
├── deploy/
│
├── app.py
├── requirements.txt
├── warm_cache.py
├── CONTRIBUTING.md
└── README.md
```

This structure follows the modular architecture documented in the repository.

---

# 🔐 Reliability & Safety

Legal AI requires stronger safeguards than a normal chatbot.

Nyaya therefore uses several defensive mechanisms.

## 1. Deterministic calculations

Important values such as fees and limitation information are derived from structured rule data rather than being invented by the language model.

## 2. Section validation

The application checks cited legal section IDs against its structured data.

Unsupported section identifiers can be removed and logged.

## 3. Second-pass verification

Generated legal content goes through an additional verification stage.

## 4. Human review

AI-generated legal material should be reviewed by a qualified legal professional where appropriate.

## 5. No blind filing

Automated filing submission is not treated as equivalent to legal review.

---

# 🌍 Social Impact

Nyaya is built as a **social-impact technology project**.

Its objective is not simply:

> "Build an AI lawyer."

The larger objective is:

> **Reduce the distance between a person with a legal problem and the help they need.**

### Potential impact areas

#### 🧑‍🌾 Underserved communities

People may not know where to begin when facing a legal issue.

Nyaya provides a structured starting point.

#### 💰 Financial barriers

Before approaching a lawyer, a person can better understand what their problem may involve and what next steps could exist.

#### 🗣️ Language barriers

Hindi/Hinglish input helps users communicate naturally instead of requiring formal legal English.

#### 📄 Documentation barriers

Nyaya can transform a citizen's description into structured drafts.

#### ⏰ Deadline awareness

Reminders can reduce the risk of missing important dates.

#### ⚖️ Legal-aid discovery

Eligibility checks and clinic assignment can help route appropriate cases toward human assistance.

---

# 💡 Example: A Citizen's Journey

Imagine a citizen says:

> "Maine ek expensive phone kharida tha. Phone defective hai aur company replacement nahi kar rahi."

### Step 1 — Explain

The user describes the problem naturally.

### Step 2 — Classify

Nyaya identifies the matter as a potential consumer complaint.

### Step 3 — Understand the forum

The system evaluates the applicable structured rules.

### Step 4 — Generate a draft

Nyaya prepares a structured complaint.

### Step 5 — Verify

Another AI pass checks the generated output.

### Step 6 — Generate PDF

The citizen receives a usable document.

### Step 7 — Legal-aid workflow

The case can enter the clinic queue.

### Step 8 — Human assistance

A volunteer/legal professional can review the matter.

This creates a bridge:

```text
"I have a problem."
          ↓
"I understand my options."
          ↓
"I have a structured document."
          ↓
"I know where to go."
          ↓
"I can get human assistance."
```

---

# 🤖 Why AI + Human Support?

Nyaya follows a **Human + AI** model.

### AI is good at:

* Processing large amounts of information
* Classification
* Draft generation
* Summarization
* Repetitive workflows
* Finding patterns
* Organizing cases

### Humans are essential for:

* Legal judgment
* Contextual interpretation
* Client communication
* Ethical decisions
* Case strategy
* Final review
* Representation

Therefore:

> **AI accelerates legal assistance; it does not replace justice professionals.**

---

# 🚀 Current Development Stages

Nyaya has been developed progressively.

### Stage 0

Core AI client and application router.

### Stage 1

Consumer complaint workflow:

```text
Intake → Forum/Fee → Draft → PDF
```

### Stage 2

Police and tenant workflows.

### Stage 3

Legal clinic:

* Cases
* Eligibility
* Assignment
* Feedback
* Admin metrics

### Stage 4

* QR-enabled PDFs
* Read-only links
* Public bilingual guides
* Template reuse
* Feedback learning

### Stage 5

Advanced automation:

* Overnight triage
* Verification agent
* Deadline sentinel
* Voice intake
* Filing preview
* Similar cases

### Stage 6

Multi-agent legal council.

### Stage 7

Ask Nyaya agentic assistant.

These stages correspond to the implementation documented in the project's repository.

---

# 🛠️ Run Locally

## Requirements

* Python 3.11+
* Anthropic API key
* Git

Python 3.12 was used during development.

### 1. Clone

```bash
git clone https://github.com/anirudh12032008/nyaya.git
cd nyaya
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate

#### macOS/Linux

```bash
source .venv/bin/activate
```

#### Windows

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API key

```bash
export ANTHROPIC_API_KEY="your_api_key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your_api_key"
```

### 6. Run self-test

```bash
python -m agent.client --selftest
```

### 7. Start the application

```bash
streamlit run app.py
```

The original project documentation provides the same basic local setup flow.

---

# 🧪 Testing

Nyaya includes offline tests.

Run:

```bash
python -m pytest -q
```

The repository notes that the tests can run without an API key.

---

# 📊 Design Philosophy

Nyaya is built around five ideas:

```text
ACCESS
  ↓
UNDERSTANDING
  ↓
ACTION
  ↓
HUMAN SUPPORT
  ↓
JUSTICE
```

### Accessibility

Legal help should not require advanced legal knowledge.

### Simplicity

Users should be able to explain problems in normal language.

### Reliability

Critical calculations and legal identifiers should be grounded in structured data.

### Human oversight

High-impact legal decisions should remain reviewable by humans.

### Social impact

Technology should reduce barriers rather than create another barrier.

---

# ⚠️ Important Disclaimer

Nyaya is an **AI-powered legal information and assistance platform**.

It is not a court, law firm, or substitute for a qualified advocate.

AI-generated information may contain errors or may not fully apply to an individual's specific circumstances.

Users should verify important legal matters with a qualified lawyer or appropriate legal-aid authority before taking consequential action.

For urgent matters involving safety, criminal allegations, domestic violence, or other high-risk situations, users should seek appropriate professional or emergency assistance.

---

Future Roadmap:

Potential future directions include:

* 🌐 More Indian languages
* 🎙️ Advanced multilingual voice assistant
* 📱 Mobile application
* 🧑‍⚖️ Verified lawyer/volunteer network
* 🏛️ Government-service integrations
* 📚 Expanded legal knowledge base
* 🔎 Better case and precedent retrieval
* 📄 More document templates
* 🧠 Improved multi-agent reasoning
* 🔐 Stronger privacy architecture
* ♿ Accessibility improvements
* 📊 Social-impact analytics
* 🏘️ Community legal-aid centers
* 🤝 NGO and legal-clinic partnerships

---

# 🤝 Contributing

Contributions are welcome.

If you want to contribute:

```bash
git checkout -b feature/your-feature
```

Contributing? Read [CONTRIBUTING.md](CONTRIBUTING.md) first (branch → PR → review → squash).
Module contracts and data schemas live in [CONTRACT.md](CONTRACT.md).

Make your changes, test them, and open a Pull Request.

Before contributing, please review:

```text
CONTRIBUTING.md
CONTRACT.md
```

---

# 🌟 Support the Project

If you believe technology can help make legal information more accessible:

⭐ Star the repository
🍴 Fork the project
🐛 Report issues
💡 Suggest improvements
🤝 Contribute code
📢 Share the project

Every contribution helps move the idea forward.

---

# 🔗 Links

### 🌐 Live Application

https://nyaya.workwithani.tech/

### 💻 Source Code

https://github.com/anirudh12032008/nyaya

---

# ❤️ Final Message

## Justice should not begin with:

> "Do you know a lawyer?"

It should begin with:

> **"Tell us what happened."**

Nyaya is an attempt to make that first step easier.

**Understand your problem.
Understand your rights.
Understand your next step.**

### ⚖️ Nyaya — Technology for Access to Justice.

---

<p align="center">

**Built with ❤️ for social impact**

</p>
