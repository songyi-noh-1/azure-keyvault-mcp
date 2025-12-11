import sys
import os
from typing import List, Dict, Optional
from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient, CertificatePolicy
from azure.core.exceptions import ResourceNotFoundError

# SSL 인증서 검증 제어 (프록시 환경 대응)
if os.environ.get("AZURE_KEYVAULT_DISABLE_SSL_VERIFY", "").lower() in ("1", "true", "yes"):
    import ssl
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''

class KeyVaultManager:
    """Key Vault Secret 및 Certificate 관리"""
    
    def __init__(self, vault_url: str, credential):
        self.vault_url = vault_url
        self.credential = credential
        
        # ⭐ SSL 검증 완전히 비활성화 (KT 프록시 환경 대응)
        print("🔧 SSL 검증 비활성화 모드로 Key Vault 연결 중...", file=sys.stderr)
        
        import ssl
        import urllib3
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context
        from azure.core.pipeline.transport import RequestsTransport
        
        # SSL 경고 비활성화
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 전역적으로 SSL 검증 비활성화 (requests 라이브러리)
        requests.packages.urllib3.disable_warnings()
        
        # 커스텀 SSL 컨텍스트 생성 (검증 완전히 비활성화)
        class NoVerifyHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)
        
        # SSL 검증 비활성화된 세션 생성
        session = requests.Session()
        session.verify = False
        session.mount('https://', NoVerifyHTTPAdapter())
        
        # RequestsTransport를 상속받아 session을 강제로 설정
        class CustomRequestsTransport(RequestsTransport):
            def __init__(self, session=None, *args, **kwargs):
                # session을 먼저 설정하지 않고 부모 초기화
                super().__init__(*args, **kwargs)
                if session:
                    # 내부 session 속성 강제 설정
                    self.session = session
                    if hasattr(self, '_session'):
                        self._session = session
                    # _client도 설정 (일부 버전에서 필요)
                    if hasattr(self, '_client'):
                        self._client.session = session
            
            def send(self, request, **kwargs):
                # Azure SDK는 connection_verify를 사용하므로 이를 False로 설정
                kwargs['connection_verify'] = False
                # verify도 False로 설정 (혹시 모를 경우 대비)
                if 'verify' in kwargs:
                    kwargs.pop('verify')
                # 부모 클래스의 send 메서드 호출
                return super().send(request, **kwargs)
        
        transport = CustomRequestsTransport(session=session)
        
        # 클라이언트 생성
        self.secret_client = SecretClient(
            vault_url=vault_url, 
            credential=credential,
            transport=transport
        )
        self.cert_client = CertificateClient(
            vault_url=vault_url, 
            credential=credential,
            transport=transport
        )
        
        print("✅ SSL 검증 비활성화 완료", file=sys.stderr)
        self._test_connection()
    
    def _test_connection(self):
        """Key Vault 접근 테스트"""
        try:
            list(self.secret_client.list_properties_of_secrets(max_page_size=1))
            print(f"✅ Key Vault 연결 성공: {self.vault_url}", file=sys.stderr)
        except Exception as e:
            error_msg = str(e)
            
            # SSL 오류 감지
            is_ssl_error = (
                "CERTIFICATE_VERIFY_FAILED" in error_msg or 
                "certificate verify failed" in error_msg.lower() or
                "ssl" in error_msg.lower()
            )
            
            if is_ssl_error:
                print(f"❌ SSL 인증서 검증 오류 (여전히 발생):", file=sys.stderr)
                print(f"   {error_msg}", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"💡 해결 방법:", file=sys.stderr)
                print(f"   1. MCP 설정에서 환경 변수 추가:", file=sys.stderr)
                print(f"      AZURE_KEYVAULT_DISABLE_SSL_VERIFY=1", file=sys.stderr)
                print(f"   2. Claude Desktop 재시작", file=sys.stderr)
                raise ConnectionError(f"SSL 인증서 검증 실패: {error_msg}")
            
            # 권한 오류
            print(f"❌ Key Vault 접근 실패: {e}", file=sys.stderr)
            vault_name = self.vault_url.split("//")[1].split(".")[0]
            print(f"💡 권한 부여가 필요할 수 있습니다:", file=sys.stderr)
            print(f"az role assignment create \\", file=sys.stderr)
            print(f"  --role 'Key Vault Secrets Officer' \\", file=sys.stderr)
            print(f"  --assignee $(az ad signed-in-user show --query id -o tsv) \\", file=sys.stderr)
            print(f"  --scope $(az keyvault show --name {vault_name} --query id -o tsv)", file=sys.stderr)
            raise ConnectionError(f"Key Vault 접근 실패: {e}")
    
    # ===== SECRET 관리 =====
    
    def set_secret(self, name: str, value: str) -> Dict:
        """Secret 생성/업데이트"""
        try:
            secret = self.secret_client.set_secret(name, value)
            return {
                "success": True,
                "name": secret.name,
                "version": secret.properties.version,
                "created": str(secret.properties.created_on)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_secret(self, name: str) -> Dict:
        """Secret 조회"""
        try:
            secret = self.secret_client.get_secret(name)
            return {
                "success": True,
                "name": secret.name,
                "value": secret.value,
                "version": secret.properties.version,
                "updated": str(secret.properties.updated_on)
            }
        except ResourceNotFoundError:
            return {"success": False, "error": f"Secret '{name}'을 찾을 수 없습니다."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_secrets(self) -> List[Dict]:
        """모든 Secret 목록 조회"""
        try:
            secrets = []
            for secret_props in self.secret_client.list_properties_of_secrets():
                secrets.append({
                    "name": secret_props.name,
                    "enabled": secret_props.enabled,
                    "created": str(secret_props.created_on),
                    "updated": str(secret_props.updated_on)
                })
            return secrets
        except Exception as e:
            print(f"❌ Secret 목록 조회 실패: {e}", file=sys.stderr)
            return []
    
    def delete_secret(self, name: str) -> Dict:
        """Secret 삭제 (soft delete)"""
        try:
            poller = self.secret_client.begin_delete_secret(name)
            deleted_secret = poller.result()
            return {
                "success": True,
                "name": deleted_secret.name,
                "deleted_on": str(deleted_secret.deleted_date)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ===== CERTIFICATE 관리 =====
    
    def import_certificate(self, name: str, pfx_bytes: bytes, password: Optional[str] = None) -> Dict:
        """PFX 인증서 import"""
        try:
            has_existing = False
            try:
                self.cert_client.get_certificate(name)
                has_existing = True
            except ResourceNotFoundError:
                has_existing = False
            
            import_kwargs = {
                "certificate_name": name,
                "certificate_bytes": pfx_bytes,
                "password": password
            }
            
            # 기존 인증서가 없을 때만 정책 설정
            # Azure Key Vault import 시 content_type을 명시적으로 설정
            if not has_existing:
                # PFX 형식 인증서를 위한 정책 생성
                policy = CertificatePolicy(
                    content_type="application/x-pkcs12"
                )
                import_kwargs["policy"] = policy
            
            cert = self.cert_client.import_certificate(**import_kwargs)
            
            return {
                "success": True,
                "name": cert.name,
                "id": cert.id,
                "thumbprint": cert.properties.x509_thumbprint.hex() if cert.properties.x509_thumbprint else None,
                "is_new": not has_existing  # 신규 추가인지 갱신인지 구분
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_certificate(self, name: str) -> Dict:
        """인증서 조회"""
        try:
            cert = self.cert_client.get_certificate(name)
            return {
                "success": True,
                "name": cert.name,
                "id": cert.id,
                "enabled": cert.properties.enabled,
                "created": str(cert.properties.created_on),
                "expires": str(cert.properties.expires_on),
                "thumbprint": cert.properties.x509_thumbprint.hex() if cert.properties.x509_thumbprint else None
            }
        except ResourceNotFoundError:
            return {"success": False, "error": f"Certificate '{name}'을 찾을 수 없습니다."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_certificates(self) -> List[Dict]:
        """모든 인증서 목록 조회"""
        try:
            certs = []
            for cert_props in self.cert_client.list_properties_of_certificates():
                certs.append({
                    "name": cert_props.name,
                    "enabled": cert_props.enabled,
                    "created": str(cert_props.created_on),
                    "expires": str(cert_props.expires_on) if cert_props.expires_on else None,
                    "thumbprint": cert_props.x509_thumbprint.hex() if cert_props.x509_thumbprint else None
                })
            return certs
        except Exception as e:
            print(f"❌ 인증서 목록 조회 실패: {e}", file=sys.stderr)
            return []
    
    def delete_certificate(self, name: str) -> Dict:
        """인증서 삭제"""
        try:
            poller = self.cert_client.begin_delete_certificate(name)
            deleted_cert = poller.result()
            # deleted_date 속성 확인 (속성 이름이 다를 수 있음)
            deleted_on = None
            if hasattr(deleted_cert, 'deleted_date') and deleted_cert.deleted_date:
                deleted_on = str(deleted_cert.deleted_date)
            elif hasattr(deleted_cert, 'deleted_on') and deleted_cert.deleted_on:
                deleted_on = str(deleted_cert.deleted_on)
            elif hasattr(deleted_cert.properties, 'deleted_on') and deleted_cert.properties.deleted_on:
                deleted_on = str(deleted_cert.properties.deleted_on)
            
            return {
                "success": True,
                "name": deleted_cert.name,
                "deleted_on": deleted_on
            }
        except Exception as e:
            return {"success": False, "error": str(e)}