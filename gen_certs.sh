#!/bin/bash
# quick-start generates this

mkdir -p ./certs

# Generate CA
openssl genrsa -out ./certs/ca.key 2048
openssl req -new -x509 -days 3650 \
    -key ./certs/ca.key -out ./certs/ca.pem \
    -subj "/CN=Roomzin Test CA" -sha256

# Generate server certificate (works for all nodes)
openssl genrsa -out ./certs/key.pem 2048
openssl req -new -key ./certs/key.pem \
    -out ./certs/cert.csr \
    -subj "/CN=roomzin-node" -sha256

# Wildcard SAN for Docker environment
cat > ./certs/cert.ext <<EOF
subjectAltName = DNS:*.docker.internal,DNS:*.test,DNS:localhost,IP:127.0.0.1
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
EOF

openssl x509 -req -in ./certs/cert.csr \
    -CA ./certs/ca.pem -CAkey ./certs/ca.key -CAcreateserial \
    -out ./certs/cert.pem -days 3650 -sha256 \
    -extfile ./certs/cert.ext

rm ./certs/cert.csr ./certs/cert.ext

# Result: cert.pem, key.pem, ca.pem