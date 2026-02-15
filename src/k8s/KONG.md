# Kong Gateway (Kong Ingress Controller) 설치

Kong을 Kubernetes Ingress로 사용할 때의 설치 방법입니다. Kong을 쓰면 `ingress.yaml`의 `ingressClassName`을 `kong`으로 바꾸고, localhost 접근 시 Kong proxy 서비스로 포트포워드하면 됩니다.

## 사전 요구 사항

- Kubernetes 클러스터
- Helm 3.x

## 1. Helm 저장소 추가 및 설치

```bash
helm repo add kong https://charts.konghq.com
helm repo update
```

**온프레미스(온라인 없이) 설치** — Kong Ingress Controller + Kong Gateway 한 번에 설치:

```bash
helm install kong kong/ingress -n kong --create-namespace
```

배포가 끝날 때까지 1~2분 정도 걸릴 수 있습니다.

## 2. 설치 확인

```bash
kubectl get pods -n kong
kubectl get svc -n kong
```

프록시 서비스 이름은 보통 `kong-gateway-proxy` 또는 `kong-kong-proxy` 입니다 (차트 버전에 따라 다를 수 있음).

## 3. 이 프로젝트 Ingress에서 Kong 사용하기

Kong Ingress Controller의 기본 IngressClass 이름은 `kong` 입니다.  
`src/k8s/ingress.yaml`에서 다음처럼 수정하세요:

```yaml
spec:
  ingressClassName: kong   # nginx → kong
  rules:
    - http:
        paths:
          # ...
```

적용:

```bash
kubectl apply -k src/k8s
# 또는
./scripts/deploy-k8s.sh
```

## 4. localhost로 접속 (포트포워드)

Kong proxy 서비스로 포트포워드한 뒤 브라우저에서 접속합니다.

```bash
# Kong proxy 서비스 확인
kubectl get svc -n kong

# 포트포워드 (서비스 이름이 kong-gateway-proxy 인 경우)
kubectl port-forward -n kong svc/kong-gateway-proxy 8080:80
```

이후 http://localhost:8080 으로 접속합니다.

서비스 이름이 다르면(예: `kong-kong-proxy`) 다음처럼 실행하세요:

```bash
kubectl port-forward -n kong svc/kong-kong-proxy 8080:80
```

기존 `scripts/port-forward-ingress.sh`는 nginx 기준이라 Kong 사용 시에는 위 `kubectl port-forward` 명령을 직접 쓰거나, 환경 변수로 Kong 서비스를 지정해 사용할 수 있습니다:

```bash
INGRESS_NS=kong INGRESS_SVC=kong-gateway-proxy ./scripts/port-forward-ingress.sh 8080
```

## 5. Kong 제거

```bash
helm uninstall kong -n kong
kubectl delete namespace kong
```

## 참고

- [Kong Ingress Controller - Install with Helm](https://docs.konghq.com/kubernetes-ingress-controller/latest/install/helm/)
- [Kong Helm Charts](https://github.com/Kong/charts)
- Kong Konnect(클라우드 제어 평면) 없이 온프레미스만 쓰면 위 `helm install kong kong/ingress` 한 줄로 충분합니다.
