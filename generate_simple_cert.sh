#!/bin/bash
# 간단한 테스트용 인증서 생성 (체인 없이)
# 사용법: ./generate_simple_cert.sh [출력 디렉토리] [도메인명]

OUTPUT_DIR="${1:-./test-certs}"
DOMAIN="${2:-test.example.com}"

mkdir -p "$OUTPUT_DIR"

echo "🔐 간단한 테스트용 인증서 생성 중..."

# 서버 개인키 생성
openssl genrsa -out "$OUTPUT_DIR/server.key" 2048

# 서버 인증서 생성 (자체 서명)
openssl req -new -x509 -key "$OUTPUT_DIR/server.key" \
    -out "$OUTPUT_DIR/server.crt" \
    -days 365 \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=Test Server/CN=$DOMAIN" \
    -extensions v3_server \
    -extfile <(cat <<EOF
[v3_server]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
IP.1 = 127.0.0.1
EOF
)

echo ""
echo "✅ 인증서 생성 완료!"
echo ""
echo "📁 생성된 파일:"
echo "  - $OUTPUT_DIR/server.crt (서버 인증서)"
echo "  - $OUTPUT_DIR/server.key (서버 개인키)"
echo ""
echo "🧪 테스트 방법:"
echo "  import_certificate_with_auto_chain("
echo "    name='test-cert',"
echo "    cert_path='$OUTPUT_DIR/server.crt',"
echo "    key_path='$OUTPUT_DIR/server.key'"
echo "  )"
echo ""


