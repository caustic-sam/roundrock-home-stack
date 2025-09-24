#!/bin/bash
# Simple Pi-hole + Unbound Demo Script for Laymen
# Author: You :)

echo "🔎 1. Ad Blocking Demo"
echo "Trying to resolve a known ad server (doubleclick.net)..."
dig +short doubleclick.net @127.0.0.1 -p 5335
echo "👉 Pi-hole blocked that — no IP address returned!"

echo
echo "✅ 2. Valid DNSSEC Domain"
echo "Resolving cloudflare.com..."
dig +dnssec +multi cloudflare.com @127.0.0.1 -p 5335 | grep flags
echo "👉 Notice the 'ad' flag = authenticated (DNSSEC validated)."

echo
echo "❌ 3. Invalid DNSSEC Domain"
echo "Resolving dnssec-failed.org..."
dig +dnssec +multi dnssec-failed.org @127.0.0.1 -p 5335
echo "👉 It fails on purpose, proving Unbound is rejecting bad signatures."

echo
echo "🌐 4. Trace Example"
echo "Walking the chain of trust for example.com..."
dig +trace example.com | head -n 15
echo "👉 See it talk directly to root → .com → example.com — no Google/ISP in the middle."
