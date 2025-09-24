sudo tee /etc/unbound/unbound.conf.d/pi-hole.conf >/dev/null <<'EOF'
# writes file

server:
  verbosity: 0
  interface: 127.0.0.1
  port: 5335
  do-ip4: yes
  do-ip6: no
  do-udp: yes
  do-tcp: yes

  # Privacy & security
  qname-minimisation: yes
  harden-glue: yes
  harden-dnssec-stripped: yes
  harden-referral-path: yes
  prefetch: yes
  prefetch-key: yes
  cache-min-ttl: 300
  cache-max-ttl: 86400
  msg-cache-size: 128m
  rrset-cache-size: 256m

  # DNSSEC
  auto-trust-anchor-file: "/var/lib/unbound/root.key"
  trust-anchor-signaling: yes

  # Root hints
  root-hints: "/var/lib/unbound/root.hints"

  # Performance sanity
  udp-connect: yes
  aggressive-nsec: yes
EOF