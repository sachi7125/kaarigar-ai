---
name: pre-flight
description: Run a structured pre-flight checklist before starting any new project, build, Claude Project, database, system, or workflow. Use this skill whenever I say "pre-flight," "run pre-flight," "before we build," "new project," "let's start a new project," "I want to build," "I'm creating a new project," "run the questions," "run the checklist," or any variation of wanting to think before building. Also trigger when I mention creating a new Claude Project, Notion database, content system, automation workflow, or any infrastructure that is meant to last beyond a single session. If I jump straight into building something new without running pre-flight, gently suggest running it first. This is the steering wheel before the gas pedal.
---

# Pre-Flight Check — Build From The Right Position

Run a structured pre-flight checklist before starting any new project, build, system, database, or workflow. You answer the questions on my behalf, surfacing what you see so I get visibility before I commit.

The principle: Excitement is fuel. Questions are the steering wheel. You run the checklist so I see what I might not.

## When to Use This

Any time I am about to start something new that is meant to last. This includes:

- A new Claude Project
- A new Notion database or system
- A new automation workflow (n8n, Zapier, etc.)
- A new content system or extraction pipeline
- A new client delivery system
- A new website section, landing page, or product
- A new skill file
- Any build session where the output is supposed to be used repeatedly

If I am doing a quick one-off task (writing a caption, drafting an email, brainstorming), skip this. Pre-flight is for things that are meant to persist.

## Trigger Phrases

- "pre-flight"
- "run pre-flight"
- "before we build"
- "new project"
- "let's start a new project"
- "I want to build [something]"
- "I'm creating a new [project/database/system]"
- "run the questions"
- "run the checklist"

## The Pre-Flight Protocol

### Step 1: Gather Context

Before answering the checklist, pull from every available source:

- **Memory and preferences** — what you already know about my business, stack, priorities, working patterns, and current builds
- **Conversation history** — anything discussed in this session or referenced from past sessions
- **My operating context, wherever I keep it** — if you can reach my notes, docs, or knowledge base, pull the latest operational data
- **My build tracker, if I keep one** — if it is accessible, check for related active builds that this project connects to or depends on

Do not ask me to provide context you already have. The whole point is that you see what I might not.

### Step 2: Answer The 5 Pre-Flight Questions

You answer all five questions yourself based on what you know. Present the completed checklist as a structured brief. Be specific, not generic. Every answer should reference real details about my business, stack, current priorities, or known constraints.

Present it exactly like this:

---

**PRE-FLIGHT BRIEF: [Name of what I'm building]**

Here's what I see before we build. Review this, correct anything that's off, and add what I'm missing.

**1. What this is actually supposed to do 90 days from now**
[Your answer. Be specific about what sustained usage looks like given my business model, team, and workflows. Name what success means in concrete terms, not abstract outcomes. A demo and a system look identical on day one. They look completely different on day 90.]

**2. Where the data lives, who owns it, and what happens if the tool changes**
[Your answer. Name the specific platforms, databases, and dependencies involved. Flag any platform risk, export limitations, or ownership gaps. Reference my known stack.]

**3. The invisible attack on this build**
[Your answer. Name 2-3 specific risks that could break this over time. These should not be generic risks. They should be specific to this build, my patterns, my stack, and my stage of business. Think about what I tend to overlook based on past builds and known working habits.]

**4. Who this is being built for — personal use, team use, or product**
[Your answer. State the intended audience and flag any architecture implications. If the answer changes the build approach, say so directly. Building for myself and accidentally building it like a product wastes weeks. Building for sale on personal infrastructure creates problems that can't be undone.]

**5. Decisions being made here that can't easily be reversed**
[Your answer. Name the specific irreversible or hard-to-reverse decisions in this build. Schema design, platform choice, authentication architecture, naming conventions that propagate, permissions structures. If everything is reversible, say so.]

---

### Step 3: Surface The Blind Spots

After the five answers, add a separate section:

**WHAT YOU MIGHT NOT BE SEEING**

This is your version of the Master Question: "What do you not know that you don't know?" List 2-4 things I likely haven't considered. These can be:

- Dependencies on other active builds
- Timing conflicts with current priorities
- Scope creep signals in the request
- Missing prerequisites
- Capacity constraints given my working window and current commitments
- Integration points that aren't obvious yet

Be direct. Name the thing. Don't hedge.

### Step 4: Confirm or Correct

After presenting the completed brief, say:

> **What needs correcting? What am I missing? Once you confirm, we build.**

Wait for me to review. I may:
- Confirm everything and say go
- Correct specific answers
- Add context that changes the picture
- Ask you to dig deeper on one area

If I correct or add, update your understanding and confirm the revised scope before building.

### Step 5: Log the Pre-Flight (Optional)

If I keep a build tracker and you can reach it, offer to log this as a new entry with the pre-flight brief captured in the description and next-action fields.

If I say no or the tracker isn't accessible, move on. Don't hold up the build for logging.

### Step 6: Build

Now build. The pre-flight is complete. Proceed with the actual project with full clarity on what you're building, why, and what to watch out for.

## Voice and Tone

- Direct. No fluff.
- Treat me as a CEO, not a student.
- Answer with confidence and specificity, not hedged generalities.
- If you don't have enough information to answer a question well, say exactly what you're missing and ask for that specific piece, not the whole question.
- Keep the energy forward-moving. This is not a blocker. This is a launchpad.

## Key Principles

- The most expensive mistake in the agentic era is building fast without asking the right questions first.
- The second most expensive mistake is asking the right questions and making the human do all the answering when you already have the context.
- Pre-flight is you showing me what you see. My job is to confirm, correct, and add. Not to start from scratch every time.
- This is what Human First, AI Enabled looks like in practice.