#!/bin/bash

set -e

CERTS_DIR="certs"
CA_DAYS=3650
CERT_DAYS=3650
KEY_BITS=2048

mkdir -p "$CERTS_DIR"

# Generate CA if not exists
if [ ! -f "$CERTS_DIR/ca.pem" ]; then
    openssl genrsa -out "$CERTS_DIR/ca.key" $KEY_BITS
    openssl req -new -x509 -days $CA_DAYS -key "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.pem" \
        -subj "/CN=Roomzin CA" -sha256 \
        -extensions v3_ca \
        -config <(cat <<EOF
[req]
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
EOF
)
    echo "Generated CA: $CERTS_DIR/ca.pem"
fi

for HOSTNAME in "$@"; do
    HOST_DIR="$CERTS_DIR/$HOSTNAME"
    mkdir -p "$HOST_DIR"
    
    # Server key
    openssl genrsa -out "$HOST_DIR/key.pem" $KEY_BITS
    
    # CSR
    openssl req -new -key "$HOST_DIR/key.pem" -out "$HOST_DIR/temp.csr" \
        -subj "/CN=$HOSTNAME" -sha256
    
    # Create extfile with SAN and EKU
    cat > "$HOST_DIR/temp.ext" <<EOF
subjectAltName = DNS:$HOSTNAME
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
EOF
    
    # Sign with CA
    openssl x509 -req -in "$HOST_DIR/temp.csr" \
        -CA "$CERTS_DIR/ca.pem" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
        -out "$HOST_DIR/cert.pem" -days $CERT_DAYS -sha256 \
        -extfile "$HOST_DIR/temp.ext"
    
    rm "$HOST_DIR/temp.csr" "$HOST_DIR/temp.ext"
    
    # Verify SAN
    echo "=== $HOSTNAME cert SANs ==="
    openssl x509 -in "$HOST_DIR/cert.pem" -noout -text | grep -A1 "Subject Alternative Name"
    
    echo "Generated for $HOSTNAME: $HOST_DIR/cert.pem and key.pem"
done