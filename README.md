# Ares.AI 📱⚡

**Control your phone with one sentence. No taps. No scrolls. Just intent → action.**

Ares.AI turns your high-level instructions like *"Open WhatsApp and message John"* into precise, automated mobile actions. Unlike traditional voice assistants that stop at simple tasks, Ares understands your screen and handles full workflows—like ordering a product or booking a ride—with real-time UI interaction.

---

## 🧠 Inspiration

Siri and Google Assistant can set alarms or play music—but what if you want to complete multi-step tasks like:

- Booking an Uber
- Ordering your cart on Amazon
- Navigating settings and toggling modes

We asked: *Why does this still take dozens of taps?*  
**Ares.AI** was born from this frustration—to act like a smart human assistant with AI precision.

---

## 🚀 What It Does

- 🔍 Understands high-level instructions like "Message Alex on Instagram"
- 🧩 Breaks it into step-by-step UI actions (tap, scroll, type, etc.)
- 👁️ Analyzes your phone screen via screenshots
- 🧠 Maintains context of what’s done, what’s next, and what failed
- 🔄 Retries, scrolls, adapts, or gives fallback instructions if stuck
- ✅ Executes real-time interactions with feedback loop

---

## ⚙️ Core Architecture

### 🧭 Goal Planning with Gemini 2.5 Pro
- Input: `"Book Uber to airport"`
- Output: Sequence of structured **atomic actions** like:
  - Open app → Tap search bar → Type destination → Tap "Book"

> Built using function calling with Gemini 2.5 Pro

### 🧠 Stateful Goal Execution
- Tracks progress per instruction
- Detects failure loops or stuck states
- Retries intelligently or attempts fallback actions

### 👁️ Visual Grounding via Gemini Vision
- Screenshots are sent to Gemini Vision with contextual prompts
- Identifies the **correct bounding box** to tap/type/scroll
- Uses screenshot hashing to detect redundant frames
- Adapts if the element is missing (scroll, wait, retry)

---

## 🧱 Built With

- **Android Studio** — UI automation + screen capture
- **Kotlin** — Native Android agent logic
- **Python** — Server + reasoning loop
- **Gemini 2.5 Pro + Vision** — Planning and grounding
- **Figma** — UI prototyping

---

## 🚧 Challenges We Faced

- 🌀 **UI Inconsistency** — Varying app layouts required adaptive vision grounding
- ⚡ **Real-Time Performance** — Balancing model calls with latency
- 🧭 **State Recovery** — Detecting dead-ends and designing recovery heuristics
- 🧠 **Natural Loop Avoidance** — Avoiding repeated steps when stuck

---

## 🤖 Outcome

Ares.AI feels like a human assistant with:
- AI-level consistency
- Visual awareness
- Resilience in unknown app flows

> From intent → screen understanding → action execution  
> Ares closes the loop in mobile automation.

---

## 📍 Roadmap (What's Next)

- 🔐 Permission-aware automation (auto-detect required permissions)
- 🧠 Long-term memory for task continuity across sessions
- 🌐 Web interface for remote task triggering
- 📊 Logs & analytics for debugging agent behavior
- 🤝 Community plugin system (custom atomic actions)

---
## 🎥 Demo

[![Watch the demo](https://img.youtube.com/vi/awKfjunMDRg/0.jpg)](https://www.youtube.com/watch?v=awKfjunMDRg)

---

## 🤝 Contributing

We welcome PRs, feature ideas, and collaborations!  
Please open an issue to start the conversation.

---

## 📜 License

MIT License

---

## 🧠 Shoutout

Inspired by the simplicity of real human assistants and powered by Google’s Gemini.  
*Ares doesn’t ask how—it just gets it done.*
