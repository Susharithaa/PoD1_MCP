# MCP Hub API Creation Accuracy Improvements

## Overview

This document outlines improvements to increase the accuracy and reliability of API creation in MCP Hub when parsing user-uploaded documents (PDF, DOCX, JSON, YAML, TXT, Postman collections).

The current system is functional but overly dependent on LLMs, which can lead to hallucinations, missing fields, and inconsistent schemas.

---

# Current Pipeline

```
User Upload → InputClassifier → doc_extractor → Chunking → SchemaAgent (LLM) → HITL → Validate → API Test → Save → Registry
```

---

# Key Problems Identified

## 1. Weak Endpoint Boundary Detection

* Regex-based chunking causes overlap
* Endpoints may bleed into each other
* Incorrect parameter association

## 2. Over-reliance on LLM

* LLM generates full schema in one pass
* Leads to:

  * hallucinated fields
  * missing required params
  * incorrect data types

## 3. No Validation Layer

* No deterministic checks before HITL
* Broken APIs reach user review stage

## 4. No Confidence Scoring

* All outputs treated equally
* No prioritization for review

## 5. No Feedback Loop

* System does not learn from corrections

---

# Improved Architecture (v2)

```
doc_extractor
   ↓
semantic_chunker
   ↓
deterministic_extractor
   ↓
SchemaAgent (LLM - enrichment only)
   ↓
schema_validator
   ↓
confidence_scoring
   ↓
reconciliation_pass (LLM)
   ↓
api_test_simulation
   ↓
HITL (focused review)
   ↓
registry
```

---

# Improvements in Detail

## 1. Deterministic Extraction Layer

### Goal:

Extract structured data without LLM.

### Extract:

* HTTP method (GET, POST, etc.)
* Endpoint path
* Query parameters
* Path parameters
* Headers

### Example:

```
GET /users/{id}
```

→ Extract:

```
method: GET
path: /users/{id}
params:
  id: string
```

### Benefit:

* Reduces hallucination
* Provides ground truth structure

---

## 2. SchemaAgent (LLM for Enrichment Only)

### Role:

LLM should ONLY:

* Add descriptions
* Infer request body schema
* Infer response schema

### NOT responsible for:

* Method detection
* Path detection
* Required param discovery

---

## 3. Semantic Chunking (Replace Regex)

### Instead of:

* Regex window extraction ❌

### Use:

* Headings (`###`, `####`)
* Endpoint patterns (`GET /`, `POST /`)

### Outcome:

* 1 chunk = 1 endpoint
* No overlap

---

## 4. Schema Validation Layer

### Validate:

* Required fields exist
* Path params match schema
* Query params correctly defined
* Data types are valid

### Example Check:

```
Path: /users/{id}
Schema must include:
id: string
```

### Action:

* Auto-fix OR
* Send correction prompt to LLM

---

## 5. Confidence Scoring

### Compute score based on:

* Has method
* Has path
* Has parameters
* Has request body
* Has response schema

### Usage:

| Score  | Action            |
| ------ | ----------------- |
| High   | Auto-approve      |
| Medium | Highlight in UI   |
| Low    | Force user review |

---

## 6. Reconciliation Pass (LLM)

### After all endpoints generated:

Run a final LLM pass:

Prompt:

> "Check consistency across all endpoints"

### Fix:

* Duplicate parameters
* Naming inconsistencies
* Missing auth
* Schema mismatches

---

## 7. Example-Based Extraction

### Priority:

Examples > Descriptions

### Extract from:

```
Request:
{
  "name": "John"
}
```

→ Build schema from actual example

---

## 8. API Test Simulation

### Before HITL:

Simulate API:

* Validate endpoint format
* Validate parameter structure
* (Optional) send test request

### If failure:

* Mark endpoint with warning
* Highlight in UI

---

# Final System Behavior

## Before Improvements:

* LLM-heavy
* High hallucination risk
* User fixes errors manually

## After Improvements:

* Deterministic + LLM hybrid
* Validated schemas
* Confidence-aware review
* Higher success rate

---

# Key Design Principle

> LLM should assist, not define the system.

---

# Recommended Implementation Order

1. Deterministic extraction layer
2. Schema validation engine
3. Confidence scoring system
4. Semantic chunking upgrade
5. Reconciliation pass
6. API test simulation

---

# Future Enhancements

* Learning from HITL corrections
* Auto schema refinement
* Versioning of generated APIs
* Observability (logging failures)

---

# Summary

By shifting from:

> LLM-dependent system

To:

> Structured + validated + assisted system

You will significantly improve:

* Accuracy
* Reliability
* User trust
* Scalability
