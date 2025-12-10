# keyvault_manager.py
import sys
from typing import List, Dict, Optional
from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient, CertificatePolicy
from azure.core.exceptions import ResourceNotFoundError

class KeyVaultManager:
    """Key Vault Secret 및 Certificate 관리"""
    
    def __init__(self, vault_url: str, credential):
        self.vault_url = vault_url
        self.secret_client = SecretClient(vault_url=vault_url, credential=credential)
        self.cert_client = CertificateClient(vault_url=vault_url, credential=credential)
        self._test_connection()
    
    def _test_connection(self):
        """Key Vault 접근 테스트"""
        try:
            # 간단한 list 호출로 접근 확인
            list(self.secret_client.list_properties_of_secrets(max_page_size=1))
            print(f"✅ Key Vault 연결 성공:  {self.vault_url}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Key Vault 접근 실패: {e}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"권한 부여 필요:", file=sys.stderr)
            vault_name = self.vault_url.split("//")[1].split(". ")[0]
            print(f"az role assignment create \\", file=sys.stderr)
            print(f"  --role 'Key Vault Secrets Officer' \\", file=sys. stderr)
            print(f"  --assignee $(az ad signed-in-user show --query id -o tsv) \\", file=sys.stderr)
            print(f"  --scope $(az keyvault show --name {vault_name} --query id -o tsv)", file=sys.stderr)
            sys.exit(1)
    
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
    
    def get_secret(self, name:  str) -> Dict:
        """Secret 조회"""
        try:
            secret = self.secret_client.get_secret(name)
            return {
                "success": True,
                "name": secret.name,
                "value": secret. value,
                "version": secret.properties.version,
                "updated": str(secret.properties.updated_on)
            }
        except ResourceNotFoundError:
            return {"success": False, "error": f"Secret '{name}'을 찾을 수 없습니다."}
        except Exception as e:
            return {"success": False, "error":  str(e)}
    
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
            poller = self.secret_client. begin_delete_secret(name)
            deleted_secret = poller.result()
            return {
                "success":  True,
                "name": deleted_secret.name,
                "deleted_on": str(deleted_secret. deleted_date)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ===== CERTIFICATE 관리 =====
    
    def import_certificate(self, name: str, pfx_bytes: bytes, password: Optional[str] = None) -> Dict:
        """PFX 인증서 import"""
        try:
            # 기존 인증서가 있는지 확인
            has_existing = False
            try:
                self.cert_client.get_certificate(name)
                has_existing = True
            except ResourceNotFoundError:
                has_existing = False
            
            # 인증서 import 파라미터 준비
            import_kwargs = {
                "certificate_name": name,
                "certificate_bytes": pfx_bytes,
                "password": password
            }
            
            # 기존 인증서가 없으면 기본 정책 사용
            if not has_existing:
                import_kwargs["policy"] = CertificatePolicy.get_default()
            # 기존 인증서가 있으면 정책 생략 (기존 정책 유지)
            
            # 인증서 import
            cert = self.cert_client.import_certificate(**import_kwargs)
            
            return {
                "success": True,
                "name": cert.name,
                "id": cert.id,
                "thumbprint": cert.properties.x509_thumbprint. hex() if cert.properties.x509_thumbprint else None
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
                "thumbprint": cert. properties.x509_thumbprint. hex() if cert.properties.x509_thumbprint else None
            }
        except ResourceNotFoundError:
            return {"success": False, "error": f"Certificate '{name}'을 찾을 수 없습니다."}
        except Exception as e:
            return {"success":  False, "error": str(e)}
    
    def list_certificates(self) -> List[Dict]:
        """모든 인증서 목록 조회"""
        try:
            certs = []
            for cert_props in self.cert_client. list_properties_of_certificates():
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
            deleted_cert = poller. result()
            return {
                "success": True,
                "name": deleted_cert.name,
                "deleted_on": str(deleted_cert.deleted_date) if deleted_cert.deleted_date else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}