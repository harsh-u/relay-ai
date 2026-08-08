# RelayAI

> AI Inference Gateway for Voice AI Platforms.

RelayAI is a provider-agnostic middleware layer that sits between a
voice platform's Speech-to-Text (STT) system and its Large Language Model (LLM).

Its goal is simple:

> Do not call an expensive LLM when the request can be answered safely and
> confidently without one.

## Problem

A typical voice AI pipeline looks like:

    User
      ↓
    STT
      ↓
    LLM
      ↓
    TTS
      ↓
    User

Many conversational requests do not require LLM reasoning.

Examples:

- Hello
- Hi
- Can you repeat that?
- Thank you
- Goodbye
- Common business FAQs
- Previously answered questions

Sending every request to an LLM increases:

- inference cost,
- latency,
- token consumption.

## RelayAI

RelayAI sits between STT and the LLM:

    User
      ↓
    STT
      ↓
    RelayAI
      │
      ├── Local response
      │
      └── LLM
            ↓
          TTS
            ↓
          User

RelayAI determines the cheapest and safest way to handle each request.

## Core Components

- Conversation Context
- Intent Detection
- Rule Engine
- Knowledge Engine
- Semantic Matching
- Decision Engine
- LLM Router
- Analytics

## Design Principles

- Low latency
- Provider agnostic
- Multi-tenant
- Business-level isolation
- LLM as the last resort
- Safe reuse of knowledge
- Minimal infrastructure overhead

## Development

Requirements:

- Python 3.12+
- uv
- Docker
- Docker Compose

Install dependencies:

    uv sync

Run tests:

    make test

Run lint:

    make lint

Run the application:

    make dev

## Project Structure

    relay-ai/
    ├── backend/
    │   ├── app/
    │   └── tests/
    ├── docs/
    ├── scripts/
    ├── AGENTS.md
    ├── Makefile
    ├── pyproject.toml
    └── README.md

## Status

RelayAI is currently under active development.