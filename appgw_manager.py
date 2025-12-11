import sys
from typing import List, Dict, Optional
from azure.mgmt.network import NetworkManagementClient
from azure.core.exceptions import ResourceNotFoundError

class AppGwManager:
    """Application Gateway 관리"""
    
    def __init__(self, subscription_id: str, credential):
        self.subscription_id = subscription_id
        self.credential = credential
        self.network_client = NetworkManagementClient(credential, subscription_id)
    
    def list_application_gateways(self, resource_group_name: Optional[str] = None) -> Dict:
        """Application Gateway 목록 조회"""
        try:
            gateways = []
            
            if resource_group_name:
                # 특정 리소스 그룹의 Application Gateway 조회
                appgws = self.network_client.application_gateways.list(resource_group_name)
            else:
                # 모든 구독의 Application Gateway 조회
                # list_all()이 작동하지 않을 수 있으므로 ResourceManagementClient를 사용
                try:
                    from azure.mgmt.resource import ResourceManagementClient
                    resource_client = ResourceManagementClient(self.credential, self.subscription_id)
                    
                    # 모든 리소스 그룹 조회
                    resource_groups = resource_client.resource_groups.list()
                    
                    # 각 리소스 그룹에서 Application Gateway 조회
                    for rg in resource_groups:
                        try:
                            appgws_in_rg = self.network_client.application_gateways.list(rg.name)
                            for appgw in appgws_in_rg:
                                gateways.append({
                                    "name": appgw.name,
                                    "resource_group": rg.name,
                                    "location": appgw.location,
                                    "state": appgw.operational_state if hasattr(appgw, 'operational_state') else None,
                                    "sku": {
                                        "name": appgw.sku.name if appgw.sku else None,
                                        "tier": appgw.sku.tier if appgw.sku else None,
                                        "capacity": appgw.sku.capacity if appgw.sku else None
                                    } if appgw.sku else None
                                })
                        except Exception as rg_error:
                            # 특정 리소스 그룹 조회 실패는 로그 남기고 계속 진행
                            print(f"⚠️ 리소스 그룹 '{rg.name}'에서 Application Gateway 조회 실패: {rg_error}", file=sys.stderr)
                            continue
                    
                    return {"success": True, "gateways": gateways}
                except Exception as list_all_error:
                    # list_all() 시도
                    try:
                        appgws = self.network_client.application_gateways.list_all()
                        for appgw in appgws:
                            gateways.append({
                                "name": appgw.name,
                                "resource_group": appgw.id.split("/")[4],
                                "location": appgw.location,
                                "state": appgw.operational_state if hasattr(appgw, 'operational_state') else None,
                                "sku": {
                                    "name": appgw.sku.name if appgw.sku else None,
                                    "tier": appgw.sku.tier if appgw.sku else None,
                                    "capacity": appgw.sku.capacity if appgw.sku else None
                                } if appgw.sku else None
                            })
                        return {"success": True, "gateways": gateways}
                    except Exception as list_all_error2:
                        raise list_all_error
            
            # 리소스 그룹이 지정된 경우
            for appgw in appgws:
                gateways.append({
                    "name": appgw.name,
                    "resource_group": appgw.id.split("/")[4] if hasattr(appgw, 'id') and appgw.id else resource_group_name,
                    "location": appgw.location,
                    "state": appgw.operational_state if hasattr(appgw, 'operational_state') else None,
                    "sku": {
                        "name": appgw.sku.name if appgw.sku else None,
                        "tier": appgw.sku.tier if appgw.sku else None,
                        "capacity": appgw.sku.capacity if appgw.sku else None
                    } if appgw.sku else None
                })
            return {"success": True, "gateways": gateways}
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"❌ Application Gateway 목록 조회 실패: {e}", file=sys.stderr)
            print(f"상세 오류:\n{error_detail}", file=sys.stderr)
            return {"success": False, "error": str(e), "error_detail": error_detail, "gateways": []}
    
    def get_application_gateway(self, resource_group_name: str, appgw_name: str) -> Dict:
        """Application Gateway 상세 정보 조회"""
        try:
            appgw = self.network_client.application_gateways.get(resource_group_name, appgw_name)
            return {
                "success": True,
                "name": appgw.name,
                "resource_group": resource_group_name,
                "location": appgw.location,
                "state": appgw.operational_state if hasattr(appgw, 'operational_state') else None,
                "ssl_certificates": [
                    {
                        "name": cert.name,
                        "key_vault_secret_id": cert.key_vault_secret_id if hasattr(cert, 'key_vault_secret_id') else None
                    }
                    for cert in (appgw.ssl_certificates or [])
                ],
                "http_listeners": [
                    {
                        "name": listener.name,
                        "frontend_port": listener.frontend_port.id.split("/")[-1] if listener.frontend_port else None,
                        "protocol": listener.protocol if hasattr(listener, 'protocol') else None,
                        "ssl_certificate": listener.ssl_certificate.id.split("/")[-1] if listener.ssl_certificate else None
                    }
                    for listener in (appgw.http_listeners or [])
                ]
            }
        except ResourceNotFoundError:
            return {"success": False, "error": f"Application Gateway '{appgw_name}'을 찾을 수 없습니다."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_ssl_certificate_from_keyvault(
        self,
        resource_group_name: str,
        appgw_name: str,
        cert_name: str,
        keyvault_secret_id: str
    ) -> Dict:
        """Key Vault 인증서를 Application Gateway SSL 인증서로 추가"""
        try:
            # Application Gateway 가져오기
            appgw = self.network_client.application_gateways.get(resource_group_name, appgw_name)
            
            # 기존 SSL 인증서 목록 확인
            ssl_certificates = list(appgw.ssl_certificates or [])
            
            # 이미 존재하는지 확인
            existing_cert = next(
                (cert for cert in ssl_certificates if cert.name == cert_name),
                None
            )
            
            if existing_cert:
                # 기존 인증서 업데이트
                existing_cert.key_vault_secret_id = keyvault_secret_id
                return {
                    "success": True,
                    "action": "updated",
                    "name": cert_name,
                    "message": f"SSL 인증서 '{cert_name}'이 업데이트되었습니다."
                }
            else:
                # 새 인증서 추가
                from azure.mgmt.network.models import ApplicationGatewaySslCertificate
                
                new_cert = ApplicationGatewaySslCertificate(
                    name=cert_name,
                    key_vault_secret_id=keyvault_secret_id
                )
                ssl_certificates.append(new_cert)
                appgw.ssl_certificates = ssl_certificates
                
                # Application Gateway 업데이트
                poller = self.network_client.application_gateways.begin_create_or_update(
                    resource_group_name,
                    appgw_name,
                    appgw
                )
                result = poller.result()
                
                return {
                    "success": True,
                    "action": "added",
                    "name": cert_name,
                    "message": f"SSL 인증서 '{cert_name}'이 추가되었습니다."
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_ssl_certificates(self, resource_group_name: str, appgw_name: str) -> List[Dict]:
        """Application Gateway의 SSL 인증서 목록 조회"""
        try:
            appgw = self.network_client.application_gateways.get(resource_group_name, appgw_name)
            certificates = []
            for cert in (appgw.ssl_certificates or []):
                certificates.append({
                    "name": cert.name,
                    "key_vault_secret_id": cert.key_vault_secret_id if hasattr(cert, 'key_vault_secret_id') else None,
                    "provisioning_state": cert.provisioning_state if hasattr(cert, 'provisioning_state') else None
                })
            return certificates
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"❌ SSL 인증서 목록 조회 실패: {e}", file=sys.stderr)
            print(f"상세 오류:\n{error_detail}", file=sys.stderr)
            # 오류 정보를 포함한 딕셔너리 반환 (서버에서 처리 가능하도록)
            raise  # 예외를 다시 발생시켜서 서버에서 처리하도록
    
    def remove_ssl_certificate(
        self,
        resource_group_name: str,
        appgw_name: str,
        cert_name: str
    ) -> Dict:
        """Application Gateway에서 SSL 인증서 제거"""
        try:
            # Application Gateway 가져오기
            appgw = self.network_client.application_gateways.get(resource_group_name, appgw_name)
            
            # 기존 SSL 인증서 목록 확인
            ssl_certificates = list(appgw.ssl_certificates or [])
            
            # 제거할 인증서 찾기
            cert_to_remove = next(
                (cert for cert in ssl_certificates if cert.name == cert_name),
                None
            )
            
            if not cert_to_remove:
                return {"success": False, "error": f"SSL 인증서 '{cert_name}'을 찾을 수 없습니다."}
            
            # 인증서 제거
            ssl_certificates = [cert for cert in ssl_certificates if cert.name != cert_name]
            appgw.ssl_certificates = ssl_certificates
            
            # Application Gateway 업데이트
            poller = self.network_client.application_gateways.begin_create_or_update(
                resource_group_name,
                appgw_name,
                appgw
            )
            result = poller.result()
            
            return {
                "success": True,
                "name": cert_name,
                "message": f"SSL 인증서 '{cert_name}'이 제거되었습니다."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def attach_certificate_to_listener(
        self,
        resource_group_name: str,
        appgw_name: str,
        listener_name: str,
        ssl_certificate_name: str
    ) -> Dict:
        """Listener에 SSL 인증서 연결"""
        try:
            # Application Gateway 가져오기
            appgw = self.network_client.application_gateways.get(resource_group_name, appgw_name)
            
            # Listener 찾기
            listener = next(
                (l for l in (appgw.http_listeners or []) if l.name == listener_name),
                None
            )
            
            if not listener:
                return {"success": False, "error": f"Listener '{listener_name}'을 찾을 수 없습니다."}
            
            # SSL 인증서 참조 설정
            from azure.mgmt.network.models import SubResource
            
            listener.ssl_certificate = SubResource(
                id=f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/applicationGateways/{appgw_name}/sslCertificates/{ssl_certificate_name}"
            )
            
            # Application Gateway 업데이트
            poller = self.network_client.application_gateways.begin_create_or_update(
                resource_group_name,
                appgw_name,
                appgw
            )
            result = poller.result()
            
            return {
                "success": True,
                "message": f"Listener '{listener_name}'에 SSL 인증서 '{ssl_certificate_name}'이 연결되었습니다."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

