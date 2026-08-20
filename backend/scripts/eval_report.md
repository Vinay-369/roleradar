# RoleRadar AI Model Evaluation Report

**Generated:** 2026-08-20T03:49:57.957708+00:00  
**Target Provider / Model:** `mock`  
**Evaluation Scope:** 10 diverse technical domains (Backend, Frontend, Full Stack, AI/ML, DevOps, Fresher, Mobile, QA, Java Enterprise, AppSec)

## Executive Summary

| Metric | Result | Target Benchmark | Status |
| :--- | :--- | :--- | :--- |
| **JSON Schema Validation Rate (Tailoring)** | **100.0%** | >= 98.0% | PASS |
| **JSON Schema Validation Rate (Interview)** | **100.0%** | >= 98.0% | PASS |
| **Truth Guard Evidence Grounding** | **100.0%** | 100.0% | PASS |
| **Average Tailoring Latency** | **0.3 ms** | < 2500 ms | PASS |
| **Average Interview Latency** | **0.3 ms** | < 2500 ms | PASS |
| **Composite Quality Score** | **5.0 / 5.00** | >= 4.0 / 5.0 | PASS |

## Domain-by-Domain Benchmark Results

| Case ID | Domain / Role | Tailoring Valid | Evidence Grounded | Tailoring Latency | Interview Valid | Interview Latency | Quality Rating |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `case_01` | **Backend / Python**<br>*Senior Backend Engineer* | PASS (2 changes) | PASS | 0.5 ms | PASS (5 Qs) | 0.5 ms | **5.0/5.0** |
| `case_02` | **Frontend / TypeScript**<br>*Senior Frontend Developer* | PASS (2 changes) | PASS | 0.4 ms | PASS (5 Qs) | 0.3 ms | **5.0/5.0** |
| `case_03` | **Full Stack / MERN**<br>*Full Stack Software Engineer* | PASS (2 changes) | PASS | 0.3 ms | PASS (5 Qs) | 0.3 ms | **5.0/5.0** |
| `case_04` | **AI / ML & Data**<br>*Machine Learning Engineer* | PASS (2 changes) | PASS | 0.2 ms | PASS (5 Qs) | 0.2 ms | **5.0/5.0** |
| `case_05` | **DevOps & Cloud**<br>*Cloud Platform & DevOps Engineer* | PASS (2 changes) | PASS | 0.2 ms | PASS (5 Qs) | 0.3 ms | **5.0/5.0** |
| `case_06` | **Fresher / Entry-Level**<br>*Junior Software Engineer* | PASS (2 changes) | PASS | 0.2 ms | PASS (5 Qs) | 0.2 ms | **5.0/5.0** |
| `case_07` | **Mobile Development**<br>*Mobile App Developer* | PASS (2 changes) | PASS | 0.4 ms | PASS (5 Qs) | 0.3 ms | **5.0/5.0** |
| `case_08` | **QA Automation & SDET**<br>*SDET / QA Automation Engineer* | PASS (2 changes) | PASS | 0.3 ms | PASS (5 Qs) | 0.2 ms | **5.0/5.0** |
| `case_09` | **Enterprise Java**<br>*Java Enterprise Developer* | PASS (2 changes) | PASS | 0.4 ms | PASS (5 Qs) | 0.4 ms | **5.0/5.0** |
| `case_10` | **Security & DevSecOps**<br>*Application Security Engineer* | PASS (2 changes) | PASS | 0.2 ms | PASS (5 Qs) | 0.2 ms | **5.0/5.0** |

## Architectural Justification for Project Report & Viva Defense

1. **Zero AI Hallucination Guarantee (Truth Guard)**: Every AI-proposed edit requires a verifiable source citation in the candidate's master resume or Achievement Journal. Unapproved items are blocked in deterministic application code.
2. **Strict Schema-Constrained Decoding**: Output is enforced via Pydantic response models, preventing malformed responses from degrading downstream ATS engines or interview pipelines.
3. **Predictable Latency Profile**: Sub-second execution for local/cached queries ensures responsive UI workflows without locking user interactions.