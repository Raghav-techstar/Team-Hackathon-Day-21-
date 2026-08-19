# Akhila - Shipment Data Cleaning & PostgreSQL Loading

## Overview

This document describes the changes implemented by **Akhila** for the shipment data cleaning and PostgreSQL loading workflow.

The changes include:

- Shipment data cleaning and transformation
- Carrier validation and standardization
- Ship date validation and formatting
- Shipment status standardization and validation
- Expected delivery date validation
- Delivered date validation
- Freight cost validation
- Delay days calculation
- Separation of clean and rejected shipment records
- Loading cleaned and rejected data into PostgreSQL

---

# 1. Project Environment Setup

The project uses a Python virtual environment to keep project dependencies isolated.

## Create Virtual Environment

From the project root directory:

```bash
python3 -m venv .venv